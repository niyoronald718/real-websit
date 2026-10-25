import { escapeHTML } from "../core/api.js";

export function movieCard(movie) {
  const badge = movie.is_new ? "NEW" : movie.is_hot ? "HOT" : "";
  const poster = movie.poster_url
    ? `<img src="${escapeHTML(movie.poster_url)}" alt="" loading="lazy">`
    : "";
  return `<article class="movie-card"><a href="/movie.html?slug=${encodeURIComponent(movie.slug)}" aria-label="View ${escapeHTML(movie.title)}"><div class="poster">${poster}${badge ? `<span class="badge">${badge}</span>` : ""}<span class="poster-title">${escapeHTML(movie.title)}</span></div><div class="card-meta"><strong>${escapeHTML(movie.title)}</strong>${escapeHTML(movie.year ?? "")} · ${escapeHTML(movie.vj?.name ?? "Luganda audio")}</div></a></article>`;
}
