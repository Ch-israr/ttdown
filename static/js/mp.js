document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("mp3-form");
  const urlInput = document.getElementById("mp3-url");
  const spinner = document.getElementById("spinner");
  const messageBox = document.getElementById("message");
  const previewCard = document.getElementById("preview");
  const previewThumbnail = document.getElementById("preview-thumbnail");
  const previewTitle = document.getElementById("preview-title");
  const previewAudio = document.getElementById("preview-audio");
  const downloadLink = document.getElementById("download-link");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const url = urlInput.value.trim();
    if (!url) return;

    // Reset UI
    messageBox.textContent = "";
    previewCard.style.display = "none";
    spinner.style.display = "block";

    try {
      // Step 1: Fetch metadata (thumbnail, title)
      const metaResp = await fetch("/thumbnail", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url })
      });
      const metaData = await metaResp.json();
      if (!metaData.ok) {
        spinner.style.display = "none";
        messageBox.textContent = metaData.error || "Failed to fetch metadata.";
        return;
      }

      // Step 2: Fetch MP3
      const mp3Resp = await fetch("/download-mp3", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url })
      });
      const mp3Data = await mp3Resp.json();
      spinner.style.display = "none";

      if (!mp3Data.ok) {
        messageBox.textContent = mp3Data.error || "MP3 conversion failed.";
        return;
      }

      // Display preview
      previewThumbnail.src = metaData.thumbnail || "";
      previewTitle.textContent = mp3Data.title || "TikTok Audio";
      previewAudio.src = mp3Data.url;
      downloadLink.href = mp3Data.url;
      downloadLink.download = `${mp3Data.title || "audio"}.mp3`;
      previewCard.style.display = "block";

    } catch (err) {
      spinner.style.display = "none";
      messageBox.textContent = "Error: " + err.message;
    }
  });
});
