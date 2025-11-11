from flask import Flask, render_template, request, redirect, url_for, jsonify, current_app
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import sys
import subprocess
from datetime import date, timedelta, datetime

load_dotenv()

app = Flask(__name__)

# Configuración de Supabase
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# ------------------------------
# Rutas para canciones
# ------------------------------

@app.route("/", methods=["GET"])
def dashboard():
    today = date.today()

    upcoming_due = supabase.table("songs").select(
        "*, artists(name), albums(name), song_statuses(name)"
    ).gte("due_date", today.isoformat()).lte(
        "due_date", (today + timedelta(days=7)).isoformat()
    ).execute()

    upcoming_releases = supabase.table("songs").select(
        "*, artists(name), albums(name)"
    ).gte("release_date", today.isoformat()).execute()

    released_songs = supabase.table("songs").select(
        "*, artists(name), albums(name)"
    ).lte("release_date", today.isoformat()).execute()

    total_songs = supabase.table("songs").select("id", count="exact").execute().count
    completed_songs = supabase.table("songs").select("id", count="exact").eq("status", 3).execute().count

    # Obtener distribución por estado
    statuses = supabase.table("song_statuses").select("id, name").execute().data
    status_labels = []
    status_counts = []

    for status in statuses:
        count = supabase.table("songs").select("id", count="exact").eq("status", status["id"]).execute().count
        status_labels.append(status["name"])
        status_counts.append(count)

    # Obtener distribución por género
    genres = supabase.table("genres").select("id, name").execute().data
    genre_labels = []
    genre_counts = []

    for genre in genres:
        count = supabase.table("songs").select("id", count="exact").eq("genre", genre["id"]).execute().count
        genre_labels.append(genre["name"])
        genre_counts.append(count)

    # === Progreso general ===
    if total_songs > 0:
        progress_percentage = round((completed_songs / total_songs) * 100, 1)
    else:
        progress_percentage = 0

    # === Promedio de tiempo por proyecto ===
    songs_data = supabase.table("songs").select("due_date, release_date").execute().data
    durations = []

    for s in songs_data:
        if s.get("due_date") and s.get("release_date"):
            try:
                start = datetime.strptime(s["due_date"], "%Y-%m-%d")
                end = datetime.strptime(s["release_date"], "%Y-%m-%d")
                durations.append((end - start).days)
            except Exception:
                continue

    avg_duration = round(sum(durations) / len(durations), 1) if durations else 0

    # === Actividad reciente (últimos 5 cambios) ===
    recent_songs = supabase.table("songs").select("*").order("updated_at", desc=True).limit(5).execute().data

    return render_template(
        "dashboard.html",
        upcoming_due=upcoming_due.data,
        upcoming_releases=upcoming_releases.data,
        released_songs=released_songs.data,
        total_songs=total_songs,
        completed_songs=completed_songs,
        progress_percentage=progress_percentage,
        avg_duration=avg_duration,
        recent_songs=recent_songs,
        status_labels=status_labels,
        status_counts=status_counts,
        genre_labels=genre_labels,
        genre_counts=genre_counts
    )

@app.route("/songs", methods=["GET"])
def list_songs():
    songs = supabase.table("songs").select("*, artists(name, color), albums(name, color), song_statuses(name, color), genres(name, color)").execute()
    artists = supabase.table('artists').select('*').execute()
    albums = supabase.table('albums').select('*').execute()
    song_statuses = supabase.table('song_statuses').select('*').execute()
    genres = supabase.table('genres').select('*').execute()
    # Imprimir los datos en la consola del servidor
    #print("=== Canciones obtenidas de Supabase ===")
    #print(songs.data)  # Esto mostrará una lista de diccionarios con la información
    return render_template("songs/list.html", songs=songs.data, artists=artists.data, albums=albums.data, song_statuses=song_statuses.data, genres=genres.data)

