"""
TikTok Downloader Pro - Flask backend

Features:
- /            -> index page
- /apk         -> "App is coming soon" page
- /thumbnail   -> POST (JSON) -> returns thumbnail + meta for given TikTok URL
- /download    -> POST (form) -> downloads video (uses yt-dlp primary, TikTokApi fallback, HTML-scrape fallback)
- /download-mp3-> POST (form) -> downloads audio as mp3 (yt-dlp with FFmpeg postprocessor preferred)

Notes:
- Make sure 'downloads/' folder exists (created at startup)
- For MP3 conversion, ffmpeg must be installed on the system.
"""

import os
import io
import re
import uuid
import shutil
import logging
from flask import Flask, render_template, request, jsonify, send_file, abort
from pathlib import Path

# Attempt imports for primary libraries
try:
    import yt_dlp
except Exception:
    yt_dlp = None

try:
    from TikTokApi import TikTokApi
except Exception:
    TikTokApi = None

import requests
from bs4 import BeautifulSoup

# Configuration
APP_DIR = Path(__file__).parent
DOWNLOADS_DIR = APP_DIR / "downloads"
DOWNLOADS_DIR.mkdir(exist_ok=True)

logging.basicConfig(filename=str(APP_DIR / "app.log"), level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")

app = Flask(__name__, static_folder="static", template_folder="templates")


def _safe_clean_path(p: Path):
    """Ensure path is inside downloads - prevent path traversal"""
    try:
        p = p.resolve()
        if DOWNLOADS_DIR.resolve() not in p.parents and p != DOWNLOADS_DIR.resolve():
            raise ValueError("Path outside downloads")
    except Exception:
        raise


def extract_meta_with_ytdlp(url: str):
    """Try to get metadata (title, thumbnail, uploader) using yt-dlp (fast, reliable)."""
    if not yt_dlp:
        return None
    ydl_opts = {"quiet": True, "no_warnings": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            out = {
                "title": info.get("title") or "",
                "thumbnail": info.get("thumbnail") or (info.get("thumbnails") and info.get("thumbnails")[-1].get("url")),
                "uploader": info.get("uploader") or info.get("uploader_id") or ""
            }
            return out
    except Exception as e:
        logging.info(f"yt-dlp metadata failed for {url}: {e}")
        return None


def extract_meta_with_tiktokapi(url: str):
    """Fallback: try TikTokApi to fetch metadata (best-effort)."""
    if not TikTokApi:
        return None
    try:
        # TikTokApi usage can vary; this is a defensive attempt. Users may need to adjust per installed version.
        api = TikTokApi()
        video = api.video(url=url)
        # Many TikTokApi versions return a bytes() method for the video object and metadata inside
        meta = {}
        try:
            info = video.as_dict()
        except Exception:
            info = {}
        meta["title"] = info.get("desc") or ""
        meta["uploader"] = info.get("author", {}).get("uniqueId") if info.get("author") else ""
        # cover or coverUrl fields
        meta["thumbnail"] = info.get("video", {}).get("cover") or info.get("cover") or ""
        return meta
    except Exception as e:
        logging.info(f"TikTokApi metadata failed for {url}: {e}")
        return None


def extract_meta_by_scraping(url: str):
    """Scrape the page and try to find og:image and og:description"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        thumb = ""
        title = ""
        uploader = ""

        og_img = soup.find("meta", property="og:image")
        if og_img and og_img.get("content"):
            thumb = og_img["content"]

        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = og_title["content"]

        description = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", property="og:description")
        if description and description.get("content"):
            # description often contains uploader or caption
            uploader = description["content"][:200]

        return {"title": title, "thumbnail": thumb, "uploader": uploader}
    except Exception as e:
        logging.info(f"Scrape meta failed for {url}: {e}")
        return None


def extract_thumbnail_info(url: str):
    """Combined attempt to get thumbnail and basic meta"""
    # Prefer yt-dlp
    data = extract_meta_with_ytdlp(url)
    if data:
        return data
    # Then TikTokApi
    data = extract_meta_with_tiktokapi(url)
    if data:
        return data
    # Then scraping
    data = extract_meta_by_scraping(url)
    if data:
        return data
    return {"title": "", "thumbnail": "", "uploader": ""}


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/")
def home():
    return "TikTok Downloader Running Inside Docker 🚀"

@app.route('/stories')
def stories_page():
    return render_template('stories.html')

@app.route('/mp')
def mp3_page():
    return render_template('mp.html')

@app.route('/contact')
def contact_page():
    return render_template('contact.html')

@app.route('/privacy')
def privacy_page():
    return render_template('privacy.html')

@app.route("/apk")
def apk():
    return render_template("apk.html")


@app.route("/thumbnail", methods=["POST"])
def thumbnail():
    """
    POST JSON: { "url": "https://www.tiktok.com/..." }
    Response JSON: { "ok": True, "title": "...", "thumbnail": "...", "uploader": "..." }
    """
    data = request.get_json(force=True, silent=True) or request.form
    url = data.get("url")
    if not url:
        return jsonify({"ok": False, "error": "No URL provided"}), 400
    try:
        meta = extract_thumbnail_info(url)
        if not meta:
            return jsonify({"ok": False, "error": "Could not extract metadata"}), 500
        return jsonify({"ok": True, **meta})
    except Exception as e:
        logging.exception("thumbnail extraction failed")
        return jsonify({"ok": False, "error": str(e)}), 500


def generate_unique_outtmpl():
    """Generates a unique output template into downloads directory to avoid collisions."""
    unique = uuid.uuid4().hex
    return str(DOWNLOADS_DIR / f"{unique}_%(title)s.%(ext)s")


@app.route("/download", methods=["POST"])
def download_video():
    """
    Downloads the video and returns the file as attachment.
    POST form fields: url (required), quality (optional e.g. 'best' or 'worst' or yt-dlp format string)
    """
    url = request.form.get("url") or (request.get_json(silent=True) or {}).get("url")
    quality = request.form.get("quality") or request.args.get("quality") or "best"
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    logging.info(f"Starting video download for {url} quality={quality}")

    # Attempt with yt-dlp
    if yt_dlp:
        # Outtmpl unique to avoid clashes
        outtmpl = generate_unique_outtmpl()
        ydl_opts = {
            "format": quality if quality in ("best", "worst") else quality,
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
            # retry and error handling
            "retries": 2,
            "noprogress": True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                # Prepare filename (actual ext filled by prepare_filename)
                filename = ydl.prepare_filename(info)
                # Now download
                ydl.download([url])
                # In some cases, prepare_filename returns without final extension (but usually correct)
                final_path = Path(filename)
                if not final_path.exists():
                    # try find any file that starts with same base name inside downloads
                    candidates = list(DOWNLOADS_DIR.glob(f"*{final_path.stem}*"))
                    if candidates:
                        final_path = candidates[0]
                _safe_clean_path(final_path)
                return send_file(str(final_path), as_attachment=True)
        except Exception as e:
            logging.exception(f"yt-dlp download failed for {url}: {e}")

    # Fallback: TikTokApi to fetch raw bytes (may not work in all envs)
    if TikTokApi:
        try:
            api = TikTokApi()
            video = api.video(url=url)
            video_bytes = video.bytes()
            if video_bytes:
                bio = io.BytesIO(video_bytes)
                bio.seek(0)
                return send_file(bio, download_name="tiktok_video.mp4", as_attachment=True, mimetype="video/mp4")
        except Exception as e:
            logging.exception(f"TikTokApi fallback download failed for {url}: {e}")

    # Final fallback: try to scrape page and find raw video url (best-effort)
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            # Find video src via og:video or javascript JSON data
            soup = BeautifulSoup(r.text, "html.parser")
            og_video = soup.find("meta", property="og:video")
            if og_video and og_video.get("content"):
                video_url = og_video["content"]
                r2 = requests.get(video_url, headers=headers, timeout=15, stream=True)
                if r2.status_code == 200:
                    temp_path = DOWNLOADS_DIR / f"{uuid.uuid4().hex}_video.mp4"
                    with open(temp_path, "wb") as f:
                        shutil.copyfileobj(r2.raw, f)
                    _safe_clean_path(temp_path)
                    return send_file(str(temp_path), as_attachment=True)
        logging.error(f"All download methods failed for {url}")
        return render_template("error.html", message="All download methods failed. Check logs.")
    except Exception as e:
        logging.exception("Final fallback download failed")
        return render_template("error.html", message=str(e))


@app.route("/download-mp3", methods=["POST"])
def download_mp3():
    """
    Convert and download audio as MP3.
    POST form fields: url (required), quality (optional)
    Requires system 'ffmpeg' for conversion (used by yt-dlp postprocessor).
    """
    url = request.form.get("url") or (request.get_json(silent=True) or {}).get("url")
    preferred_quality = request.form.get("quality") or "192"
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    logging.info(f"Starting mp3 download for {url}")

    if not yt_dlp:
        return render_template("error.html", message="yt-dlp is required for MP3 extraction. Install yt-dlp.")

    outtmpl = generate_unique_outtmpl()
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": str(preferred_quality),
            }
        ],
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            filename_noext = ydl.prepare_filename(info)
            # Download + postprocess (convert to mp3)
            ydl.download([url])

            # The final mp3 file usually has .mp3 extension
            mp3_path = Path(filename_noext).with_suffix(".mp3")
            if not mp3_path.exists():
                # find candidate
                candidates = list(DOWNLOADS_DIR.glob(f"*{Path(filename_noext).stem}*.mp3"))
                if candidates:
                    mp3_path = candidates[0]
            _safe_clean_path(mp3_path)
            return send_file(str(mp3_path), as_attachment=True, download_name=f"{mp3_path.name}")
    except Exception as e:
        logging.exception("MP3 extraction with yt-dlp failed")
        return render_template("error.html", message=f"MP3 extraction failed: {e}")


@app.errorhandler(500)
def internal_err(e):
    logging.exception("Internal server error")
    return render_template("error.html", message="Internal server error"), 500

if __name__ == "__main__":
    app.run(debug=False, port=5000, host="0.0.0.0")


