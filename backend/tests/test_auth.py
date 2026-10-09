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

        # Gestion de sa propre fiche, réserve comprise ; nom et TJM restent ceux fixés par l'admin
        r = c.put("/api/consultants/me", json={"name": "Ahmed B.", "title": "Lead", "tjm": 800,
                                               "reserve_pct": 10, "skills": [{"name": "AWS", "level": 5}]})
        assert r.status_code == 200, r.text
        assert (r.json()["name"], r.json()["tjm"], r.json()["reserve_amount"]) == ("Ahmed", 700, 70)
        assert c.put(f"/api/consultants/{mine['id']}", json={"name": "X", "title": "Y", "tjm": 2000}).status_code == 403
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


def test_profil_consultant_mission_et_salaire(client):
    m = client.post("/api/missions/", json={"title": "DevOps Banque", "tjm_max": 800}).json()
    mine = make_consultant(client, email="ahmed@example.com", tjm=700, reserve_pct=10, mission_id=m["id"])
    assert client.post("/api/consultants/", json={"name": "X", "title": "Y", "mission_id": 999}).status_code == 422
    make_account(client, mine["id"])

    with as_consultant() as c:
        me = c.get("/api/consultants/me").json()
        assert me["mission"]["title"] == "DevOps Banque"
        # 700 € × 20 j = 14 000 € ; réserve 10 % = 1 400 € ; salaire = 12 600 €
        assert me["monthly"] == {"days_per_month": 20, "revenue": 14000, "reserve": 1400, "salary": 12600}

        r = c.put("/api/consultants/me", json={"title": "DevOps", "reserve_pct": 15, "days_per_month": 18,
                                               "mission_id": None})
        assert r.status_code == 200, r.text
        assert r.json()["monthly"] == {"days_per_month": 18, "revenue": 12600, "reserve": 1890, "salary": 10710}
        assert r.json()["mission"]["id"] == m["id"]  # la mission reste gérée par l'admin

    # Mission supprimée : le consultant n'a plus de mission
    assert client.delete(f"/api/missions/{m['id']}").status_code == 204
    assert client.get(f"/api/consultants/{mine['id']}").json()["mission"] is None


def test_cv(client):
    mine = make_consultant(client, email="ahmed@example.com")
    other = make_consultant(client, name="Sophie", email="sophie@example.com")
    make_account(client, mine["id"])

    with as_consultant() as c:
        assert c.get("/api/consultants/me/cv").status_code == 404
        bad = c.put("/api/consultants/me/cv", files={"file": ("cv.exe", b"MZ", "application/pdf")})
        assert bad.status_code == 422
        big = c.put("/api/consultants/me/cv", files={"file": ("cv.pdf", b"x" * (5 * 1024 * 1024 + 1))})
        assert big.status_code == 413

        r = c.put("/api/consultants/me/cv", files={"file": ("Mon CV é.pdf", b"%PDF-1.4 cv", "text/html")})
        assert r.status_code == 200, r.text
        assert (r.json()["cv"]["filename"], r.json()["cv"]["size"]) == ("Mon CV é.pdf", 11)

        dl = c.get("/api/consultants/me/cv")
        assert dl.content == b"%PDF-1.4 cv"
        assert dl.headers["content-type"] == "application/pdf"  # jamais le type envoyé par le client
        assert "attachment" in dl.headers["content-disposition"]

        # Pas d'accès au CV d'un autre
        assert c.get(f"/api/consultants/{other['id']}/cv").status_code == 403
        assert c.put(f"/api/consultants/{other['id']}/cv", files={"file": ("cv.pdf", b"x")}).status_code == 403

    # L'admin voit le CV ; le remplacement écrase l'ancien
    assert client.get(f"/api/consultants/{mine['id']}/cv").content == b"%PDF-1.4 cv"
    client.put(f"/api/consultants/{mine['id']}/cv", files={"file": ("v2.docx", b"PK v2")})
    assert client.get(f"/api/consultants/{mine['id']}").json()["cv"]["filename"] == "v2.docx"
    assert client.delete(f"/api/consultants/{mine['id']}/cv").status_code == 204
    assert client.get(f"/api/consultants/{mine['id']}").json()["cv"] is None


def test_offres_du_consultant(client):
    from tests.test_api import make_mission

    me = make_consultant(client, email="ahmed@example.com", reserve_pct=10)  # AWS 5, Kubernetes 4, Terraform 4
    make_account(client, me["id"])
    company = client.post("/api/companies/", json={"name": "Banque", "sector": "Banking"}).json()
    # Éligible, TJM fixé par l'admin
    fixed = make_mission(client, title="Fixé", company_id=company["id"], tjm_max=900, consultant_tjm=720,
                         skills=[{"name": "AWS", "min_level": 4}, {"name": "Terraform", "min_level": 3}])
    # Éligible, TJM calculé : 800 − 15 % = 680
    auto = make_mission(client, title="Auto", tjm_max=800, skills=[{"name": "k8s", "min_level": 5}])
    # Non éligible (compétence obligatoire manquante), fermée, ou mission en cours : jamais proposées
    make_mission(client, title="Azure", skills=[{"name": "Azure"}, {"name": "AWS"}])
    make_mission(client, title="Fermée", status="Fermée", skills=[{"name": "AWS"}])
    current = make_mission(client, title="En cours", skills=[{"name": "AWS"}])
    client.put(f"/api/consultants/{me['id']}", json={**me, "skills": [{"name": s["skill"]["name"], "level": s["level"]}
                                                                          for s in me["skills"]], "mission_id": current["id"]})
    client.post("/api/proposals/", json={"mission_id": fixed["id"], "consultant_id": me["id"]})

    with as_consultant() as c:
        offers = c.get("/api/consultants/me/offers").json()
        assert [o["mission"]["title"] for o in offers] == ["Fixé", "Auto"]  # classées par score
        first, second = offers
        assert (first["tjm"], first["sector"], first["proposal_status"]) == (720, "Banking", "Proposé")
        # 720 € × 20 j = 14 400 € ; réserve 10 % ; salaire 12 960 €
        assert first["monthly"] == {"days_per_month": 20, "revenue": 14400, "reserve": 1440, "salary": 12960}
        assert (second["tjm"], second["proposal_status"]) == (680, None)
        # Ni le nom de l'entreprise ni son TJM max
        assert not {"company", "tjm_max"} & first["mission"].keys()

    # L'entreprise ne voit jamais le TJM proposé au consultant, et ne peut pas le modifier
    client.post("/api/users/", json={"email": "rh@banque.lu", "password": "motdepasse", "role": "company",
                                     "company_id": company["id"]})
    with as_consultant("rh@banque.lu") as co:
        m = co.get(f"/api/missions/{fixed['id']}").json()
        assert (m["consultant_tjm"], m["offered_tjm"]) == (None, None)
        co.put(f"/api/missions/{fixed['id']}", json={"title": "Fixé", "tjm_max": 900, "consultant_tjm": 1})
    assert client.get(f"/api/missions/{fixed['id']}").json()["consultant_tjm"] == 720
    assert client.get("/api/consultants/me/offers").status_code == 404  # l'admin n'a pas de fiche consultant
