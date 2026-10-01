import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import SessionLocal
from .routers import companies, consultants, missions, skills, training
from .seed import seed

log = logging.getLogger("cloudtalent")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Le schéma est géré par Alembic (`alembic upgrade head`, lancé par l'entrypoint Docker).
    if os.getenv("SEED_DEMO", "true").lower() == "true":
        db = SessionLocal()
        try:
            seed(db)
        except Exception:
            db.rollback()
            log.exception("Échec du chargement des données de démonstration")
        finally:
            db.close()
    yield


app = FastAPI(title="CloudTalent MVP", version="0.2.0", lifespan=lifespan)

# En dev, le frontend passe par le proxy Vite (même origine) : CORS n'est utile que
# si on appelle l'API depuis une autre origine. Liste séparée par des virgules.
origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (consultants, companies, missions, training, skills):
    app.include_router(r.router, prefix="/api")


@app.get("/api/health", tags=["Système"])
def health():
    return {"status": "ok", "application": "CloudTalent MVP", "version": app.version}
