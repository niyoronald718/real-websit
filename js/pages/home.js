import { api } from "../core/api.js";
import { movieCard } from "../components/movie-card.js";

async function fill(url, target) {
  const data = await api(url);
  document.querySelector(target).innerHTML = data.items.map(movieCard).join("") || '<p class="muted">Nothing here yet.</p>';
  return data.items;
}

try {
  const [featured, newest] = await Promise.all([
    fill("/api/movies?featured=1&per_page=6", "#featured-row"),
    fill("/api/movies?new=1&per_page=8", "#new-row"),
    fill("/api/movies/trending", "#trending-row")
  ]).then(values => [values[0], values[1]]);
  await fill("/api/movies?per_page=10", "#all-row");
  const slides = featured.length ? featured : newest;
  const dots = document.querySelector("#hero-dots");
  dots.innerHTML = slides.map((_, index) => `<button class="hero-dot${index === 0 ? " active" : ""}" aria-label="Featured title ${index + 1}"></button>`).join("");
  let index = 0;
  const draw = () => {
    const movie = slides[index];
    if (!movie) return;
    const hero = document.querySelector("#hero");
    hero.style.backgroundImage = movie.backdrop_url ? `linear-gradient(90deg,#0b0b0f 0%,#0b0b0fdd 48%,transparent),url("${movie.backdrop_url}")` : "";
    hero.querySelector("h1").innerHTML = `${movie.title}<br><span>${movie.year ?? "Luganda stories"}</span>`;
    hero.querySelector(".hero-content > p:not(.eyebrow)").textContent = movie.description;
    hero.querySelector(".button").href = `/movie.html?slug=${encodeURIComponent(movie.slug)}`;
    dots.querySelectorAll("button").forEach((dot, i) => dot.classList.toggle("active", i === index));
  };
  dots.addEventListener("click", event => {
    const dot = event.target.closest("button");
    if (dot) { index = [...dots.children].indexOf(dot); draw(); }
  });
  document.querySelectorAll("[data-scroll]").forEach(button => button.addEventListener("click", () => {
    document.getElementById(button.dataset.target).scrollBy({ left: Number(button.dataset.scroll) * 500, behavior: "smooth" });
  }));
  if (slides.length) { draw(); setInterval(() => { index = (index + 1) % slides.length; draw(); }, 6000); }
} catch (error) {
  document.querySelectorAll(".movie-row,.movie-grid").forEach(node => { node.innerHTML = `<p class="muted">${error.message}</p>`; });
}
