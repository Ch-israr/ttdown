// Debounce helper
function debounce(fn, delay) {
  let t;
  return function (...args) {
    clearTimeout(t);
    t = setTimeout(() => fn.apply(this, args), delay);
  };
}

// DOM elements
const urlInput = document.getElementById("urlInput");
const thumbnailCard = document.getElementById("thumbnailCard");
const thumbImg = document.getElementById("thumbImg");
const videoTitle = document.getElementById("videoTitle");
const videoUploader = document.getElementById("videoUploader");
const messageBox = document.getElementById("message");
const downloadForm = document.getElementById("downloadForm");
const downloadMp3Btn = document.getElementById("downloadMp3Btn");
const previewBtn = document.getElementById("previewBtn");
const downloadBtn = document.getElementById("downloadBtn");

// hide helper
function hide(el) { if (el && !el.classList.contains('hidden')) el.classList.add('hidden'); }
function show(el) { if (el && el.classList.contains('hidden')) el.classList.remove('hidden'); }

// Show messages
function setMessage(msg, isError=false) {
  messageBox.textContent = msg;
  if (isError) { messageBox.style.background = "rgba(255,0,0,0.15)"; }
  else { messageBox.style.background = "rgba(255,255,255,0.15)"; }
  show(messageBox);
}

// Fetch thumbnail metadata
async function fetchThumbnail(url) {
  hide(thumbnailCard);
  if (!url || url.length < 6) return;
  setMessage("Fetching preview...");
  try {
    const res = await fetch("/thumbnail", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({url})
    });
    const data = await res.json();
    if (!data.ok) {
      setMessage("Preview not available: " + (data.error || "unknown"), true);
      return;
    }
    // populate card
    if (data.thumbnail) thumbImg.src = data.thumbnail;
    else thumbImg.src = "/static/images/placeholder-thumbnail.png";
    videoTitle.textContent = data.title || "No title available";
    videoUploader.textContent = data.uploader ? "By: " + data.uploader : "";
    show(thumbnailCard);
    setMessage("Preview loaded!");
  } catch (err) {
    console.error(err);
    setMessage("Could not fetch preview", true);
  }
}

// Debounced version to avoid too many calls
const debouncedFetch = debounce((val) => fetchThumbnail(val), 700);

// Listen to input changes
urlInput.addEventListener("input", (e) => {
  const val = e.target.value.trim();
  debouncedFetch(val);
});

// Form submit for video download
downloadForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const url = urlInput.value.trim();
  if (!url) { setMessage("Paste a TikTok URL first", true); return; }
  setMessage("Preparing download...");
  try {
    // Use FormData to submit to /download (video)
    const formData = new FormData(downloadForm);
    const res = await fetch("/download", { method: "POST", body: formData });
    if (!res.ok) {
      const text = await res.text();
      setMessage("Download failed: " + text, true);
      return;
    }
    const blob = await res.blob();
    const contentDisposition = res.headers.get("content-disposition") || "";
    let filename = "tiktok_video.mp4";
    const match = contentDisposition.match(/filename\*?=([^;]+)/);
    if (match) {
      filename = match[1].replace(/['"]/g, "").trim();
    }
    const urlBlob = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = urlBlob;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(urlBlob);
    setMessage("Download completed!");
  } catch (err) {
    console.error(err);
    setMessage("Error while downloading video.", true);
  }
});

// Download MP3 button
downloadMp3Btn.addEventListener("click", async () => {
  const url = urlInput.value.trim();
  if (!url) { setMessage("Paste a TikTok URL first", true); return; }
  setMessage("Preparing MP3...");
  try {
    const fd = new FormData();
    fd.append("url", url);
    const res = await fetch("/download-mp3", { method: "POST", body: fd });
    if (!res.ok) {
      const text = await res.text();
      setMessage("MP3 failed: " + text, true);
      return;
    }
    const blob = await res.blob();
    const urlBlob = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = urlBlob;
    a.download = "audio.mp3";
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(urlBlob);
    setMessage("MP3 downloaded!");
  } catch (err) {
    console.error(err);
    setMessage("Error while downloading MP3.", true);
  }
});

// Preview video in a new tab (direct URL of original page)
previewBtn.addEventListener("click", () => {
  const url = urlInput.value.trim();
  if (!url) { setMessage("Paste a TikTok URL first", true); return; }
  window.open(url, "_blank");
});
