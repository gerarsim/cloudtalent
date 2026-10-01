import os
import pathlib
import tempfile

# La base de test doit être configurée AVANT l'import de l'application.
_tmp = pathlib.Path(tempfile.mkdtemp()) / "test.db"
# On écrase volontairement DATABASE_URL : les tests vident les tables, ils ne doivent
# jamais tourner sur la base de dev. Pour tester sur Postgres, définir TEST_DATABASE_URL
# vers une base dédiée.
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", f"sqlite:///{_tmp}")
os.environ["SEED_DEMO"] = "false"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["ADMIN_EMAIL"] = ADMIN_EMAIL = "admin@example.com"
os.environ["ADMIN_PASSWORD"] = ADMIN_PASSWORD = "admin-password"

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _alembic() -> Config:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    return cfg


@pytest.fixture(scope="session", autouse=True)
def schema():
    # On passe par la vraie migration : si elle diverge des modèles, les tests cassent.
    Base.metadata.drop_all(engine)
    with engine.begin() as c:
        c.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
    command.upgrade(_alembic(), "head")
    yield
    command.downgrade(_alembic(), "base")


@pytest.fixture(autouse=True)
def clean_tables():
    yield
    with engine.begin() as c:
        for table in reversed(Base.metadata.sorted_tables):
            c.execute(table.delete())


def login(client: TestClient, email: str, password: str) -> TestClient:
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return client


@pytest.fixture
def anon():
    """Client non authentifié. Le démarrage crée le compte admin (ADMIN_EMAIL)."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client(anon):
    """Client connecté en admin (accès complet)."""
    return login(anon, ADMIN_EMAIL, ADMIN_PASSWORD)
