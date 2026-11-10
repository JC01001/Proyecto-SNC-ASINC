"""Aplicación ASÍNCRONA: FastAPI + PyMongo Async (AsyncMongoClient). Puerto 8000."""
import asyncio
import time
from contextlib import asynccontextmanager

from bson import ObjectId
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pymongo import AsyncMongoClient, InsertOne

from common import *

client = AsyncMongoClient(MONGODB_URI)
movies = client[DB_NAME][COLLECTION]


@asynccontextmanager
async def lifespan(app):
    yield
    await client.close()


app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")


def clean(doc):
    doc["_id"] = str(doc["_id"])
    return doc


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {"mode": "ASÍNCRONO", "driver": "PyMongo Async (AsyncMongoClient)"})


# ---------- CONSULTAS ----------
@app.get("/api/random")
async def random_movies():
    t = time.perf_counter()
    cursor = await movies.aggregate([{"$match": {"poster": {"$exists": True}}}, {"$sample": {"size": 5}}])
    docs = await cursor.to_list(5)
    return {"movies": [clean(d) for d in docs], "ms": round((time.perf_counter() - t) * 1000)}


@app.get("/api/search")
async def search(q: str = "", genre: str = "", year_min: str = "", year_max: str = "", min_rating: str = ""):
    t = time.perf_counter()
    f = build_filter(q, genre, int(year_min or 0), int(year_max or 0), float(min_rating or 0))
    # asyncio.gather: la búsqueda y el conteo se ejecutan al mismo tiempo
    docs, total = await asyncio.gather(
        movies.find(f).sort("imdb.rating", -1).limit(20).to_list(20),
        movies.count_documents(f),
    )
    return {"movies": [clean(d) for d in docs], "total": total, "ms": round((time.perf_counter() - t) * 1000)}


# ---------- CARGA MASIVA ----------
@app.post("/api/bulk")
async def bulk_load():
    t = time.perf_counter()
    docs = make_movies()
    batches = [docs[i:i + BATCH_SIZE] for i in range(0, len(docs), BATCH_SIZE)]
    sem = asyncio.Semaphore(3)  # máximo 3 bulk_write simultáneos
    inserted = 0

    async def send(batch):
        nonlocal inserted
        async with sem:
            r = await movies.bulk_write([InsertOne(d) for d in batch], ordered=False)
            inserted += r.inserted_count

    # TaskGroup: lanza todos los lotes en paralelo y espera a que terminen
    async with asyncio.TaskGroup() as tg:
        for b in batches:
            tg.create_task(send(b))
    return {"inserted": inserted, "ms": round((time.perf_counter() - t) * 1000)}


@app.delete("/api/bulk")
async def bulk_delete():
    r = await movies.delete_many({"bulk": True})
    return {"deleted": r.deleted_count}


# ---------- CRUD ----------
@app.post("/api/movies")
async def create(body: dict):
    r = await movies.insert_one(movie_from_body(body))
    return {"_id": str(r.inserted_id)}


@app.put("/api/movies/{id}")
async def update(id: str, body: dict):
    r = await movies.update_one({"_id": ObjectId(id)}, {"$set": movie_from_body(body)})
    if not r.matched_count:
        raise HTTPException(404, "No encontrada")
    return {"ok": True}


@app.delete("/api/movies/{id}")
async def delete(id: str):
    r = await movies.delete_one({"_id": ObjectId(id)})
    if not r.deleted_count:
        raise HTTPException(404, "No encontrada")
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
