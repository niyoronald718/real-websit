import { getDownloads, saveDownloads } from "../core/storage.js";
import { cancelDownload, removeDownload } from "../core/download-manager.js";
import { escapeHTML } from "../core/api.js";

let filter = "all";
const root = document.querySelector("#download-list");

function render() {
  const entries = getDownloads().filter(entry => filter === "all" || (filter === "active" ? ["queued", "downloading"].includes(entry.status) : entry.status === filter));
  root.innerHTML = entries.map(entry => {
    const percent = Math.min(100, Math.max(0, Number(entry.progress) || 0));
    const size = Number(entry.size);
    const startedAt = new Date(entry.startedAt);
    const date = Number.isNaN(startedAt.getTime()) ? "Date unavailable" : startedAt.toLocaleString();
    return `<article class="download-item"><div><strong>${escapeHTML(entry.title)}</strong><div class="muted">${escapeHTML(entry.variant)} · ${size > 0 ? `${(size / 1024 / 1024).toFixed(1)} MB` : "Size unknown"} · ${escapeHTML(date)}</div><div class="progress"><span style="width:${percent}%"></span></div><small class="muted">${escapeHTML(entry.status)}${entry.error ? `: ${escapeHTML(entry.error)}` : ""}</small></div><div>${["queued", "downloading"].includes(entry.status) ? `<button data-cancel="${escapeHTML(entry.id)}" class="button button-secondary">Cancel</button>` : `<button data-remove="${escapeHTML(entry.id)}" class="button button-secondary">Remove</button>`}</div></article>`;
  }).join("") || '<p class="muted">No downloads tracked on this device.</p>';
  root.querySelectorAll("[data-cancel]").forEach(button => button.addEventListener("click", () => cancelDownload(button.dataset.cancel)));
  root.querySelectorAll("[data-remove]").forEach(button => button.addEventListener("click", () => removeDownload(button.dataset.remove)));
}

document.querySelector("#download-filters").addEventListener("click", event => {
  const button = event.target.closest("button[data-filter]");
  if (!button) return;
  filter = button.dataset.filter;
  document.querySelectorAll("#download-filters button").forEach(item => item.classList.toggle("active", item === button));
  render();
});
window.addEventListener("downloads:changed", render);
window.addEventListener("storage", event => { if (event.key === "downloads") render(); });
render();
