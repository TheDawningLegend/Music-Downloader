import os
import subprocess

import yt_dlp
import imageio_ffmpeg
from PIL import Image
from mutagen.easyid3 import EasyID3
from mutagen.id3 import error


FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

raw_input = input("Enter YouTube Playlist ID, YouTube URL, or YouTube Music URL:\n> ").strip()
if raw_input.startswith("http"):
    PLAYLIST_URL = raw_input
else:
    PLAYLIST_URL = f"https://www.youtube.com/playlist?list={raw_input}"

desktop = os.path.join(os.path.expanduser("~"), "Desktop", "MusicDL")
TARGET_DIR = input(f"Enter target directory (default: {desktop}): ").strip()
if not TARGET_DIR:
    TARGET_DIR = desktop

os.makedirs(TARGET_DIR, exist_ok=True)

def download_music():
    ydl_opts = {
        "ffmpeg_location": FFMPEG_PATH,
        "format": "bestaudio/best",
        "outtmpl": os.path.join(TARGET_DIR, "%(album)s", "%(playlist_index)02d - %(title)s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            },
            {"key": "EmbedThumbnail"},
            {"key": "FFmpegMetadata"},
        ],
        "writethumbnail": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([PLAYLIST_URL])

def crop_to_square(image_path):
    with Image.open(image_path) as im:
        w, h = im.size
        m = min(w, h)
        left, top = (w - m) // 2, (h - m) // 2
        square = im.crop((left, top, left + m, top + m))
        square.save(image_path, format="JPEG")

def extract_cover(mp3_path, out_jpg):
    try:
        subprocess.run([FFMPEG_PATH, "-y", "-i", mp3_path, "-an", "-vcodec", "copy", out_jpg],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

def replace_cover(mp3_path, new_cover_path):
    temp_output = mp3_path + ".temp.mp3"
    try:
        subprocess.run([
            FFMPEG_PATH, "-y", "-i", mp3_path, "-i", new_cover_path,
            "-map", "0", "-map", "1", "-c", "copy",
            "-id3v2_version", "3",
            "-metadata:s:v", "title=Album cover",
            "-metadata:s:v", "comment=Cover (front)",
            temp_output
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.replace(temp_output, mp3_path)
    except subprocess.CalledProcessError:
        if os.path.exists(temp_output):
            os.remove(temp_output)

def set_track_number(mp3_path):
    basename = os.path.basename(mp3_path)
    try:
        track_str = basename.split(" ")[0]
        track_num = int(''.join(filter(str.isdigit, track_str)))
    except Exception:
        return
    try:
        audio = EasyID3(mp3_path)
    except error.ID3NoHeaderError:
        audio = EasyID3()
        audio.save(mp3_path)
        audio = EasyID3(mp3_path)

    audio["tracknumber"] = str(track_num)
    audio.save()

def process_folder(folder):
    for file in sorted(os.listdir(folder)):
        if file.lower().endswith(".mp3"):
            mp3_path = os.path.join(folder, file)
            temp_jpg = os.path.join(folder, "cover_temp.jpg")
            if extract_cover(mp3_path, temp_jpg):
                crop_to_square(temp_jpg)
                replace_cover(mp3_path, temp_jpg)
                os.remove(temp_jpg)
            set_track_number(mp3_path)

def fix_music():
    for root, _, files in os.walk(TARGET_DIR):
        if any(f.lower().endswith(".mp3") for f in files):
            process_folder(root)

if __name__ == "__main__":
    print("Downloading music...")
    download_music()
    print("Fixing metadata and covers...")
    fix_music()
    print("Done! All music saved in:", TARGET_DIR)