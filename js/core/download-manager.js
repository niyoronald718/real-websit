import { api } from "./api.js";
import { getDownloads, saveDownloads } from "./storage.js";

const active = new Map();
const persist = entry => {
  const entries = getDownloads().filter(item => item.id !== entry.id);
  entries.unshift(entry);
  saveDownloads(entries.slice(0, 100));
  window.dispatchEvent(new CustomEvent("downloads:changed"));
};

export async function downloadMovie(movie, variant = "original", onProgress = () => {}) {
  const details = await api(`/api/download/${movie.id}?variant=${encodeURIComponent(variant)}`);
  const entry = {
    id: `${movie.id}-${variant}-${Date.now()}`, movieId: movie.id, title: movie.title,
    variant, filename: details.filename, size: details.size, progress: 0,
    status: "queued", startedAt: new Date().toISOString()
  };
  persist(entry);
  if (!window.ReadableStream || !window.Response.prototype.blob) {
    const anchor = document.createElement("a");
    anchor.href = details.url;
    anchor.download = details.filename;
    anchor.click();
    entry.status = "complete";
    persist(entry);
    return entry;
  }
  const controller = new AbortController();
  active.set(entry.id, controller);
  try {
    entry.status = "downloading";
    persist(entry);
    const response = await fetch(details.url, { signal: controller.signal });
    if (!response.ok) throw new Error(`Download failed (${response.status})`);
    const reader = response.body.getReader();
    const chunks = [];
    let received = 0;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(value);
      received += value.length;
      entry.progress = details.size ? Math.min(100, Math.round(received * 100 / details.size)) : 0;
      onProgress(entry.progress);
      persist(entry);
    }
    const blob = new Blob(chunks, { type: details.format === "mp4" ? "video/mp4" : "application/octet-stream" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = details.filename;
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
    entry.progress = 100;
    entry.status = "complete";
    persist(entry);
    return entry;
  } catch (error) {
    entry.status = error.name === "AbortError" ? "failed" : "failed";
    entry.error = error.message;
    persist(entry);
    throw error;
  } finally {
    active.delete(entry.id);
  }
}

export function cancelDownload(id) {
  active.get(id)?.abort();
}

export function removeDownload(id) {
  saveDownloads(getDownloads().filter(entry => entry.id !== id));
  window.dispatchEvent(new CustomEvent("downloads:changed"));
}
