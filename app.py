import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode

from flask import Flask, abort, jsonify, request, send_file, send_from_directory, session
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"


def create_app():
    app = Flask(__name__, static_folder=None)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        DATABASE_PATH=os.environ.get("DATABASE_PATH", str(ROOT / "instance" / "movies.sqlite3")),
        UPLOAD_DIR=os.environ.get("UPLOAD_DIR", str(ROOT / "instance" / "uploads")),
        MAX_CONTENT_LENGTH=int(os.environ.get("MAX_CONTENT_LENGTH", 4 * 1024**3)),
        DOWNLOAD_RATE_LIMIT=int(os.environ.get("DOWNLOAD_RATE_LIMIT", "10")),
        DAILY_BANDWIDTH_CAP=int(os.environ.get("DAILY_BANDWIDTH_CAP", str(5 * 1024**3))),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1",
    )
    Path(app.config["DATABASE_PATH"]).parent.mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_DIR"]).mkdir(parents=True, exist_ok=True)
    app.extensions["download_attempts"] = {}
    initialize_database(app)

    @contextmanager
    def db():
        connection = sqlite3.connect(app.config["DATABASE_PATH"], timeout=20)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def movie_dict(connection, row):
        item = dict(row)
        item["has_video"] = bool(item.get("video_path"))
        item["genres"] = [
            dict(g) for g in connection.execute(
                "SELECT g.name, g.slug FROM genres g JOIN movie_genres mg ON mg.genre_id=g.id WHERE mg.movie_id=? ORDER BY g.name",
                (item["id"],),
            )
        ]
        item["vj"] = None
        if item.get("vj_id"):
            vj = connection.execute("SELECT id, name, slug FROM vjs WHERE id=?", (item["vj_id"],)).fetchone()
            item["vj"] = dict(vj) if vj else None
        item.pop("video_path", None)
        return item

    def signed_token(item_id, purpose, expiry):
        message = f"{item_id}:{purpose}:{expiry}".encode()
        return hmac.new(app.config["SECRET_KEY"].encode(), message, hashlib.sha256).hexdigest()

    def valid_token(item_id, purpose):
        expiry = request.args.get("expires", "")
        token = request.args.get("token", "")
        if not expiry.isdigit() or int(expiry) < int(time.time()):
            return False
        return hmac.compare_digest(token, signed_token(item_id, purpose, expiry))

    def require_admin():
        if not session.get("admin_id"):
            return jsonify(error="Admin login required"), 401
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            supplied = request.headers.get("X-CSRF-Token", "")
            if not session.get("csrf_token") or not hmac.compare_digest(supplied, session["csrf_token"]):
                return jsonify(error="Invalid CSRF token"), 403
        return None

    def get_movie_by_id(movie_id):
        with db() as connection:
            return connection.execute("SELECT * FROM movies WHERE id=? AND is_published=1", (movie_id,)).fetchone()

    def resolve_upload(relative_path):
        base = Path(app.config["UPLOAD_DIR"]).resolve()
        candidate = (base / relative_path).resolve()
        if candidate != base and base not in candidate.parents:
            abort(404)
        if not candidate.is_file():
            abort(404, description="Media file has not been uploaded yet.")
        return candidate

    def check_download_limit():
        now = time.time()
        ip = request.remote_addr or "unknown"
        attempts = app.extensions["download_attempts"]
        active = [stamp for stamp in attempts.get(ip, []) if now - stamp < 3600]
        if len(active) >= app.config["DOWNLOAD_RATE_LIMIT"]:
            abort(429, description="Download limit reached. Please try again later.")
        active.append(now)
        attempts[ip] = active

    @app.errorhandler(413)
    def too_large(_error):
        return jsonify(error="Upload is larger than the configured limit."), 413

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error=error.description), error.code

    @app.get("/")
    def home():
        return send_from_directory(PUBLIC, "index.html")

    @app.get("/<path:filename>")
    def static_files(filename):
        if filename.startswith(("api/", "admin/", "stream/", "download/")):
            abort(404)
        return send_from_directory(PUBLIC, filename)

    @app.get("/api/movies")
    def api_movies():
        page = max(1, request.args.get("page", 1, type=int))
        per_page = min(48, max(1, request.args.get("per_page", 24, type=int)))
        clauses = ["m.is_published=1"]
        values = []
        for arg, expression in (("genre", "g.slug=?"), ("vj", "v.slug=?")):
            value = request.args.get(arg, "").strip()
            if value:
                clauses.append(f"EXISTS (SELECT 1 FROM movie_genres mg JOIN genres g ON g.id=mg.genre_id WHERE mg.movie_id=m.id AND {expression})" if arg == "genre" else f"EXISTS (SELECT 1 FROM vjs v WHERE v.id=m.vj_id AND {expression})")
                values.append(value)
        year = request.args.get("year", "").strip()
        if year.isdigit():
            clauses.append("m.year=?")
            values.append(int(year))
        media_type = request.args.get("type", "").strip()
        if media_type in ("movie", "series"):
            clauses.append("m.type=?")
            values.append(media_type)
        for flag in ("featured", "new", "hot"):
            if request.args.get(flag) in ("1", "true"):
                clauses.append(f"m.is_{flag}=1")
        ids = request.args.get("ids", "").strip()
        if ids:
            parsed = [int(value) for value in ids.split(",") if value.isdigit()][:100]
            if not parsed:
                return jsonify(items=[], total=0, page=page, per_page=per_page)
            clauses.append(f"m.id IN ({','.join('?' for _ in parsed)})")
            values.extend(parsed)
        sort = request.args.get("sort", "newest")
        order_by = {
            "newest": "m.created_at DESC, m.id DESC",
            "year": "m.year DESC, m.id DESC",
            "rating": "m.rating DESC, m.id DESC",
            "views": "m.views DESC, m.id DESC",
            "title": "m.title COLLATE NOCASE ASC",
        }.get(sort, "m.created_at DESC, m.id DESC")
        where = " AND ".join(clauses)
        with db() as connection:
            total = connection.execute(f"SELECT COUNT(*) FROM movies m WHERE {where}", values).fetchone()[0]
            rows = connection.execute(
                f"SELECT m.* FROM movies m WHERE {where} ORDER BY {order_by} LIMIT ? OFFSET ?",
                [*values, per_page, (page - 1) * per_page],
            ).fetchall()
            items = [movie_dict(connection, row) for row in rows]
        return jsonify(items=items, total=total, page=page, per_page=per_page)

    @app.get("/api/movies/trending")
    def api_trending():
        since = (date.today() - timedelta(days=6)).isoformat()
        with db() as connection:
            rows = connection.execute(
                "SELECT m.* FROM movies m LEFT JOIN view_events e ON e.movie_id=m.id AND e.day>=? "
                "WHERE m.is_published=1 GROUP BY m.id ORDER BY COALESCE(SUM(e.count),0) DESC, m.views DESC LIMIT 12",
                (since,),
            ).fetchall()
            return jsonify(items=[movie_dict(connection, row) for row in rows])

    @app.get("/api/movies/<slug>")
    def api_movie(slug):
        with db() as connection:
            row = connection.execute("SELECT * FROM movies WHERE slug=? AND is_published=1", (slug,)).fetchone()
            if not row:
                abort(404)
            item = movie_dict(connection, row)
            item["episodes"] = [dict(e) for e in connection.execute(
                "SELECT id, season, episode, title, duration, is_downloadable FROM episodes WHERE movie_id=? ORDER BY season, episode",
                (row["id"],),
            )]
            return jsonify(item)

    @app.get("/api/movies/<slug>/related")
    def api_related(slug):
        with db() as connection:
            source = connection.execute("SELECT id FROM movies WHERE slug=? AND is_published=1", (slug,)).fetchone()
            if not source:
                abort(404)
            rows = connection.execute(
                "SELECT DISTINCT m.* FROM movies m JOIN movie_genres mg ON mg.movie_id=m.id "
                "WHERE mg.genre_id IN (SELECT genre_id FROM movie_genres WHERE movie_id=?) "
                "AND m.id<>? AND m.is_published=1 ORDER BY m.is_hot DESC, m.rating DESC LIMIT 8",
                (source["id"], source["id"]),
            ).fetchall()
            return jsonify(items=[movie_dict(connection, row) for row in rows])

    @app.get("/api/vjs")
    def api_vjs():
        with db() as connection:
            return jsonify(items=[dict(row) for row in connection.execute("SELECT id,name,slug,bio,photo FROM vjs ORDER BY name")])

    @app.get("/api/genres")
    def api_genres():
        with db() as connection:
            return jsonify(items=[dict(row) for row in connection.execute("SELECT id,name,slug FROM genres ORDER BY name")])

    @app.get("/api/search")
    def api_search():
        query = request.args.get("q", "").strip()[:100]
        if len(query) < 2:
            return jsonify(movies=[], series=[], vjs=[])
        pattern = f"%{query}%"
        with db() as connection:
            rows = connection.execute(
                "SELECT m.* FROM movies m LEFT JOIN vjs v ON v.id=m.vj_id WHERE m.is_published=1 "
                "AND (m.title LIKE ? OR m.description LIKE ? OR v.name LIKE ?) ORDER BY m.is_hot DESC, m.rating DESC LIMIT 30",
                (pattern, pattern, pattern),
            ).fetchall()
            result = [movie_dict(connection, row) for row in rows]
            vjs = [dict(row) for row in connection.execute("SELECT id,name,slug,bio,photo FROM vjs WHERE name LIKE ? LIMIT 10", (pattern,))]
        return jsonify(movies=[item for item in result if item["type"] == "movie"], series=[item for item in result if item["type"] == "series"], vjs=vjs)

    @app.post("/api/movies/<int:movie_id>/view")
    def api_view(movie_id):
        today = date.today().isoformat()
        with db() as connection:
            cursor = connection.execute("UPDATE movies SET views=views+1 WHERE id=? AND is_published=1", (movie_id,))
            if cursor.rowcount == 0:
                abort(404)
            connection.execute(
                "INSERT INTO view_events(movie_id,day,count) VALUES(?,?,1) ON CONFLICT(movie_id,day) DO UPDATE SET count=count+1",
                (movie_id, today),
            )
        return jsonify(ok=True)

    @app.get("/api/stream/<int:movie_id>")
    def api_stream(movie_id):
        movie = get_movie_by_id(movie_id)
        if not movie or not movie["video_path"]:
            abort(404)
        expiry = str(int(time.time()) + 7200)
        query = urlencode({"expires": expiry, "token": signed_token(movie_id, "stream", expiry)})
        return jsonify(url=f"/stream/{movie_id}?{query}", expires=int(expiry))

    @app.get("/stream/<int:movie_id>")
    def stream_movie(movie_id):
        if not valid_token(movie_id, "stream"):
            abort(403)
        movie = get_movie_by_id(movie_id)
        if not movie or not movie["video_path"]:
            abort(404)
        path = resolve_upload(movie["video_path"])
        return send_file(path, mimetype="video/mp4", conditional=True, etag=True, max_age=0)

    @app.get("/api/download/<int:movie_id>")
    def api_download(movie_id):
        movie = get_movie_by_id(movie_id)
        if not movie or not movie["is_downloadable"]:
            abort(404)
        variant = request.args.get("variant", "original")
        with db() as connection:
            selected = connection.execute(
                "SELECT file_path,file_size,format,quality FROM download_variants WHERE movie_id=? AND quality=?",
                (movie_id, variant),
            ).fetchone()
        if selected:
            media_path, size, quality, extension = selected["file_path"], selected["file_size"], selected["quality"], selected["format"]
        elif variant == "original" and movie["video_path"]:
            media_path = movie["video_path"]
            size = resolve_upload(media_path).stat().st_size
            quality, extension = "original", Path(media_path).suffix.lstrip(".") or "mp4"
        else:
            abort(404, description="That download quality is not available.")
        expiry = str(int(time.time()) + 7200)
        query = urlencode({"variant": quality, "expires": expiry, "token": signed_token(movie_id, "download", expiry)})
        filename = secure_filename(f"{movie['title']}-{quality}.{extension}") or f"movie-{movie_id}.{extension}"
        return jsonify(url=f"/download/{movie_id}?{query}", size=size, filename=filename, format=extension)

    @app.get("/download/<int:movie_id>")
    def download_movie(movie_id):
        if not valid_token(movie_id, "download"):
            abort(403)
        check_download_limit()
        movie = get_movie_by_id(movie_id)
        if not movie or not movie["is_downloadable"]:
            abort(404)
        variant = request.args.get("variant", "original")
        with db() as connection:
            selected = connection.execute(
                "SELECT file_path,format FROM download_variants WHERE movie_id=? AND quality=?",
                (movie_id, variant),
            ).fetchone()
        media_path = selected["file_path"] if selected else movie["video_path"] if variant == "original" else ""
        if not media_path:
            abort(404)
        path = resolve_upload(media_path)
        ip_digest = hmac.new(app.config["SECRET_KEY"].encode(), (request.remote_addr or "").encode(), hashlib.sha256).hexdigest()
        with db() as connection:
            connection.execute(
                "INSERT INTO download_events(movie_id,variant,ip_hash,day,count) VALUES(?,?,?,?,1) "
                "ON CONFLICT(movie_id,variant,ip_hash,day) DO UPDATE SET count=count+1",
                (movie_id, variant, ip_digest, date.today().isoformat()),
            )
        extension = (selected["format"] if selected else path.suffix.lstrip(".")) or "mp4"
        filename = secure_filename(f"{movie['title']}-{variant}.{extension}") or f"movie-{movie_id}.{extension}"
        return send_file(path, mimetype="application/octet-stream", as_attachment=True, download_name=filename, conditional=True, etag=True, max_age=0)

    @app.get("/admin")
    def admin_page():
        return send_from_directory(PUBLIC, "admin.html")

    @app.post("/admin/login")
    def admin_login():
        payload = request.get_json(silent=True) or request.form
        username = str(payload.get("username", ""))[:100]
        password = str(payload.get("password", ""))[:256]
        with db() as connection:
            row = connection.execute("SELECT id,password_hash FROM admin_users WHERE username=?", (username,)).fetchone()
        if not row or not check_password_hash(row["password_hash"], password):
            return jsonify(error="Invalid username or password"), 401
        session.clear()
        session["admin_id"] = row["id"]
        session["csrf_token"] = secrets.token_urlsafe(32)
        return jsonify(ok=True, csrf_token=session["csrf_token"])

    @app.post("/admin/logout")
    def admin_logout():
        denied = require_admin()
        if denied:
            return denied
        session.clear()
        return jsonify(ok=True)

    @app.get("/admin/api/stats")
    def admin_stats():
        denied = require_admin()
        if denied:
            return denied
        with db() as connection:
            return jsonify(
                movies=connection.execute("SELECT COUNT(*) FROM movies").fetchone()[0],
                published=connection.execute("SELECT COUNT(*) FROM movies WHERE is_published=1").fetchone()[0],
                views=connection.execute("SELECT COALESCE(SUM(views),0) FROM movies").fetchone()[0],
                downloads=connection.execute("SELECT COALESCE(SUM(count),0) FROM download_events").fetchone()[0],
            )

    @app.get("/admin/api/movies")
    def admin_movies():
        denied = require_admin()
        if denied:
            return denied
        with db() as connection:
            rows = connection.execute("SELECT id,title,slug,year,type,is_published,is_downloadable,video_path FROM movies ORDER BY id DESC").fetchall()
            return jsonify(items=[dict(row) for row in rows])

    @app.post("/admin/api/movies")
    def admin_create_movie():
        denied = require_admin()
        if denied:
            return denied
        payload = request.get_json(silent=True) or {}
        title = str(payload.get("title", "")).strip()[:200]
        if not title:
            return jsonify(error="Title is required"), 400
        base_slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "movie"
        slug, suffix = base_slug, 2
        try:
            year = int(payload["year"]) if payload.get("year") else None
            duration = int(payload.get("duration") or 0)
        except (TypeError, ValueError):
            return jsonify(error="Year and duration must be whole numbers"), 400
        if year is not None and not 1888 <= year <= 2100:
            return jsonify(error="Year must be between 1888 and 2100"), 400
        if not 0 <= duration <= 10000:
            return jsonify(error="Duration must be between 0 and 10000 minutes"), 400
        with db() as connection:
            while connection.execute("SELECT 1 FROM movies WHERE slug=?", (slug,)).fetchone():
                slug = f"{base_slug}-{suffix}"
                suffix += 1
            cursor = connection.execute(
                "INSERT INTO movies(title,slug,description,year,duration,type,is_published,is_downloadable) VALUES(?,?,?,?,?,?,?,?)",
                (title, slug, str(payload.get("description", ""))[:5000], year, duration, payload.get("type") if payload.get("type") in ("movie", "series") else "movie", int(bool(payload.get("is_published", True))), int(bool(payload.get("is_downloadable", True)))),
            )
            return jsonify(id=cursor.lastrowid, slug=slug), 201

    @app.put("/admin/api/movies/<int:movie_id>")
    def admin_update_movie(movie_id):
        denied = require_admin()
        if denied:
            return denied
        payload = request.get_json(silent=True) or {}
        allowed = {"title", "description", "year", "duration", "type", "is_published", "is_downloadable"}
        fields = {key: payload[key] for key in allowed if key in payload}
        if "type" in fields and fields["type"] not in ("movie", "series"):
            return jsonify(error="type must be movie or series"), 400
        for key, minimum, maximum in (("year", 1888, 2100), ("duration", 0, 10000)):
            if key in fields:
                try:
                    fields[key] = int(fields[key]) if fields[key] not in (None, "") else None if key == "year" else 0
                except (TypeError, ValueError):
                    return jsonify(error=f"{key} must be a whole number"), 400
                if fields[key] is not None and not minimum <= fields[key] <= maximum:
                    return jsonify(error=f"{key} must be between {minimum} and {maximum}"), 400
        for key in ("is_published", "is_downloadable"):
            if key in fields:
                value = fields[key]
                if value not in (True, False, 0, 1, "0", "1", "true", "false"):
                    return jsonify(error=f"{key} must be a boolean"), 400
                fields[key] = int(value in (True, 1, "1", "true"))
        if not fields:
            return jsonify(error="No editable fields supplied"), 400
        assignments = ", ".join(f"{key}=?" for key in fields)
        with db() as connection:
            cursor = connection.execute(f"UPDATE movies SET {assignments}, updated_at=CURRENT_TIMESTAMP WHERE id=?", [*fields.values(), movie_id])
            if not cursor.rowcount:
                abort(404)
        return jsonify(ok=True)

    @app.delete("/admin/api/movies/<int:movie_id>")
    def admin_delete_movie(movie_id):
        denied = require_admin()
        if denied:
            return denied
        with db() as connection:
            cursor = connection.execute("DELETE FROM movies WHERE id=?", (movie_id,))
            if not cursor.rowcount:
                abort(404)
        return jsonify(ok=True)

    @app.post("/admin/api/movies/<int:movie_id>/upload")
    def admin_upload(movie_id):
        denied = require_admin()
        if denied:
            return denied
        uploaded = request.files.get("file")
        kind = request.form.get("kind", "video")
        allowed_extensions = {"video": {"mp4", "webm"}, "poster": {"jpg", "jpeg", "png", "webp"}}
        if not uploaded or kind not in allowed_extensions:
            return jsonify(error="Choose a valid file and upload type"), 400
        extension = Path(secure_filename(uploaded.filename or "")).suffix.lower().lstrip(".")
        if extension not in allowed_extensions[kind]:
            return jsonify(error="Unsupported file extension"), 400
        with db() as connection:
            movie = connection.execute("SELECT id FROM movies WHERE id=?", (movie_id,)).fetchone()
            if not movie:
                abort(404)
        filename = f"{secrets.token_hex(16)}.{extension}"
        destination = Path(app.config["UPLOAD_DIR"]) / str(movie_id)
        destination.mkdir(parents=True, exist_ok=True)
        uploaded.save(destination / filename)
        relative = f"{movie_id}/{filename}"
        with db() as connection:
            if kind == "video":
                connection.execute("UPDATE movies SET video_path=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (relative, movie_id))
            else:
                connection.execute("UPDATE movies SET poster_url=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (f"/media/{relative}", movie_id))
        return jsonify(ok=True, path=relative)

    @app.get("/media/<path:relative_path>")
    def media_file(relative_path):
        if Path(relative_path).suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            abort(404)
        path = resolve_upload(relative_path)
        return send_file(path, conditional=True, max_age=3600)

    @app.get("/robots.txt")
    def robots():
        return "User-agent: *\nDisallow: /admin\n", 200, {"Content-Type": "text/plain"}

    return app


def initialize_database(app):
    database_path = Path(app.config["DATABASE_PATH"])
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
    count = connection.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    if count == 0:
        connection.executescript((ROOT / "seed.sql").read_text(encoding="utf-8"))
    username = os.environ.get("ADMIN_USERNAME", "")
    password = os.environ.get("ADMIN_PASSWORD", "")
    if username and password and not connection.execute("SELECT 1 FROM admin_users LIMIT 1").fetchone():
        connection.execute(
            "INSERT INTO admin_users(username,password_hash) VALUES(?,?)",
            (username, generate_password_hash(password)),
        )
    connection.commit()
    connection.close()


app = create_app()

if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "5000")), debug=os.environ.get("FLASK_DEBUG") == "1")
