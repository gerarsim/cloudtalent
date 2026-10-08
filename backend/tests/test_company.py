from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import login
from tests.test_api import make_consultant, make_mission


def make_company(admin, name="Banque", **kw):
    r = admin.post("/api/companies/", json={"name": name, **kw})
    assert r.status_code == 201, r.text
    return r.json()


def make_company_account(admin, company_id, email="rh@banque.lu", password="motdepasse"):
    r = admin.post("/api/users/", json={"email": email, "password": password,
                                        "role": "company", "company_id": company_id})
    assert r.status_code == 201, r.text
    return r.json()


def as_company(email="rh@banque.lu", password="motdepasse"):
    return login(TestClient(app), email, password)


def test_compte_entreprise_doit_pointer_vers_une_entreprise(client):
    body = {"email": "x@example.com", "password": "motdepasse", "role": "company"}
    assert client.post("/api/users/", json=body).status_code == 422
    assert client.post("/api/users/", json={**body, "company_id": 999}).status_code == 422
    u = make_company_account(client, make_company(client)["id"])
    assert (u["role"], u["consultant_id"]) == ("company", None)


def test_entreprise_gere_sa_fiche(client):
    mine = make_company(client)
    other = make_company(client, name="Autre")
    make_company_account(client, mine["id"])

    with as_company() as c:
        r = c.put("/api/companies/me", json={"name": "Banque SA", "phone": "+352 1234", "vat_number": "LU123",
                                             "website": "https://banque.lu", "description": "Banque privée"})
        assert r.status_code == 200, r.text
        assert (r.json()["id"], r.json()["vat_number"]) == (mine["id"], "LU123")
        assert c.get("/api/companies/me").json()["name"] == "Banque SA"
        assert c.put("/api/companies/me", json={"name": "B", "website": "javascript:alert(1)"}).status_code == 422

        # Pas les autres entreprises, ni les consultants, comptes ou formations
        assert c.get("/api/companies/").status_code == 403
        assert c.get(f"/api/companies/{other['id']}").status_code == 403
        assert c.put(f"/api/companies/{other['id']}", json={"name": "X"}).status_code == 403
        for path in ("/api/consultants/", "/api/users/", "/api/trainings/"):
            assert c.get(path).status_code == 403, path
        assert c.get("/api/skills/").status_code == 200


def test_entreprise_gere_ses_missions(client):
    mine = make_company(client)
    other = make_company(client, name="Autre")
    theirs = make_mission(client, title="Mission Autre", company_id=other["id"])
    make_company_account(client, mine["id"])

    with as_company() as c:
        # company_id forcé à sa propre entreprise, même si le client en envoie un autre
        r = c.post("/api/missions/", json={"title": "Platform Engineer", "company_id": other["id"], "tjm_max": 750,
                                           "description": "Migration EKS", "skills": [{"name": "k8s", "min_level": 4}]})
        assert r.status_code == 201, r.text
        m = r.json()
        assert (m["company"]["id"], m["description"], m["skills"][0]["skill"]["name"]) == (mine["id"], "Migration EKS", "Kubernetes")

        assert [x["id"] for x in c.get("/api/missions/").json()] == [m["id"]]
        r = c.put(f"/api/missions/{m['id']}", json={"title": "Platform Engineer", "status": "Pourvue",
                                                     "company_id": other["id"]})
        assert r.status_code == 200 and r.json()["company"]["id"] == mine["id"]

        # Pas les missions des autres, ni le matching (données consultants)
        for method in ("get", "delete"):
            assert getattr(c, method)(f"/api/missions/{theirs['id']}").status_code == 404
        assert c.put(f"/api/missions/{theirs['id']}", json={"title": "X"}).status_code == 404
        assert c.get(f"/api/missions/{m['id']}/matches").status_code == 403

        assert c.delete(f"/api/missions/{m['id']}").status_code == 204

    # L'admin voit toujours tout
    assert client.get(f"/api/missions/{theirs['id']}").status_code == 200


def test_consultant_sans_acces_entreprise(client):
    cid = make_consultant(client, email="ahmed@example.com")["id"]
    client.post("/api/users/", json={"email": "ahmed@example.com", "password": "motdepasse",
                                     "role": "consultant", "consultant_id": cid})
    with login(TestClient(app), "ahmed@example.com", "motdepasse") as c:
        assert c.get("/api/companies/me").status_code == 403
        assert c.post("/api/missions/", json={"title": "X"}).status_code == 403


def test_supprimer_entreprise_supprime_ses_comptes(client):
    cid = make_company(client)["id"]
    make_company_account(client, cid)
    assert client.delete(f"/api/companies/{cid}").status_code == 204
    assert all(u["role"] != "company" for u in client.get("/api/users/").json())


def test_seed_cree_compte_entreprise_demo():
    from app.database import SessionLocal
    from app.seed import DEMO_COMPANY_EMAIL, DEMO_COMPANY_PASSWORD, seed

    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
    with TestClient(app) as anon:
        with login(anon, DEMO_COMPANY_EMAIL, DEMO_COMPANY_PASSWORD) as c:
            assert c.get("/api/companies/me").json()["name"] == "Demo Bank Luxembourg"
            assert [m["title"] for m in c.get("/api/missions/").json()] == ["Senior DevOps Engineer"]
