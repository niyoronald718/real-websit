# Pacha

A self-hostable, ad-free catalogue and player for **media you have the rights to distribute**. The seeded titles are fictional examples. No movie/video assets are included.

## Current scope

This is a runnable MVP: catalogue browsing and filtering, search, featured/new/trending rows, details, local watchlist/resume, native MP4 playback with signed URLs and HTTP Range support, original-file downloads, device-local download tracking, and a session-protected admin page for title CRUD and video uploads.

Not yet implemented in this MVP: series episode management, subtitle delivery, variant upload UI, downloadable season ZIPs, full VJ/genre CRUD, persistent distributed rate limits, daily bandwidth accounting, HLS playback, automated sitemap generation, and comprehensive audit logging. The admin stats include basic views/download totals. Upload only media for which you hold valid distribution rights.

## Requirements

- Python 3.11 or newer
- Flask 3.x
- SQLite (included with Python)

No frontend build, CSS framework, CDN, third-party tracker, ad network, or browser framework is used. MP4 playback uses the native `<video>` element; HLS.js is not needed for the included MP4 MVP.

## Local setup (Windows PowerShell)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:SECRET_KEY = "replace-with-a-long-random-value"
$env:ADMIN_USERNAME = "admin"
$env:ADMIN_PASSWORD = "set-a-strong-local-password"
python app.py
```

Open `http://127.0.0.1:5000`. The SQLite database and uploaded files are created under `instance/`. Initial fictional sample catalogue data is seeded automatically. The first admin user is created only if both admin environment variables are set and there is no existing admin.

For Linux/macOS, create and activate the virtual environment with the platform's normal `python3 -m venv .venv` and `source .venv/bin/activate` commands.

## Admin

Visit `/admin` and sign in with `ADMIN_USERNAME` and `ADMIN_PASSWORD`. The admin API is protected by a signed, HttpOnly session cookie and a per-session CSRF token for state-changing operations. Create titles and upload an MP4 or WebM video from the dashboard. Poster uploads are accepted by the API but image management is not yet exposed in the MVP UI.

Set `COOKIE_SECURE=1` when serving over HTTPS. Never deploy with the development fallback secret or a weak admin password. For production, use a secret manager/environment injection, HTTPS, and a production WSGI server; do not expose Flask's development server.

## Media URLs and download behavior

- A public play request gets a short-lived HMAC-SHA256 URL scoped to the `stream` purpose.
- A download link is separately signed for the `download` purpose and expires after two hours.
- Media files live outside `public/`; direct video paths are not served as static files.
- Flask/Werkzeug's conditional file response supports byte-range requests for local files, enabling seeking and browser resume where supported.
- Downloads use the browser download manager. The site tracks metadata in localStorage; browser pause/resume behavior is browser-dependent.
- The in-process download request limiter defaults to 10 requests per IP per hour. It is memory-local, so use an Nginx limit and/or a shared limiter before running multiple workers.
- `DAILY_BANDWIDTH_CAP` is reserved for a future bandwidth-accounting implementation and is **not enforced by this MVP**.

For lower hosting costs, transcode rights-cleared media with `ffmpeg` into smaller 480p/720p/1080p MP4 files and add variant records through a future admin extension. Video is already compressed; gzip should be limited to text assets/manifests.

## Production example (Nginx + Gunicorn)

Install Gunicorn on the Linux host (`pip install gunicorn`) and run the app behind a reverse proxy:

```sh
gunicorn --workers 2 --bind 127.0.0.1:8000 app:app
```

Example Nginx site (adjust domain, TLS, and paths):

```nginx
limit_req_zone $binary_remote_addr zone=downloads:10m rate=10r/h;

server {
    listen 443 ssl;
    server_name example.invalid;

    client_max_body_size 4g;
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;

    location /download/ {
        limit_req zone=downloads burst=3 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
    }

    location /stream/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

The included `deploy/nginx.conf` has the same proxy/rate-limit outline. To offload large media responses in a high-traffic deployment, add a private Nginx `internal` location and have the Flask routes authorize the signed URL before returning `X-Accel-Redirect`; do not expose the upload directory as a public static alias.

The app currently uses SQLite and local filesystem storage. Back up both `instance/movies.sqlite3` and `instance/uploads/`. For a multi-host setup, move to a database and storage architecture with shared state before enabling multiple app workers.

## Configuration

Copy `.env.example` values into your service environment. Flask does not automatically load `.env` files; use your process manager/container environment or add `python-dotenv` intentionally if desired.

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Flask session signing and HMAC signed media URL key |
| `DATABASE_PATH` | SQLite database location |
| `UPLOAD_DIR` | Private local uploads location |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD` | Initial administrator, used only on first initialization |
| `DOWNLOAD_RATE_LIMIT` | In-process hourly download request limit |
| `DAILY_BANDWIDTH_CAP` | Reserved; not currently enforced |
| `MAX_CONTENT_LENGTH` | Maximum upload request size in bytes |
| `COOKIE_SECURE` | Set to `1` for HTTPS-only session cookies |

## Rights and privacy

This is demonstration software, not a source of film content. The operator is responsible for licensing and distribution permissions. It does not scrape content, bypass DRM, or include copyrighted film media. There are no ads, third-party trackers, analytics, or public user accounts. Watchlist, resume state, and download metadata stay in browser localStorage. Server-side view/download counts are aggregate; the download event stores a keyed IP hash rather than a raw IP.

## Dependencies and license

- Flask — BSD-3-Clause
- Python standard library, including SQLite, HMAC, and ZIP-related utilities — Python Software Foundation License
- Application code — MIT; see `LICENSE`

No HLS.js binary is bundled because this MVP only plays MP4 files through the browser's native player.
