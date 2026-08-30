from ytmusicapi import YTMusic
import subprocess
import sys
from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

print("MUSIC PLAYER LOADED")
yt = YTMusic()

audio = QAudioOutput()
player = QMediaPlayer()

player.setAudioOutput(audio)
audio.setVolume(1.0)

results = yt.search("Blinding Lights", filter="songs")

for song in results:
    print(song["title"])

song = results[0]
video_id = song["videoId"]

print(song["title"])
print(song["videoId"])

result = subprocess.run(
    [
        sys.executable,
        "-m",
        "yt_dlp",
        "-f", "140",
        "-g",
        f"https://www.youtube.com/watch?v={video_id}"
    ],
    capture_output=True,
    text=True
)

url = result.stdout.strip()
print("URL GOT:", bool(url))

player.setSource(QUrl(url))
player.play()