@app.route("/songs/add", methods=["GET", "POST"])
def add_song():
    if request.method == "POST":
        # accept JSON or form
        data = request.get_json(silent=True)
        if not data:
            data = request.form.to_dict()

        insert_data = {}

        # simple text fields
        for field in ['name', 'project_name', 'path', 'url']:
            if field in data:
                insert_data[field] = data.get(field) or None

        # rating
        if 'rating' in data:
            try:
                insert_data['rating'] = int(data.get('rating')) if data.get('rating') not in (None, '') else None
            except Exception:
                insert_data['rating'] = None

        # dates
        for d in ['due_date', 'release_date']:
            if d in data:
                insert_data[d] = data.get(d) or None

        # in_album
        if 'in_album' in data:
            val = data.get('in_album')
            if isinstance(val, str):
                val_l = val.lower()
                insert_data['in_album'] = 1 if val_l in ('1', 'true', 't', 'yes', 'y', 'on') else 0
            else:
                try:
                    insert_data['in_album'] = 1 if int(val) else 0
                except Exception:
                    insert_data['in_album'] = 1 if bool(val) else 0

        created = {}

        # artist_id / new: token
        if 'artist_id' in data:
            a_val = data.get('artist_id')
            if not a_val:
                insert_data['artist_id'] = None
            else:
                a_str = str(a_val)
                if a_str.startswith('new:'):
                    artist_name = a_str.split(':', 1)[1]
                    ins = supabase.table('artists').insert({'name': artist_name}).execute()
                    ins_data = getattr(ins, 'data', None)
                    if ins_data and len(ins_data) > 0:
                        insert_data['artist_id'] = ins_data[0].get('id')
                        created['artist'] = {'id': ins_data[0].get('id'), 'name': ins_data[0].get('name') or artist_name}
                    else:
                        insert_data['artist_id'] = None
                else:
                    try:
                        insert_data['artist_id'] = int(a_val)
                    except Exception:
                        insert_data['artist_id'] = None

        # album_id / new:
        if 'album_id' in data:
            al_val = data.get('album_id')
            if not al_val:
                insert_data['album_id'] = None
            else:
                al_str = str(al_val)
                if al_str.startswith('new:'):
                    album_name = al_str.split(':', 1)[1]
                    ins = supabase.table('albums').insert({'name': album_name}).execute()
                    ins_data = getattr(ins, 'data', None)
                    if ins_data and len(ins_data) > 0:
                        insert_data['album_id'] = ins_data[0].get('id')
                        created['album'] = {'id': ins_data[0].get('id'), 'name': ins_data[0].get('name') or album_name}
                    else:
                        insert_data['album_id'] = None
                else:
                    try:
                        insert_data['album_id'] = int(al_val)
                    except Exception:
                        insert_data['album_id'] = None

        # genre / new:
        if 'genre' in data:
            g_val = data.get('genre')
            if not g_val:
                insert_data['genre'] = None
            else:
                g_str = str(g_val)
                if g_str.startswith('new:'):
                    genre_name = g_str.split(':', 1)[1]
                    ins = supabase.table('genres').insert({'name': genre_name}).execute()
                    ins_data = getattr(ins, 'data', None)
                    if ins_data and len(ins_data) > 0:
                        insert_data['genre'] = ins_data[0].get('id')
                        created['genre'] = {'id': ins_data[0].get('id'), 'name': ins_data[0].get('name') or genre_name}
                    else:
                        insert_data['genre'] = None
                else:
                    try:
                        insert_data['genre'] = int(g_val)
                    except Exception:
                        insert_data['genre'] = None
        elif 'genre' in data:
            # legacy string
            insert_data['genre'] = data.get('genre') or None

        # status handling
        if 'status' in data:
            try:
                insert_data['status'] = int(data.get('status')) if data.get('status') not in (None, '') else None
            except Exception:
                insert_data['status'] = None
        elif 'status' in data:
            # allow sending status as text or id
            try:
                insert_data['status'] = int(data.get('status'))
            except Exception:
                insert_data['status'] = data.get('status') or None

        # perform insert
        resp = supabase.table('songs').insert(insert_data).execute()
        if getattr(resp, 'error', None):
            # basic error handling: for form submit redirect back with an error might be better, but keep it simple
            return jsonify({'error': str(resp.error)}), 400

        result_data = getattr(resp, 'data', None)
        # if caller expects JSON, return created resource
        if request.is_json:
            out = {'success': True, 'data': result_data}
            if created:
                out['created'] = created
            return jsonify(out), 201

        # otherwise redirect back to list
        return redirect(url_for('list_songs'))

    artists = supabase.table("artists").select("*").execute().data
    albums = supabase.table("albums").select("*").execute().data
    song_statuses = supabase.table('song_statuses').select('*').execute().data
    genres = supabase.table('genres').select('*').execute().data
    return render_template("songs/add.html", artists=artists, albums=albums, song_statuses=song_statuses, genres=genres)

