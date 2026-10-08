from ytmusicapi import YTMusic
import subprocess
import sys
import os
import json
import tempfile
import threading
import queue
import time

from PySide6.QtCore import (
    QObject,
    Slot,
    Signal,
    Property,
    QIODevice,
    QByteArray
)

from PySide6.QtMultimedia import (
    QMediaPlayer,
    QAudioOutput,
    QAudioSink,
    QAudioFormat
)


class AudioBuffer(QIODevice):
    def __init__(self):
        super().__init__()
        self.buffer = bytearray()
        self.lock = threading.Lock()

    def start(self):
        self.open(QIODevice.ReadOnly)

    def feed(self, data):
        with self.lock:
            self.buffer.extend(data)
        self.readyRead.emit()

    def readData(self, maxlen):
        with self.lock:
            if not self.buffer:
                return b""
            data = self.buffer[:maxlen]
            del self.buffer[:maxlen]
            return bytes(data)

    def writeData(self, data):
        return -1

    def bytesAvailable(self):
        with self.lock:
            return len(self.buffer) + super().bytesAvailable()


class MusicPlayer(QObject):
    # Core existing signal compatibility
    searchResults = Signal(list)

    # UI status and state signals
    playbackStateChanged = Signal(str)  # "playing", "paused", "stopped"
    currentSongChanged = Signal(str, str, str, int)  # title, artist, videoId, durationSec
    volumeChanged = Signal(float)
    songFinished = Signal(str)  # videoId
    coverUrlChanged = Signal(str)
    likedSongsChanged = Signal(list)
    recommendationsReady = Signal(list)

    def __init__(self):
        super().__init__()
        try:
            self.yt = YTMusic()
        except Exception:
            self.yt = None

        self.audio = QAudioOutput()
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio)
        self.audio.setVolume(0.8)

        self._volume = 0.8
        self._playback_state = "stopped"
        self._current_title = "No Track Selected"
        self._current_artist = "Ready to Play"
        self._current_video = None
        self._current_duration = 210
        self._current_cover_url = ""

        self._audio_sink = None
        self._audio_device = None
        self._download_process = None
        self._stream_thread = None
        self._song_cache = {}

        # Liked Songs Storage (~/.dgx/liked_songs.json)
        self._liked_file = os.path.join(os.path.expanduser("~"), ".dgx", "liked_songs.json")
        os.makedirs(os.path.dirname(self._liked_file), exist_ok=True)
        self._liked_songs = self._load_liked_songs()

    def _load_liked_songs(self) -> list:
        if os.path.isfile(self._liked_file):
            try:
                with open(self._liked_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for s in data:
                            if isinstance(s, dict) and "videoId" in s:
                                self._song_cache[s["videoId"]] = s
                        return data
            except Exception as e:
                print("[MusicPlayer] Notice loading liked songs:", e)
        return []

    def _save_liked_songs(self):
        try:
            with open(self._liked_file, "w", encoding="utf-8") as f:
                json.dump(self._liked_songs, f, indent=2)
        except Exception as e:
            print("[MusicPlayer] Notice saving liked songs:", e)

    @Property(str, notify=coverUrlChanged)
    def coverUrl(self):
        return self._current_cover_url

    @Property(str, notify=playbackStateChanged)
    def playbackState(self):
        return self._playback_state

    @Property(str, notify=currentSongChanged)
    def currentTitle(self):
        return self._current_title

    @Property(str, notify=currentSongChanged)
    def currentArtist(self):
        return self._current_artist

    @Property(str, notify=currentSongChanged)
    def currentVideoId(self):
        return self._current_video or ""

    @Property(int, notify=currentSongChanged)
    def currentDuration(self):
        return self._current_duration

    @Slot(result=list)
    def get_liked_songs(self) -> list:
        return list(self._liked_songs)

    @Slot(str, result=bool)
    def is_liked(self, video_id: str) -> bool:
        if not video_id:
            return False
        return any(s.get("videoId") == video_id for s in self._liked_songs)

    @Slot(str, str, str, int, str, result=bool)
    def toggle_like(self, video_id: str, title: str = "", artist: str = "", duration: int = 0, cover_url: str = "") -> bool:
        if not video_id:
            return False

        existing_idx = next((i for i, s in enumerate(self._liked_songs) if s.get("videoId") == video_id), None)
        if existing_idx is not None:
            # Unlike
            self._liked_songs.pop(existing_idx)
            self._save_liked_songs()
            self.likedSongsChanged.emit(self._liked_songs)
            return False
        else:
            # Like
            dur_sec = duration or 210
            dur_text = f"{dur_sec//60}:{dur_sec%60:02d}"
            item = {
                "videoId": video_id,
                "title": title or (self._current_title if self._current_video == video_id else "Track"),
                "artist": artist or (self._current_artist if self._current_video == video_id else "Artist"),
                "duration": dur_sec,
                "durationText": dur_text,
                "coverUrl": cover_url or (f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"),
                "likedAt": time.time()
            }
            self._liked_songs.insert(0, item)
            self._song_cache[video_id] = item
            self._save_liked_songs()
            self.likedSongsChanged.emit(self._liked_songs)
            return True

    @Slot(str, result=bool)
    def remove_liked_song(self, video_id: str) -> bool:
        if not video_id:
            return False
        before_len = len(self._liked_songs)
        self._liked_songs = [s for s in self._liked_songs if s.get("videoId") != video_id]
        if len(self._liked_songs) != before_len:
            self._save_liked_songs()
            self.likedSongsChanged.emit(self._liked_songs)
            return True
        return False

    @Slot()
    def fetch_recommendations(self):
        """Generates lightweight music recommendations based on liked songs and artists."""
        def _worker():
            try:
                liked = self._liked_songs
                queries = []
                if liked:
                    # Collect top artists & track vibes from liked songs
                    artists = [s.get("artist") for s in liked if s.get("artist") and s.get("artist") != "Artist"]
                    if artists:
                        # Pick most recent liked artist or combination
                        queries.append(f"{artists[0]} songs")
                        if len(artists) > 1:
                            queries.append(f"{artists[1]} music")
                if not queries:
                    queries = ["lofi chill coding beats", "ambient focus synthwave"]

                results = []
                seen_ids = set(s.get("videoId") for s in liked)
                if self.yt is None:
                    self.yt = YTMusic()

                for q in queries[:2]:
                    try:
                        raw = self.yt.search(q, filter="songs")
                        for song in raw[:6]:
                            vid = song.get("videoId", "")
                            if vid and vid not in seen_ids:
                                seen_ids.add(vid)
                                dur_sec = self._parse_duration(song.get("duration_seconds") or song.get("duration"))
                                thumbnails = song.get("thumbnails", [])
                                cover_url = thumbnails[-1]["url"] if thumbnails else f"https://img.youtube.com/vi/{vid}/hqdefault.jpg"
                                artists_list = song.get("artists", [])
                                item = {
                                    "title": song.get("title", "Unknown Title"),
                                    "artist": artists_list[0]["name"] if artists_list else "Unknown Artist",
                                    "videoId": vid,
                                    "duration": dur_sec,
                                    "durationText": song.get("duration", f"{dur_sec//60}:{dur_sec%60:02d}"),
                                    "coverUrl": cover_url
                                }
                                results.append(item)
                                self._song_cache[vid] = item
                    except Exception as ex_q:
                        print("[MusicPlayer] Recommendation search error for query:", q, ex_q)

                self.recommendationsReady.emit(results)
            except Exception as e:
                print("[MusicPlayer] Fetch recommendations error:", e)
                self.recommendationsReady.emit([])

        threading.Thread(target=_worker, daemon=True).start()

    @staticmethod
    def _parse_duration(dur_val):
        if isinstance(dur_val, (int, float)):
            return int(dur_val)
        if isinstance(dur_val, str) and ":" in dur_val:
            parts = dur_val.strip().split(":")
            try:
                if len(parts) == 2:
                    return int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:
                    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            except ValueError:
                pass
        return 210

    @Slot(str)
    def search_music(self, query):
        if not query or not query.strip():
            return

        def _do_search():
            try:
                if self.yt is None:
                    self.yt = YTMusic()
                results = self.yt.search(query, filter="songs")
                songs = []
                for song in results:
                    title = song.get("title", "Unknown Title")
                    artists = song.get("artists", [])
                    artist = artists[0]["name"] if artists else "Unknown Artist"
                    vid = song.get("videoId", "")
                    if vid:
                        dur_sec = self._parse_duration(song.get("duration_seconds") or song.get("duration"))
                        thumbnails = song.get("thumbnails", [])
                        cover_url = thumbnails[-1]["url"] if thumbnails else f"https://img.youtube.com/vi/{vid}/hqdefault.jpg"
                        item = {
                            "title": title,
                            "artist": artist,
                            "videoId": vid,
                            "duration": dur_sec,
                            "durationText": song.get("duration", f"{dur_sec//60}:{dur_sec%60:02d}"),
                            "coverUrl": cover_url
                        }
                        songs.append(item)
                        self._song_cache[vid] = item

                self.searchResults.emit(songs)
            except Exception as e:
                print("Search error:", e)
                # No fake demo tracks on search failure
                self.searchResults.emit([])

        t = threading.Thread(target=_do_search, daemon=True)
        t.start()

    @Slot(str)
    def play_song(self, videoId):
        self._stop_stream()
        self._current_video = videoId

        # Update metadata and cover URL if available in cache
        if videoId in self._song_cache:
            song = self._song_cache[videoId]
            self._current_title = song.get("title", "Streaming Track")
            self._current_artist = song.get("artist", "Artist")
            self._current_duration = song.get("duration", 210)
            self._current_cover_url = song.get("coverUrl", f"https://img.youtube.com/vi/{videoId}/hqdefault.jpg")
        else:
            self._current_title = f"Track {videoId[:8]}"
            self._current_artist = "YouTube Music"
            self._current_duration = 210
            self._current_cover_url = f"https://img.youtube.com/vi/{videoId}/hqdefault.jpg"

        self.currentSongChanged.emit(self._current_title, self._current_artist, videoId, self._current_duration)
        self.coverUrlChanged.emit(self._current_cover_url)
        self._set_state("loading")
        print("Loading song:", videoId, "Duration:", self._current_duration, "Cover:", self._current_cover_url)

        # Create audio format
        format = QAudioFormat()
        format.setSampleRate(48000)
        format.setChannelCount(2)
        format.setSampleFormat(QAudioFormat.Int16)

        # Create our streaming device
        self._audio_device = AudioBuffer()
        self._audio_device.start()

        # Create audio sink
        self._audio_sink = QAudioSink(format, self)
        self._audio_sink.setVolume(self._volume)
        self._audio_sink.start(self._audio_device)

        # Start network/FFmpeg stream thread
        self._stream_thread = threading.Thread(
            target=self._stream_song,
            args=(videoId,),
            daemon=True
        )
        self._stream_thread.start()

    @staticmethod
    def _get_installed_browsers():
        local_app = os.environ.get("LOCALAPPDATA", "")
        app_data = os.environ.get("APPDATA", "")
        prog_files = os.environ.get("ProgramFiles", "")
        prog_files_x86 = os.environ.get("ProgramFiles(x86)", "")

        browser_paths = {
            "chrome": [
                os.path.join(local_app, "Google", "Chrome", "User Data"),
                os.path.join(prog_files, "Google", "Chrome", "Application", "chrome.exe"),
                os.path.join(prog_files_x86, "Google", "Chrome", "Application", "chrome.exe"),
            ],
            "edge": [
                os.path.join(local_app, "Microsoft", "Edge", "User Data"),
                os.path.join(prog_files_x86, "Microsoft", "Edge", "Application", "msedge.exe"),
                os.path.join(prog_files, "Microsoft", "Edge", "Application", "msedge.exe"),
            ],
            "firefox": [
                os.path.join(app_data, "Mozilla", "Firefox", "Profiles"),
                os.path.join(prog_files, "Mozilla Firefox", "firefox.exe"),
            ],
            "brave": [
                os.path.join(local_app, "BraveSoftware", "Brave-Browser", "User Data"),
                os.path.join(prog_files, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
            ],
            "opera": [
                os.path.join(app_data, "Opera Software", "Opera Stable"),
                os.path.join(local_app, "Programs", "Opera"),
            ],
            "vivaldi": [
                os.path.join(local_app, "Vivaldi", "User Data"),
            ],
            "chromium": [
                os.path.join(local_app, "Chromium", "User Data"),
            ],
        }

        order = ["chrome", "edge", "firefox", "brave", "chromium", "opera", "vivaldi"]
        installed = []
        for b in order:
            paths = browser_paths.get(b, [])
            if any(os.path.exists(p) for p in paths):
                installed.append(b)

        # Include remaining browsers in fallback order
        for b in order:
            if b not in installed:
                installed.append(b)

        return installed

    def _extract_stream_url(self, url):
        # 1. Android / Mobile client extraction (Primary fast path)
        for client in ["android", "ios", "tv_embedded"]:
            cmd_client = [
                sys.executable,
                "-m",
                "yt_dlp",
                "-g",
                "--no-playlist",
                "--extractor-args",
                f"youtube:player_client={client}",
                url
            ]
            try:
                res = subprocess.run(cmd_client, capture_output=True, text=True, timeout=15)
                if res.returncode == 0 and res.stdout.strip():
                    print("Android client succeeded" if client == "android" else f"{client.capitalize()} client succeeded")
                    return res.stdout.strip()
            except Exception:
                pass

        # 2. Normal extraction fallback
        print("Android client failed -> trying normal extraction")
        cmd_normal = [
            sys.executable,
            "-m",
            "yt_dlp",
            "-f",
            "bestaudio/140/ba",
            "-g",
            "--no-playlist",
            url
        ]
        try:
            res = subprocess.run(cmd_normal, capture_output=True, text=True, timeout=20)
            if res.returncode == 0 and res.stdout.strip():
                print("Normal extraction succeeded")
                return res.stdout.strip()
        except Exception:
            pass

        # 3. Browser cookies fallback
        print("Normal extraction failed -> trying browser cookies")
        browsers = self._get_installed_browsers()

        for b in browsers:
            name = b.capitalize()
            print(f"Trying {name}...")
            cmd_browser = [
                sys.executable,
                "-m",
                "yt_dlp",
                "-f",
                "bestaudio/140/ba",
                "-g",
                "--no-playlist",
                "--cookies-from-browser",
                b,
                url
            ]
            try:
                res = subprocess.run(cmd_browser, capture_output=True, text=True, timeout=15)
                if res.returncode == 0 and res.stdout.strip():
                    print(f"{name} succeeded")
                    return res.stdout.strip()
                else:
                    print(f"{name} failed")
            except Exception:
                print(f"{name} failed")

        return None

    def _stream_song(self, videoId):
        actual_id = videoId
        if videoId.startswith("demo_"):
            demo_map = {
                "demo_1": "3_g2un5M350",
                "demo_2": "suxP321fM5s",
                "demo_3": "5qap5aO4i9A",
                "demo_4": "DWcJFNfaw90"
            }
            actual_id = demo_map.get(videoId, "3_g2un5M350")

        url = f"https://www.youtube.com/watch?v={actual_id}"
        print("Getting audio stream for:", url)

        try:
            stream_url = self._extract_stream_url(url)
            if not stream_url or self._current_video != videoId:
                print("No stream URL returned after all fallbacks")
                self._set_state("stopped")
                return

            self._download_process = subprocess.Popen(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    stream_url,
                    "-vn",
                    "-f",
                    "s16le",
                    "-acodec",
                    "pcm_s16le",
                    "-ar",
                    "48000",
                    "-ac",
                    "2",
                    "pipe:1"
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            print("Streaming audio chunks...")
            started_playback = False
            while True:
                if self._current_video != videoId or self._playback_state == "stopped":
                    break

                if self._playback_state == "paused":
                    threading.Event().wait(0.1)
                    continue

                if not self._download_process or not self._download_process.stdout:
                    break

                data = self._download_process.stdout.read(8192)
                if not data:
                    break

                if not started_playback:
                    started_playback = True
                    self._set_state("playing")

                if self._audio_device:
                    self._audio_device.feed(data)

            print("Stream finished buffering for:", videoId)
        except Exception as e:
            print("Streaming error:", e)
            self._set_state("stopped")

    @Slot()
    def pause(self):
        if self._playback_state == "playing":
            if self._audio_sink:
                self._audio_sink.suspend()
            self._set_state("paused")

    @Slot()
    def resume(self):
        if self._playback_state == "paused":
            if self._audio_sink:
                self._audio_sink.resume()
            self._set_state("playing")

    @Slot()
    def toggle_play_pause(self):
        if self._playback_state == "playing":
            self.pause()
        elif self._playback_state == "paused":
            self.resume()
        elif self._current_video:
            self.play_song(self._current_video)
        elif hasattr(self, "_last_video") and self._last_video:
            self.play_song(self._last_video)

    @Slot()
    def stop(self):
        self._stop_stream()
        self._set_state("stopped")

    def _stop_stream(self):
        if self._current_video:
            self._last_video = self._current_video
        self._current_video = None
        if self._download_process:
            try:
                self._download_process.kill()
            except Exception:
                pass
            self._download_process = None

        if self._audio_sink:
            try:
                self._audio_sink.stop()
            except Exception:
                pass
            self._audio_sink = None

        self._audio_device = None

    def _set_state(self, new_state):
        if self._playback_state != new_state:
            self._playback_state = new_state
            self.playbackStateChanged.emit(new_state)

    @Slot(float)
    def volume_change(self, value):
        self._volume = max(0.0, min(1.0, float(value)))
        self.audio.setVolume(self._volume)
        if self._audio_sink:
            self._audio_sink.setVolume(self._volume)
        self.volumeChanged.emit(self._volume)

    @Slot(float)
    def set_volume(self, value):
        self.volume_change(value)
