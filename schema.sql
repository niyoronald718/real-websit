PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS vjs (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    bio TEXT NOT NULL DEFAULT '',
    photo TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS genres (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    year INTEGER,
    duration INTEGER NOT NULL DEFAULT 0,
    rating REAL NOT NULL DEFAULT 0,
    poster_url TEXT NOT NULL DEFAULT '',
    backdrop_url TEXT NOT NULL DEFAULT '',
    video_path TEXT NOT NULL DEFAULT '',
    type TEXT NOT NULL DEFAULT 'movie' CHECK(type IN ('movie', 'series')),
    is_new INTEGER NOT NULL DEFAULT 0,
    is_hot INTEGER NOT NULL DEFAULT 0,
    is_featured INTEGER NOT NULL DEFAULT 0,
    is_published INTEGER NOT NULL DEFAULT 1,
    is_downloadable INTEGER NOT NULL DEFAULT 1,
    views INTEGER NOT NULL DEFAULT 0,
    vj_id INTEGER REFERENCES vjs(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS movie_genres (
    movie_id INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    genre_id INTEGER NOT NULL REFERENCES genres(id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, genre_id)
);

CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY,
    movie_id INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    season INTEGER NOT NULL DEFAULT 1,
    episode INTEGER NOT NULL DEFAULT 1,
    title TEXT NOT NULL,
    video_path TEXT NOT NULL DEFAULT '',
    duration INTEGER NOT NULL DEFAULT 0,
    is_downloadable INTEGER NOT NULL DEFAULT 1,
    UNIQUE(movie_id, season, episode)
);

CREATE TABLE IF NOT EXISTS download_variants (
    id INTEGER PRIMARY KEY,
    movie_id INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    episode_id INTEGER REFERENCES episodes(id) ON DELETE CASCADE,
    quality TEXT NOT NULL CHECK(quality IN ('480p', '720p', '1080p', 'original')),
    file_path TEXT NOT NULL,
    file_size INTEGER NOT NULL DEFAULT 0,
    format TEXT NOT NULL DEFAULT 'mp4',
    UNIQUE(movie_id, episode_id, quality)
);

CREATE TABLE IF NOT EXISTS subtitles (
    id INTEGER PRIMARY KEY,
    movie_id INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    episode_id INTEGER REFERENCES episodes(id) ON DELETE CASCADE,
    language TEXT NOT NULL,
    file_path TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS view_events (
    id INTEGER PRIMARY KEY,
    movie_id INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    day TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    UNIQUE(movie_id, day)
);

CREATE TABLE IF NOT EXISTS download_events (
    id INTEGER PRIMARY KEY,
    movie_id INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    episode_id INTEGER REFERENCES episodes(id) ON DELETE SET NULL,
    variant TEXT NOT NULL,
    ip_hash TEXT NOT NULL,
    day TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    UNIQUE(movie_id, variant, ip_hash, day)
);

CREATE TABLE IF NOT EXISTS admin_users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_movies_published_created ON movies(is_published, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_movies_slug ON movies(slug);
CREATE INDEX IF NOT EXISTS idx_view_events_day ON view_events(day);