@app.route("/songs/delete/<int:song_id>")
def delete_song(song_id):
    supabase.table("songs").delete().eq("id", song_id).execute()
    return redirect(url_for("list_songs"))


@app.route('/songs/edit/<int:song_id>', methods=['POST'])
def edit_song(song_id):
    """Update a song. Accepts JSON (preferred) or form data.

    Expected fields (all optional):
      - in_album (1/0 or true/false)
      - name, project_name, genre, status, rating, path, url, due_date, release_date
      - artist (artist name) -> will be resolved to artist_id if exists
      - album (album name) -> will be resolved to album_id if exists
    """
    # Accept JSON or form-encoded data
    data = request.get_json(silent=True)
    if not data:
        data = request.form.to_dict()

    update_data = {}
    created = {}

    # simple string fields (leave status to status when provided)
    for field in ['name', 'project_name', 'genre', 'path', 'url']:
        if field in data:
            update_data[field] = data.get(field) or None

    # numeric/nullable
    if 'rating' in data:
        try:
            update_data['rating'] = int(data.get('rating')) if data.get('rating') not in (None, '') else None
        except ValueError:
            update_data['rating'] = None

    # dates (store as-is or None)
    for dfield in ['due_date', 'release_date']:
        if dfield in data:
            update_data[dfield] = data.get(dfield) or None

    # in_album boolean/int
    if 'in_album' in data:
        val = data.get('in_album')
        if isinstance(val, str):
            val_l = val.lower()
            update_data['in_album'] = 1 if val_l in ('1', 'true', 't', 'yes', 'y', 'on') else 0
        else:
            try:
                update_data['in_album'] = 1 if int(val) else 0
            except Exception:
                update_data['in_album'] = 1 if bool(val) else 0

    # Artist ID handling: prefer explicit artist_id, allow special 'new:<name>' token to create
    if 'artist_id' in data:
        a_val = data.get('artist_id')
        if not a_val:
            update_data['artist_id'] = None
        else:
            a_str = str(a_val)
            if a_str.startswith('new:'):
                artist_name = a_str.split(':', 1)[1]
                ins = supabase.table('artists').insert({'name': artist_name}).execute()
                ins_data = getattr(ins, 'data', None)
                if ins_data and len(ins_data) > 0:
                    update_data['artist_id'] = ins_data[0].get('id')
                    # return created artist info to client
                    created['artist'] = {'id': ins_data[0].get('id'), 'name': ins_data[0].get('name') or artist_name}
                else:
                    update_data['artist_id'] = None
            else:
                try:
                    update_data['artist_id'] = int(a_val)
                except Exception:
                    update_data['artist_id'] = None
    # fallback: resolve artist name -> artist_id
    elif 'artist' in data:
        artist_name = data.get('artist')
        if not artist_name:
            update_data['artist_id'] = None
        else:
            artist_resp = supabase.table('artists').select('id').eq('name', artist_name).limit(1).execute()
            artist_rows = getattr(artist_resp, 'data', None)
            if artist_rows:
                update_data['artist_id'] = artist_rows[0].get('id')
            else:
                # create the artist if not found
                ins = supabase.table('artists').insert({'name': artist_name}).execute()
                ins_data = getattr(ins, 'data', None)
                if ins_data and len(ins_data) > 0:
                    update_data['artist_id'] = ins_data[0].get('id')
                else:
                    update_data['artist_id'] = None

    # Album ID handling: prefer explicit album_id, allow 'new:<name>' token to create
    if 'album_id' in data:
        al_val = data.get('album_id')
        if not al_val:
            update_data['album_id'] = None
        else:
            al_str = str(al_val)
            if al_str.startswith('new:'):
                album_name = al_str.split(':', 1)[1]
                ins = supabase.table('albums').insert({'name': album_name}).execute()
                ins_data = getattr(ins, 'data', None)
                if ins_data and len(ins_data) > 0:
                    update_data['album_id'] = ins_data[0].get('id')
                    created['album'] = {'id': ins_data[0].get('id'), 'name': ins_data[0].get('name') or album_name}
                else:
                    update_data['album_id'] = None
            else:
                try:
                    update_data['album_id'] = int(al_val)
                except Exception:
                    update_data['album_id'] = None
    # fallback: resolve album name -> album_id
    elif 'album' in data:
        album_name = data.get('album')
        if not album_name:
            update_data['album_id'] = None

    # Genre ID handling: prefer explicit genre, allow 'new:<name>' token to create
    if 'genre' in data:
        g_val = data.get('genre')
        if not g_val:
            update_data['genre'] = None
        else:
            g_str = str(g_val)
            if g_str.startswith('new:'):
                genre_name = g_str.split(':', 1)[1]
                ins = supabase.table('genres').insert({'name': genre_name}).execute()
                ins_data = getattr(ins, 'data', None)
                if ins_data and len(ins_data) > 0:
                    update_data['genre'] = ins_data[0].get('id')
                    created['genre'] = {'id': ins_data[0].get('id'), 'name': ins_data[0].get('name') or genre_name}
                else:
                    update_data['genre'] = None
            else:
                try:
                    update_data['genre'] = int(g_val)
                except Exception:
                    update_data['genre'] = None
    # fallback: allow legacy 'genre' string (kept for compatibility)
    elif 'genre' in data:
        if data.get('genre'):
            update_data['genre'] = data.get('genre')

    # Status ID handling: prefer explicit status (reference to song_statuses table)
    if 'status' in data:
        s_val = data.get('status')
        if not s_val:
            update_data['status'] = None
        else:
            try:
                update_data['status'] = int(s_val)
            except Exception:
                update_data['status'] = None
    # fallback: allow old 'status' string field (kept for backward compatibility)
    elif 'status' in data:
        update_data['status'] = data.get('status') or None

    if not update_data:
        return jsonify({'error': 'No valid fields to update provided.'}), 400

    resp = supabase.table('songs').update(update_data).eq('id', song_id).execute()
    # supabase-py may attach an 'error' attribute or return status
    if getattr(resp, 'error', None):
        return jsonify({'error': str(resp.error)}), 400

    result = {'success': True, 'data': getattr(resp, 'data', None)}
    if created:
        result['created'] = created
    return jsonify(result), 200


