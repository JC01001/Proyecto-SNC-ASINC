#sincrono
import time

from bson import ObjectId
from flask import Flask, jsonify, render_template, request
from pymongo import MongoClient, InsertOne

from common import *

client = MongoClient(MONGODB_URI)
movies = client[DB_NAME][COLLECTION]

app = Flask(__name__)


def clean(doc):
    doc["_id"] = str(doc["_id"])
    return doc


@app.get("/")
def home():
    return render_template("index.html", mode="SÍNCRONO")


#CONSULTAS
@app.get("/api/random")
def random_movies():
    t = time.perf_counter()
    docs = list(movies.aggregate([{"$match": {"poster": {"$exists": True}}}, {"$sample": {"size": 5}}]))
    return jsonify(movies=[clean(d) for d in docs], ms=round((time.perf_counter() - t) * 1000))


@app.get("/api/search")
def search():
    t = time.perf_counter()
    a = request.args
    f = build_filter(a.get("q", ""), a.get("genre", ""), int(a.get("year_min") or 0),
                     int(a.get("year_max") or 0), float(a.get("min_rating") or 0))
    # Síncrono: primero la búsqueda, y hasta que termina, el conteo
    docs = list(movies.find(f).sort("imdb.rating", -1).limit(20))
    total = movies.count_documents(f)
    return jsonify(movies=[clean(d) for d in docs], total=total, ms=round((time.perf_counter() - t) * 1000))


#CARGA MASIVA
@app.post("/api/bulk")
def bulk_load():
    t = time.perf_counter()
    docs = make_movies()
    inserted = 0
    # Lotes uno tras otro, cada bulk_write bloquea hasta terminar
    for i in range(0, len(docs), BATCH_SIZE):
        r = movies.bulk_write([InsertOne(d) for d in docs[i:i + BATCH_SIZE]], ordered=False)
        inserted += r.inserted_count
    return jsonify(inserted=inserted, ms=round((time.perf_counter() - t) * 1000))


@app.delete("/api/bulk")
def bulk_delete():
    r = movies.delete_many({"bulk": True})
    return jsonify(deleted=r.deleted_count)


#CRUD
@app.post("/api/movies")
def create():
    r = movies.insert_one(movie_from_body(request.get_json()))
    return jsonify(_id=str(r.inserted_id))


@app.put("/api/movies/<id>")
def update(id):
    r = movies.update_one({"_id": ObjectId(id)}, {"$set": movie_from_body(request.get_json())})
    if not r.matched_count:
        return jsonify(detail="No encontrada"), 404
    return jsonify(ok=True)


@app.delete("/api/movies/<id>")
def delete(id):
    r = movies.delete_one({"_id": ObjectId(id)})
    if not r.deleted_count:
        return jsonify(detail="No encontrada"), 404
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8001)
