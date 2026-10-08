import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import current_user, ensure_admin, require_admin
from .database import SessionLocal
from .routers import auth, companies, consultants, missions, skills, training, users
from .seed import seed

log = logging.getLogger("cloudtalent")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Le schéma est géré par Alembic (`alembic upgrade head`, lancé par l'entrypoint Docker).
    db = SessionLocal()
    try:
        ensure_admin(db)
        if os.getenv("SEED_DEMO", "true").lower() == "true":
            seed(db)
    except Exception:
        db.rollback()
        log.exception("Échec de l'initialisation (admin / données de démonstration)")
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

# Droits : un admin a accès à tout ; un consultant uniquement à sa propre fiche
# (contrôle fait dans le router consultants) et au référentiel de compétences ;
# une entreprise partenaire à sa fiche et à ses missions (contrôles dans les routers
# companies et missions).
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(consultants.router, prefix="/api")
app.include_router(skills.router, prefix="/api", dependencies=[Depends(current_user)])
app.include_router(companies.router, prefix="/api")
app.include_router(missions.router, prefix="/api")
app.include_router(training.router, prefix="/api", dependencies=[Depends(require_admin)])


@app.get("/api/health", tags=["Système"])
def health():
    return {"status": "ok", "application": "CloudTalent MVP", "version": app.version}