# Endpoint to open a local file on the server (useful when running locally).
# Security: only allow opening paths that are under a configured base directory.
@app.route('/open-file', methods=['POST'])
def open_file():
    data = request.get_json(silent=True)
    if not data or 'path' not in data:
        return jsonify({'success': False, 'error': 'No path provided.'}), 400
    path = data.get('path')
    # normalize
    try:
        abs_path = os.path.abspath(path)
    except Exception as e:
        return jsonify({'success': False, 'error': f'Invalid path: {e}'}), 400

    # Allowed base dir from env variable; if not set, default to app root
    base = os.environ.get('OPEN_BASE_DIR')
    if not base:
        base = os.path.abspath(os.getcwd())
    else:
        base = os.path.abspath(base)

    if not abs_path.startswith(base):
        return jsonify({'success': False, 'error': 'Path not allowed. Set OPEN_BASE_DIR if you need to open files outside the project.'}), 403

    # Try to open the file on the host machine where the server runs
    try:
        if sys.platform.startswith('win'):
            os.startfile(abs_path)
        elif sys.platform.startswith('darwin'):
            subprocess.Popen(['open', abs_path])
        else:
            # linux
            subprocess.Popen(['xdg-open', abs_path])
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

    return jsonify({'success': True}), 200

# ------------------------------
# Rutas para artistas y álbumes
# ------------------------------

@app.route("/artists")
def list_artists():
    artists = supabase.table("artists").select("*").execute()
    return render_template("artists/list.html", artists=artists.data)

@app.route("/albums")
def list_albums():
    albums = supabase.table("albums").select("*").execute()
    return render_template("albums/list.html", albums=albums.data)

if __name__ == "__main__":
    app.run(debug=True)
