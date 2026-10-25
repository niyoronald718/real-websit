import { api } from "../core/api.js";
import { getResume, saveResume } from "../core/storage.js";

const formatTime = seconds => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;

export async function mountPlayer(container, movie) {
  const resume = getResume()[movie.id];
  const stream = await api(`/api/stream/${movie.id}`);
  container.innerHTML = `<video controls playsinline preload="metadata" aria-label="${movie.title}"></video><p class="video-message" id="player-message">Playback starts when you press play.</p>`;
  const video = container.querySelector("video");
  const message = container.querySelector("#player-message");
  video.src = stream.url;
  video.addEventListener("loadedmetadata", () => {
    if (resume?.t > 30 && (!video.duration || resume.t < video.duration * .95)) {
      message.innerHTML = `Resume from ${formatTime(resume.t)}? <button class="button button-secondary" id="resume-play">Resume</button> <button class="button button-secondary" id="start-over">Start over</button>`;
      container.querySelector("#resume-play").onclick = () => { video.currentTime = resume.t; video.play(); message.remove(); };
      container.querySelector("#start-over").onclick = () => message.remove();
    }
  });
  let viewSent = false;
  video.addEventListener("play", () => {
    if (!viewSent) {
      viewSent = true;
      api(`/api/movies/${movie.id}/view`, { method: "POST" }).catch(() => {});
    }
    message.textContent = "";
  });
  video.addEventListener("timeupdate", () => {
    const data = getResume();
    data[movie.id] = { t: video.currentTime, updatedAt: Date.now(), title: movie.title, slug: movie.slug };
    saveResume(data);
  });
  video.addEventListener("error", () => { message.textContent = "This title is not ready for playback yet. Please check back later."; });
}
