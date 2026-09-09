from ytmusicapi import YTMusic
import subprocess
import sys
import os
import tempfile
import glob
import threading
import queue

from PySide6.QtCore import (
    QObject,
    Slot,
    Signal,
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
        self.open(
            QIODevice.ReadOnly
        )

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

            return (
                len(self.buffer)
                + super().bytesAvailable()
            )


class MusicPlayer(QObject):

    searchResults = Signal(list)

    def __init__(self):
        super().__init__()

        self.yt = YTMusic()

        self.audio = QAudioOutput()
        self.player = QMediaPlayer()

        self.player.setAudioOutput(
            self.audio
        )

        self.audio.setVolume(
            1.0
        )

        self.player.errorOccurred.connect(
            self._on_player_error
        )

        self._temp_dir = tempfile.mkdtemp(
            prefix="music_player_"
        )

        self._download_process = None
        self._current_video = None

        self._audio_sink = None
        self._audio_device = None

        self._stream_thread = None

    @Slot(str)
    def search_music(self, query):

        results = self.yt.search(
            query,
            filter="songs"
        )

        songs = []

        for song in results:

            songs.append({
                "title": song["title"],
                "artist": song["artists"][0]["name"],
                "videoId": song["videoId"]
            })

        self.searchResults.emit(
            songs
        )

    @Slot(str)
    def play_song(self, videoId):

        self._stop_stream()

        self._current_video = videoId

        print(
            "Playing:",
            videoId
        )

        # Create audio format
        format = QAudioFormat()

        format.setSampleRate(
            48000
        )

        format.setChannelCount(
            2
        )

        format.setSampleFormat(
            QAudioFormat.Int16
        )

        # Create our streaming device
        self._audio_device = AudioBuffer()

        self._audio_device.start()

        # Create audio sink
        self._audio_sink = QAudioSink(
            format,
            self
        )

        self._audio_sink.setVolume(
            1.0
        )

        # Start audio output
        self._audio_sink.start(
            self._audio_device
        )

        # Start network/FFmpeg thread
        self._stream_thread = threading.Thread(
            target=self._stream_song,
            args=(videoId,),
            daemon=True
        )

        self._stream_thread.start()

    def _stream_song(self, videoId):

        url = (
            "https://www.youtube.com/watch?v="
            + videoId
        )

        print(
            "Getting audio stream..."
        )

        # Resolve direct YouTube audio URL
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
            text=True
        )

        if result.returncode != 0:

            print(
                "yt-dlp FAILED:",
                result.stderr[-1000:]
            )

            return

        stream_url = result.stdout.strip()

        if not stream_url:

            print(
                "No stream URL returned"
            )

            return

        print(
            "Stream URL obtained"
        )

        # FFmpeg converts directly to PCM.
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

        print(
            "Streaming..."
        )

        while True:

            if self._current_video != videoId:
                break

            data = (
                self._download_process
                .stdout
                .read(8192)
            )

            if not data:
                break

            if self._audio_device:

                self._audio_device.feed(
                    data
                )

        print(
            "Stream ended"
        )

    def _stop_stream(self):

        self._current_video = None

        if self._download_process:

            try:
                self._download_process.kill()

            except:
                pass

            self._download_process = None

        if self._audio_sink:

            try:
                self._audio_sink.stop()

            except:
                pass

            self._audio_sink = None

        self._audio_device = None

    @Slot(float)
    def volume_change(self, value):

        self.audio.setVolume(
            value
        )

        if self._audio_sink:

            self._audio_sink.setVolume(
                value
            )

    def _on_player_error(
        self,
        error,
        error_string
    ):

        if error == QMediaPlayer.NoError:
            return

        print(
            "PLAYER ERROR:",
            error,
            error_string
        )
