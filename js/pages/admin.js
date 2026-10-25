import { api, escapeHTML } from "../core/api.js";

const loginPanel = document.querySelector("#login-panel");
const dashboard = document.querySelector("#dashboard");
let csrf = "";

async function adminApi(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.method && options.method !== "GET") headers.set("X-CSRF-Token", csrf);
  return api(path, { ...options, headers });
}

async function showDashboard() {
  const stats = await adminApi("/admin/api/stats");
  document.querySelector("#stats").innerHTML = Object.entries({ "All titles": stats.movies, Published: stats.published, Views: stats.views, Downloads: stats.downloads }).map(([label, value]) => `<div class="stat-card"><span>${label}</span><strong>${value}</strong></div>`).join("");
  const movies = await adminApi("/admin/api/movies");
  document.querySelector("#admin-movies").innerHTML = movies.items.map(movie => `<article class="admin-movie"><div><strong>${escapeHTML(movie.title)}</strong><div class="muted">${escapeHTML(movie.slug)} · ${movie.is_published ? "Published" : "Draft"} · ${movie.video_path ? "Video ready" : "No video"}</div><form data-upload="${movie.id}"><input type="file" name="file" accept="video/mp4,video/webm" required><button>Upload video</button></form></div><button data-delete="${movie.id}" aria-label="Delete ${escapeHTML(movie.title)}">Delete</button></article>`).join("") || '<p class="muted">No titles.</p>';
  document.querySelectorAll("[data-upload]").forEach(form => form.addEventListener("submit", async event => {
    event.preventDefault();
    const formData = new FormData(form);
    formData.set("kind", "video");
    const response = await fetch(`/admin/api/movies/${form.dataset.upload}/upload`, { method: "POST", body: formData, headers: { "X-CSRF-Token": csrf } });
    const result = await response.json();
    if (!response.ok) alert(result.error || "Upload failed");
    else await showDashboard();
  }));
  document.querySelectorAll("[data-delete]").forEach(button => button.addEventListener("click", async () => {
    if (!confirm("Delete this title?")) return;
    try { await adminApi(`/admin/api/movies/${button.dataset.delete}`, { method: "DELETE" }); await showDashboard(); }
    catch (error) { alert(error.message); }
  }));
  loginPanel.hidden = true;
  dashboard.hidden = false;
}

document.querySelector("#login-form").addEventListener("submit", async event => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const response = await fetch("/admin/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(Object.fromEntries(form)) });
  const result = await response.json();
  if (!response.ok) { document.querySelector("#login-error").textContent = result.error || "Sign-in failed"; return; }
  csrf = result.csrf_token;
  try { await showDashboard(); }
  catch (error) { document.querySelector("#login-error").textContent = error.message; }
});

document.querySelector("#movie-form").addEventListener("submit", async event => {
  event.preventDefault();
  const values = Object.fromEntries(new FormData(event.currentTarget));
  values.is_published = event.currentTarget.elements.is_published.checked;
  values.is_downloadable = event.currentTarget.elements.is_downloadable.checked;
  try {
    await adminApi("/admin/api/movies", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(values) });
    event.currentTarget.reset();
    await showDashboard();
  } catch (error) { document.querySelector("#movie-error").textContent = error.message; }
});

document.querySelector("#logout").addEventListener("click", async () => {
  try { await adminApi("/admin/logout", { method: "POST" }); location.reload(); }
  catch (error) { alert(error.message); }
});
