import { api, escapeHTML } from "../core/api.js";
import { getWatchlist, saveWatchlist } from "../core/storage.js";
import { mountPlayer } from "../components/player.js";
import { movieCard } from "../components/movie-card.js";
import { downloadMovie } from "../core/download-manager.js";

const slug = new URLSearchParams(location.search).get("slug");
const root = document.querySelector("#movie-detail");
const dialog = document.querySelector("#download-dialog");
let movie;

if (!slug) root.innerHTML = "<p>Choose a title from the <a href='/movies.html'>library</a>.</p>";
else api(`/api/movies/${encodeURIComponent(slug)}`).then(async data => {
  movie = data;
  document.title = `${movie.title} — Pacha`;
  document.querySelector('meta[name="description"]').content = movie.description;
  root.innerHTML = `<section class="movie-detail-hero"><div class="detail-layout"><div class="detail-poster">${movie.poster_url ? `<img src="${escapeHTML(movie.poster_url)}" alt="" style="width:100%;height:100%;object-fit:cover;position:absolute">` : escapeHTML(movie.title)}</div><div class="detail-copy"><p class="eyebrow">${movie.is_new ? "New release" : "Luganda audio"}</p><h1>${escapeHTML(movie.title)}</h1><div class="detail-facts"><span>${escapeHTML(movie.year ?? "")}</span><span>${movie.duration ? `${movie.duration} min` : "Feature"}</span><span>★ ${Number(movie.rating).toFixed(1)}</span><span>${escapeHTML(movie.type)}</span><span>${escapeHTML(movie.vj?.name ?? "Independent")}</span></div><p class="detail-description">${escapeHTML(movie.description)}</p><div class="detail-actions"><button id="watchlist-button" class="button button-secondary"></button><button id="download-button" class="button button-primary" ${movie.has_video ? "" : "disabled"}>${movie.has_video ? "↓ Download" : "Download unavailable"}</button></div></div></div></section><section class="page-shell"><div class="video-wrap" id="player"><p class="video-message">${movie.has_video ? "Loading player…" : "Playback is unavailable: no media file has been uploaded for this title."}</p></div><section class="subsection"><div class="section-heading"><h2>More like this</h2></div><div class="movie-row" id="related"></div></section></section>`;
  const watchButton = document.querySelector("#watchlist-button");
  const paintWatch = () => { watchButton.textContent = getWatchlist().includes(movie.id) ? "✓ In watchlist" : "+ Add to watchlist"; };
  paintWatch();
  watchButton.addEventListener("click", () => {
    const list = getWatchlist();
    saveWatchlist(list.includes(movie.id) ? list.filter(id => id !== movie.id) : [...list, movie.id]);
    paintWatch();
  });
  document.querySelector("#download-button").addEventListener("click", () => {
    document.querySelector("#download-options").innerHTML = `<label class="download-choice"><span><input type="radio" name="quality" value="original" checked> Original MP4</span><span>${movie.duration ? `${movie.duration} min` : "Size varies"}</span></label>`;
    document.querySelector("#download-status").textContent = "";
    dialog.showModal();
  });
  document.querySelector("#start-download").addEventListener("click", async event => {
    event.preventDefault();
    const button = event.currentTarget;
    button.disabled = true;
    button.textContent = "Preparing download…";
    try {
      await downloadMovie(movie, document.querySelector('input[name="quality"]:checked').value, percent => {
        button.textContent = percent ? `Downloading… ${percent}%` : "Downloading…";
      });
      document.querySelector("#download-status").textContent = "Download handed to your browser.";
    } catch (error) {
      document.querySelector("#download-status").textContent = error.message;
    } finally {
      button.disabled = false;
      button.textContent = "Start download";
    }
  });
  if (movie.has_video) {
    try { await mountPlayer(document.querySelector("#player"), movie); }
    catch (error) { document.querySelector("#player").innerHTML = `<p class="video-message">${escapeHTML(error.message)}<br>Playback could not be started.</p>`; }
  }
  const related = await api(`/api/movies/${encodeURIComponent(slug)}/related`);
  document.querySelector("#related").innerHTML = related.items.map(movieCard).join("") || '<p class="muted">No related titles yet.</p>';
}).catch(error => { root.innerHTML = `<p role="alert">${escapeHTML(error.message)} <a href="/movies.html">Browse titles</a></p>`; });

document.addEventListener("keydown", event => { if (event.key === "Escape" && dialog.open) dialog.close(); });
