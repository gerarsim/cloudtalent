from datetime import date, timedelta


def make_consultant(client, **kw):
    body = {"name": "Ahmed", "title": "DevOps", "tjm": 700,
            "skills": [{"name": "AWS", "level": 5}, {"name": "k8s", "level": 4}, {"name": "Terraform", "level": 4}]}
    body.update(kw)
    r = client.post("/api/consultants/", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def make_mission(client, **kw):
    body = {"title": "Senior DevOps", "tjm_max": 800,
            "skills": [{"name": "AWS", "min_level": 4}, {"name": "Kubernetes", "min_level": 4},
                       {"name": "ArgoCD", "required": False}]}
    body.update(kw)
    r = client.post("/api/missions/", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_synonymes_et_casse_normalises(client):
    c = make_consultant(client, skills=[{"name": "k8s", "level": 3}, {"name": "  KUBERNETES ", "level": 5}])
    assert [(s["skill"]["name"], s["level"]) for s in c["skills"]] == [("Kubernetes", 5)]
    names = [s["name"] for s in client.get("/api/skills/").json()]
    assert names.count("Kubernetes") == 1


def test_validation(client):
    assert client.post("/api/consultants/", json={"name": "X", "title": "Y", "tjm": -1}).status_code == 422
    assert client.post("/api/consultants/", json={"name": "X", "title": "Y", "email": "pas-un-email"}).status_code == 422
    assert client.post("/api/consultants/", json={"name": "", "title": "Y"}).status_code == 422
    assert client.post("/api/consultants/",
                       json={"name": "X", "title": "Y", "skills": [{"name": "AWS", "level": 9}]}).status_code == 422
    assert client.post("/api/missions/", json={"title": "M", "status": "Bidon"}).status_code == 422


def test_email_unique_409(client):
    make_consultant(client, email="a@example.com")
    r = client.post("/api/consultants/", json={"name": "B", "title": "T", "email": "a@example.com"})
    assert r.status_code == 409


def test_crud_consultant(client):
    c = make_consultant(client)
    r = client.put(f"/api/consultants/{c['id']}",
                   json={"name": "Ahmed B.", "title": "Lead", "tjm": 750, "skills": [{"name": "Azure", "level": 2}]})
    assert r.status_code == 200
    assert r.json()["name"] == "Ahmed B." and [s["skill"]["name"] for s in r.json()["skills"]] == ["Azure"]
    assert client.delete(f"/api/consultants/{c['id']}").status_code == 204
    assert client.get(f"/api/consultants/{c['id']}").status_code == 404


def test_404(client):
    for path in ("/api/consultants/999", "/api/companies/999", "/api/missions/999",
                 "/api/trainings/999", "/api/missions/999/matches"):
        assert client.get(path).status_code == 404, path


def test_mission_company_fk(client):
    assert client.post("/api/missions/", json={"title": "M", "company_id": 42}).status_code == 422
    co = client.post("/api/companies/", json={"name": "Bank"}).json()
    m = make_mission(client, company_id=co["id"])
    assert m["company"] == {"id": co["id"], "name": "Bank"}
    # suppression de l'entreprise -> la mission reste, sans entreprise
    assert client.delete(f"/api/companies/{co['id']}").status_code == 204
    assert client.get(f"/api/missions/{m['id']}").json()["company"] is None


def test_filtre_statut_mission(client):
    make_mission(client, title="A")
    make_mission(client, title="B", status="Pourvue")
    assert [m["title"] for m in client.get("/api/missions/?status=Ouverte").json()] == ["A"]


def test_matches_format_constant(client):
    make_consultant(client, name="Fort")
    make_consultant(client, name="Azure only", skills=[{"name": "Azure", "level": 5}])
    make_consultant(client, name="Partiel", skills=[{"name": "AWS", "level": 3}])
    m = make_mission(client)

    res = client.get(f"/api/missions/{m['id']}/matches").json()
    assert [x["consultant"]["name"] for x in res] == ["Fort", "Partiel"]
    top = res[0]
    assert set(top) >= {"consultant", "score", "skill_score", "eligible", "matched", "missing", "tjm_ok", "available"}
    assert top["eligible"] and [s["name"] for s in top["missing"]] == ["ArgoCD"]
    assert not res[1]["eligible"]

    eligibles = client.get(f"/api/missions/{m['id']}/matches?only_eligible=true").json()
    assert [x["consultant"]["name"] for x in eligibles] == ["Fort"]

    vide = make_mission(client, title="Sans compétences", skills=[])
    assert client.get(f"/api/missions/{vide['id']}/matches").json() == []


def test_matches_disponibilite(client):
    start = date.today() + timedelta(days=10)
    make_consultant(client, name="Tard", available_from=str(start + timedelta(days=60)))
    make_consultant(client, name="Dispo")
    m = make_mission(client, start_date=str(start))
    res = client.get(f"/api/missions/{m['id']}/matches").json()
    assert [(x["consultant"]["name"], x["available"]) for x in res] == [("Dispo", True), ("Tard", False)]


def test_training_skill(client):
    r = client.post("/api/trainings/", json={"title": "TF", "skill": "tf", "level": "Avancé", "price": 900})
    assert r.status_code == 201 and r.json()["skill"]["name"] == "Terraform"


def test_seed_idempotent():
    from app.database import SessionLocal
    from app.models import Consultant, Mission
    from app.seed import seed

    db = SessionLocal()
    try:
        seed(db)
        seed(db)
        assert db.query(Consultant).count() == 3
        assert db.query(Mission).count() == 1
    finally:
        db.close()
