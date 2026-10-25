import { api } from "../core/api.js";
import { movieCard } from "../components/movie-card.js";

const form = document.querySelector("#filters");
const grid = document.querySelector("#movie-grid");
const params = new URLSearchParams(location.search);
let page = Math.max(1, Number(params.get("page")) || 1);

for (const name of ["genre", "vj", "type", "sort"]) {
  const select = form.elements[name];
  if (params.has(name)) select.value = params.get(name);
}
if (params.has("q")) document.querySelector("#site-search").value = params.get("q");

async function load() {
  const query = new URLSearchParams(new FormData(form));
  query.set("page", page);
  if (document.querySelector("#site-search").value.trim()) query.set("q", document.querySelector("#site-search").value.trim());
  const search = query.get("q");
  const result = search ? await api(`/api/search?q=${encodeURIComponent(search)}`).then(data => ({ items: [...data.movies, ...data.series], total: data.movies.length + data.series.length, page: 1, per_page: 48 })) : await api(`/api/movies?${query}`);
  grid.innerHTML = result.items.map(movieCard).join("") || '<p class="muted">No matching titles found.</p>';
  document.querySelector("#results-count").textContent = `${result.total} title${result.total === 1 ? "" : "s"} found`;
  const pageCount = Math.max(1, Math.ceil(result.total / result.per_page));
  document.querySelector("#pagination").innerHTML = Array.from({ length: pageCount }, (_, i) => `<button class="${i + 1 === page ? "active" : ""}" data-page="${i + 1}">${i + 1}</button>`).join("");
  document.querySelectorAll("#pagination button").forEach(button => button.addEventListener("click", () => { page = Number(button.dataset.page); updateUrl(); load(); window.scrollTo({ top: 0, behavior: "smooth" }); }));
  updateUrl();
}

function updateUrl() {
  const query = new URLSearchParams(new FormData(form));
  if (page > 1) query.set("page", page); else query.delete("page");
  const q = document.querySelector("#site-search").value.trim();
  if (q) query.set("q", q);
  for (const [key, value] of [...query]) if (!value) query.delete(key);
  history.replaceState(null, "", `/movies.html${query.size ? `?${query}` : ""}`);
}

form.addEventListener("submit", event => { event.preventDefault(); page = 1; load(); });
document.querySelector("#site-search").addEventListener("input", () => {
  clearTimeout(window.searchTimer);
  window.searchTimer = setTimeout(() => { page = 1; load(); }, 300);
});

Promise.all([api("/api/genres"), api("/api/vjs")]).then(([genres, vjs]) => {
  const genreSelect = form.elements.genre;
  genres.items.forEach(item => genreSelect.add(new Option(item.name, item.slug)));
  const vjSelect = form.elements.vj;
  vjs.items.forEach(item => vjSelect.add(new Option(item.name, item.slug)));
  for (const name of ["genre", "vj"]) if (params.has(name)) form.elements[name].value = params.get(name);
  return load();
}).catch(error => { grid.textContent = error.message; });
