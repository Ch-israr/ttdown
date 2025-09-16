# TikTok Downloader Pro

A simple Flask-based TikTok downloader web app with:
- Thumbnail preview under input
- Video download (yt-dlp primary, multiple fallbacks)
- MP3 extraction via yt-dlp + FFmpeg (optional)
- Separate APK "coming soon" page
- Clean responsive UI inspired by SSSTik look

## Quickstart (dev)
1. Clone or copy this folder.
2. Create a Python venv (recommended) and activate it:
python -m venv venv
source venv/bin/activate # macOS / Linux
venv\Scripts\activate # Windows
3. Install dependencies:
pip install -r requirements.txt
4. **(If you want MP3)** Install ffmpeg on your system so yt-dlp can convert to mp3.
- Ubuntu/Debian: `sudo apt install ffmpeg`
- macOS (Homebrew): `brew install ffmpeg`
- Windows: download from https://ffmpeg.org and add to PATH

5. Run the app:
python app.py
6. Open http://127.0.0.1:5000

## What changed vs earlier version
- Thumbnail preview: API endpoint `/thumbnail` returns metadata and thumbnail; UI displays it under the input box.
- APK: separate page `/apk` shows "APP is coming soon".
- MP3: endpoint `/download-mp3` implemented using yt-dlp + FFmpeg (system-level).

## Notes
- TikTok frequently changes site internals and may block automated fetches — if a method fails, the app tries multiple fallbacks.
- Always respect copyright and TikTok terms when downloading content.
- For production, add rate-limiting, caching, and user input sanitization.

## Development guide
See `DEVELOP.md` for step-by-step instructions on how to add features like TikTok Stories downloader, improve MP3 conversion reliability, and other enhancements.

