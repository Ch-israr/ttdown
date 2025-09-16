const storiesForm = document.getElementById('storiesForm');
const storyMessage = document.getElementById('storyMessage');

storiesForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  storyMessage.textContent = "Fetching story...";
  storyMessage.style.display = "block";

  const formData = new FormData(storiesForm);
  const response = await fetch('/download_story', { method: 'POST', body: formData });

  const result = await response.json();
  if (result.error) {
    storyMessage.textContent = "❌ " + result.error;
    storyMessage.classList.add("error");
  } else {
    storyMessage.textContent = "✅ " + result.message;
    storyMessage.classList.add("success");
  }
});
