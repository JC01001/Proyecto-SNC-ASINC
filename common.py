#config, filtros, datos de carga masiva
import os
import random
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "").strip()
DB_NAME = os.getenv("DB_NAME", "sample_mflix")
COLLECTION = os.getenv("COLLECTION_NAME", "movies")

if not MONGODB_URI:
    raise SystemExit("falta el link de el cluster")

BULK_TOTAL = 1000   #las mil peliculas de la carga masiva
BATCH_SIZE = 100    #bulk_write(los lotes)

GENRES = [
    "Action", "Adventure", "Animation", "Biography", "Comedy", "Crime",
    "Documentary", "Drama", "Family", "Fantasy", "Film-Noir", "History",
    "Horror", "Music", "Musical", "Mystery", "News", "Romance", "Sci-Fi",
    "Short", "Sport", "Talk-Show", "Thriller", "War", "Western"
]

#filtros
def build_filter(q=None, genre=None, year_min=None, year_max=None, min_rating=None):
    f = {}
    if q:
        f["title"] = {"$regex": q, "$options": "i"} #busca lo que contenga el titulo y es insensible a mayus o minus
    if genre and genre != "todos": #si no esta vacio y es diferente si filtra
        f["genres"] = genre
    year = {}
    if year_min:
        year["$gte"] = year_min
    if year_max:
        year["$lte"] = year_max
    if year:
        f["year"] = year
    if min_rating:
        f["imdb.rating"] = {"$gte": min_rating}
    return f

#genrar las 1000 peliculas con datos
def make_movies(n=BULK_TOTAL):
    return [{
        "title": f"Pelicula Masiva {i}",
        "year": random.randint(1950, 2026),
        "genres": random.sample(GENRES, 2),
        "plot": "Pelicula de carga masiva",
        "runtime": random.randint(80, 180),
        "imdb": {"rating": round(random.uniform(3, 9.5), 1)},
        "bulk": True,
    } for i in range(1, n + 1)]

#json a formulario para mongo
def movie_from_body(b):
    return {
        "title": b["title"].strip(),
        "year": int(b["year"]),
        "genres": [g.strip() for g in b.get("genres", "").split(",") if g.strip()],
        "plot": b.get("plot", ""),
        "imdb": {"rating": float(b.get("rating") or 0)},
    }
