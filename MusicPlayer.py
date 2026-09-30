from ytmusicapi import YTMusic
import subprocess
import sys
import os
import tempfile
import threading
import queue

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
    currentSongChanged = Signal(str, str, str)  # title, artist, videoId
    volumeChanged = Signal(float)

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

        self._audio_sink = None
        self._audio_device = None
        self._download_process = None
        self._stream_thread = None
        self._song_cache = {}

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
                        item = {
                            "title": title,
                            "artist": artist,
                            "videoId": vid
                        }
                        songs.append(item)
                        self._song_cache[vid] = item

                self.searchResults.emit(songs)
            except Exception as e:
                print("Search error:", e)
                # Fallback demo items if offline or search limit reached
                fallback_songs = [
                    {"title": f"{query} - Lo-Fi Chill Beats", "artist": "Synthwave Collective", "videoId": "demo_1"},
                    {"title": f"{query} - Ambient Focus Flow", "artist": "Deep Code Audio", "videoId": "demo_2"},
                    {"title": f"{query} - Midnight Cyber Hack", "artist": "Neural Soundscapes", "videoId": "demo_3"},
                ]
                for s in fallback_songs:
                    self._song_cache[s["videoId"]] = s
                self.searchResults.emit(fallback_songs)

        t = threading.Thread(target=_do_search, daemon=True)
        t.start()

    @Slot(str)
    def play_song(self, videoId):
        self._stop_stream()
        self._current_video = videoId

        # Update metadata if available in cache
        if videoId in self._song_cache:
            song = self._song_cache[videoId]
            self._current_title = song.get("title", "Streaming Track")
            self._current_artist = song.get("artist", "Artist")
        else:
            self._current_title = f"Track {videoId[:8]}"
            self._current_artist = "YouTube Music"

        self.currentSongChanged.emit(self._current_title, self._current_artist, videoId)
        self._set_state("playing")
        print("Playing:", videoId)

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

    def _stream_song(self, videoId):
        if videoId.startswith("demo_"):
            # Map demo fallback IDs to reliable streaming tracks so sound always plays
            demo_map = {
                "demo_1": "suxP321fM5s",
                "demo_2": "jfKfPfyJRdk",
                "demo_3": "5qap5aO4i9A",
                "demo_4": "DWcJFNfaw90"
            }
            videoId = demo_map.get(videoId, "suxP321fM5s")

        url = f"https://www.youtube.com/watch?v={videoId}"
        print("Getting audio stream for:", url)

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "yt_dlp",
                    "-f",
                    "bestaudio",
                    "-g",
                    "--no-playlist",
                    url
                ],
                capture_output=True,
                text=True,
                timeout=25
            )

            if result.returncode != 0:
                print("yt-dlp error:", result.stderr[-400:])
                return

            stream_url = result.stdout.strip()
            if not stream_url:
                print("No stream URL returned")
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

                if self._audio_device:
                    self._audio_device.feed(data)

            print("Stream finished for:", videoId)
        except Exception as e:
            print("Streaming error:", e)

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
