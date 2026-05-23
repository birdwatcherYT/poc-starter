const messageOut = document.getElementById("message-out");
const messageForm = document.getElementById("message-form");
const messageInput = document.getElementById("message");
const authorInput = document.getElementById("author");

const documentOut = document.getElementById("document-out");
const documentForm = document.getElementById("document-form");
const docTitleInput = document.getElementById("doc-title");
const docContentInput = document.getElementById("doc-content");

const similarOut = document.getElementById("similar-out");
const similarForm = document.getElementById("similar-form");
const similarQueryInput = document.getElementById("similar-query");

async function requestJson(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  }
  return res.json();
}

function showResult(el, data) {
  el.textContent = JSON.stringify(data, null, 2);
}

function showError(el, err) {
  el.textContent = `error: ${err.message}`;
}

messageForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  messageOut.textContent = "loading...";
  try {
    const body = {
      message: messageInput.value,
      author: authorInput.value || null,
    };
    showResult(
      messageOut,
      await requestJson("/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    );
  } catch (err) {
    showError(messageOut, err);
  }
});

documentForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  documentOut.textContent = "loading...";
  try {
    const body = {
      title: docTitleInput.value,
      content: docContentInput.value,
    };
    showResult(
      documentOut,
      await requestJson("/documents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    );
  } catch (err) {
    showError(documentOut, err);
  }
});

similarForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  similarOut.textContent = "loading...";
  try {
    const q = encodeURIComponent(similarQueryInput.value);
    showResult(similarOut, await requestJson(`/documents/similar?q=${q}`));
  } catch (err) {
    showError(similarOut, err);
  }
});
