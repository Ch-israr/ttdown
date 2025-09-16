DEVELOPMENT & FEATURE GUIDE (casual / step-by-step)
Hey — this file walks you through how to add features you're asking for:
- TikTok Stories downloader
- Better MP3 support
- APK page (already added)
We keep it short + actionable.

---

1) Thumbnail preview (already implemented)
- Endpoint: POST /thumbnail (JSON: {url})
- Uses yt-dlp -> TikTokApi -> page-scrape fallback
- Frontend shows thumbnail card under input with title/uploader

If you want to tweak UI:
- Edit templates/index.html -> #thumbnailCard markup
- Edit static/js/script.js -> function `fetchThumbnail(url)` for debounce & UX

---

2) Add "Download TikTok Stories" feature (step-by-step)
Stories require a different approach than normal posts. TikTok often provides ephemeral "stories" via OR specific endpoints.

Step A — Research:
- Check if TikTokApi version you installed exposes "stories" or "user stories" endpoints (APIs change often).
- If TikTokApi supports it, you can call something like:
  ```py
  api = TikTokApi()
  stories = api.user(username="username").stories()
