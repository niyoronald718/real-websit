const read = (key, fallback) => {
  try { return JSON.parse(localStorage.getItem(key)) ?? fallback; }
  catch { return fallback; }
};

export const getWatchlist = () => {
  const value = read("watchlist", []);
  return Array.isArray(value) ? value : [];
};
export const saveWatchlist = value => localStorage.setItem("watchlist", JSON.stringify(value));
export const getResume = () => {
  const value = read("resume", {});
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
};
export const saveResume = value => localStorage.setItem("resume", JSON.stringify(value));
export const getDownloads = () => {
  const value = read("downloads", []);
  return Array.isArray(value) ? value : [];
};
export const saveDownloads = value => localStorage.setItem("downloads", JSON.stringify(value));
