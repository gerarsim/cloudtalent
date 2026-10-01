from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import ADMIN_EMAIL, login
from tests.test_api import make_consultant


def make_account(admin, consultant_id, email="ahmed@example.com", password="motdepasse"):
    r = admin.post("/api/users/", json={"email": email, "password": password,
                                        "role": "consultant", "consultant_id": consultant_id})
    assert r.status_code == 201, r.text
    return r.json()


def as_consultant(email="ahmed@example.com", password="motdepasse"):
    return login(TestClient(app), email, password)


def test_api_fermee_sans_jeton(anon):
    assert anon.get("/api/health").status_code == 200
    for path in ("/api/consultants/", "/api/companies/", "/api/missions/", "/api/trainings/",
                 "/api/skills/", "/api/users/", "/api/auth/me", "/api/consultants/me"):
        assert anon.get(path).status_code == 401, path
    anon.headers["Authorization"] = "Bearer faux.jeton"
    assert anon.get("/api/auth/me").status_code == 401


def test_login(anon):
    assert anon.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": "faux"}).status_code == 401
    assert anon.post("/api/auth/login", json={"email": "inconnu@example.com", "password": "x"}).status_code == 401
    me = login(anon, ADMIN_EMAIL.upper(), "admin-password").get("/api/auth/me").json()
    assert me["role"] == "admin" and me["consultant_id"] is None


def test_consultant_ne_voit_que_sa_fiche(client):
    mine = make_consultant(client, name="Ahmed", email="ahmed@example.com")
    other = make_consultant(client, name="Sophie", email="sophie@example.com")
    make_account(client, mine["id"])

    with as_consultant() as c:
        assert c.get("/api/auth/me").json()["role"] == "consultant"
        assert c.get("/api/consultants/me").json()["id"] == mine["id"]
        assert c.get(f"/api/consultants/{mine['id']}").status_code == 200

        # Gestion de sa propre fiche, réserve comprise
        r = c.put("/api/consultants/me", json={"name": "Ahmed B.", "title": "Lead", "tjm": 800,
                                               "reserve_pct": 10, "skills": [{"name": "AWS", "level": 5}]})
        assert r.status_code == 200, r.text
        assert r.json()["reserve_amount"] == 80
        assert c.get("/api/skills/").status_code == 200

        # Rien d'autre
        assert c.get(f"/api/consultants/{other['id']}").status_code == 403
        assert c.put(f"/api/consultants/{other['id']}", json={"name": "X", "title": "Y"}).status_code == 403
        assert c.delete(f"/api/consultants/{mine['id']}").status_code == 403
        assert c.get("/api/consultants/").status_code == 403
        assert c.post("/api/consultants/", json={"name": "X", "title": "Y"}).status_code == 403
        for path in ("/api/companies/", "/api/missions/", "/api/trainings/", "/api/users/"):
            assert c.get(path).status_code == 403, path

    assert client.get(f"/api/consultants/{other['id']}").json()["name"] == "Sophie"


def test_changement_mot_de_passe(client):
    make_account(client, make_consultant(client)["id"])
    with as_consultant() as c:
        bad = c.post("/api/auth/password", json={"current_password": "faux", "new_password": "nouveau-mdp"})
        assert bad.status_code == 400
        assert c.post("/api/auth/password",
                      json={"current_password": "motdepasse", "new_password": "nouveau-mdp"}).status_code == 204
    as_consultant(password="nouveau-mdp").close()


def test_gestion_des_comptes(client):
    cid = make_consultant(client)["id"]
    # Un compte consultant doit pointer vers une fiche existante
    assert client.post("/api/users/", json={"email": "x@example.com", "password": "motdepasse",
                                            "role": "consultant"}).status_code == 422
    assert client.post("/api/users/", json={"email": "x@example.com", "password": "motdepasse",
                                            "role": "consultant", "consultant_id": 999}).status_code == 422
    assert client.post("/api/users/", json={"email": "x@example.com", "password": "court",
                                            "role": "admin"}).status_code == 422
    u = make_account(client, cid)
    # Email unique, une fiche = un compte
    assert client.post("/api/users/", json={"email": "ahmed@example.com", "password": "motdepasse",
                                            "role": "admin"}).status_code == 409
    assert client.post("/api/users/", json={"email": "autre@example.com", "password": "motdepasse",
                                            "role": "consultant", "consultant_id": cid}).status_code == 409

    # Désactivation : plus de connexion, et le jeton existant est refusé
    c = as_consultant()
    r = client.put(f"/api/users/{u['id']}", json={"email": u["email"], "role": "consultant",
                                                  "consultant_id": cid, "active": False})
    assert r.status_code == 200 and r.json()["active"] is False
    assert c.get("/api/consultants/me").status_code == 401
    assert c.post("/api/auth/login", json={"email": u["email"], "password": "motdepasse"}).status_code == 401
    c.close()

    # Supprimer la fiche supprime le compte
    assert client.delete(f"/api/consultants/{cid}").status_code == 204
    assert [x["email"] for x in client.get("/api/users/").json()] == [ADMIN_EMAIL]


def test_admin_ne_peut_pas_se_retirer_ses_droits(client):
    me = client.get("/api/auth/me").json()
    assert client.delete(f"/api/users/{me['id']}").status_code == 400
    r = client.put(f"/api/users/{me['id']}", json={"email": me["email"], "role": "admin", "active": False})
    assert r.status_code == 400
