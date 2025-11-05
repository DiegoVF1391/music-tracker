from flask import Flask, render_template, request, redirect, url_for, jsonify
from supabase import create_client, Client
from dotenv import load_dotenv
import os

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
@app.route("/songs", methods=["GET"])
def list_songs():
    songs = supabase.table("songs").select("*, artists(name), albums(name)").execute()
    # Imprimir los datos en la consola del servidor
    #print("=== Canciones obtenidas de Supabase ===")
    #print(songs.data)  # Esto mostrará una lista de diccionarios con la información
    return render_template("songs/list.html", songs=songs.data)

@app.route("/songs/add", methods=["GET", "POST"])
def add_song():
    if request.method == "POST":
        data = {
            "name": request.form["name"],
            "project_name": request.form["project_name"],
            "path": request.form["path"],
            "genre": request.form["genre"],
            "status": request.form["status"],
            "url": request.form.get("url"),
            "album_id": request.form.get("album_id"),
            "rating": request.form.get("rating"),
            "artist_id": request.form.get("artist_id"),
            "due_date": request.form.get("due_date"),
            "release_date": request.form.get("release_date"),
        }
        supabase.table("songs").insert(data).execute()
        return redirect(url_for("list_songs"))

    artists = supabase.table("artists").select("*").execute().data
    albums = supabase.table("albums").select("*").execute().data
    return render_template("songs/add.html", artists=artists, albums=albums)

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

    # simple string fields
    for field in ['name', 'project_name', 'genre', 'status', 'path', 'url']:
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

    # resolve artist name -> artist_id
    if 'artist' in data:
        artist_name = data.get('artist')
        if not artist_name:
            update_data['artist_id'] = None
        else:
            artist_resp = supabase.table('artists').select('id').eq('name', artist_name).limit(1).execute()
            artist_rows = getattr(artist_resp, 'data', None)
            if artist_rows:
                update_data['artist_id'] = artist_rows[0].get('id')
            else:
                # leave as None if not found (do not auto-create)
                update_data['artist_id'] = None

    # resolve album name -> album_id
    if 'album' in data:
        album_name = data.get('album')
        if not album_name:
            update_data['album_id'] = None
        else:
            album_resp = supabase.table('albums').select('id').eq('name', album_name).limit(1).execute()
            album_rows = getattr(album_resp, 'data', None)
            if album_rows:
                update_data['album_id'] = album_rows[0].get('id')
            else:
                update_data['album_id'] = None

    if not update_data:
        return jsonify({'error': 'No valid fields to update provided.'}), 400

    resp = supabase.table('songs').update(update_data).eq('id', song_id).execute()
    # supabase-py may attach an 'error' attribute or return status
    if getattr(resp, 'error', None):
        return jsonify({'error': str(resp.error)}), 400

    return jsonify({'success': True, 'data': getattr(resp, 'data', None)}), 200

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
