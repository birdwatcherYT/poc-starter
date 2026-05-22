const out = document.getElementById("out");
const form = document.getElementById("echo-form");
const messageInput = document.getElementById("message");
const authorInput = document.getElementById("author");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  out.textContent = "loading...";
  const body = {
    message: messageInput.value,
    author: authorInput.value || null,
  };
  try {
    const res = await fetch("/example/echo", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      out.textContent = `HTTP ${res.status}: ${await res.text()}`;
      return;
    }
    out.textContent = JSON.stringify(await res.json(), null, 2);
  } catch (err) {
    out.textContent = `error: ${err.message}`;
  }
});
