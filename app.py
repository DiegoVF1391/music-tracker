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
