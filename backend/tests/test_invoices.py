from tests.test_api import make_consultant, make_mission
from tests.test_auth import as_consultant, make_account
from tests.test_company import as_company, make_company, make_company_account

PDF = ("facture-2026-09.pdf", b"%PDF-1.4 facture signee", "application/pdf")


def setup(client, billing_tjm=800):
    company = make_company(client)
    mission = make_mission(client, company_id=company["id"])
    c = make_consultant(client, tjm=650, mission_id=mission["id"], billing_tjm=billing_tjm, days_per_month=20)
    make_account(client, c["id"])
    make_company_account(client, company["id"])
    return c, mission, company


def deposit(cl, period="2026-09", days=18, file=PDF):
    return cl.post("/api/invoices/", data={"period": period, "days": str(days)}, files={"file": file})


def test_marge_admin_par_jour_semaine_mois(client):
    c, _, _ = setup(client)
    assert (c["billing_tjm"], c["effective_billing_tjm"]) == (800, 800)
    assert c["margin"] == {"per_day": 150, "per_week": 750, "per_month": 3000}
    assert client.get(f"/api/consultants/{c['id']}").json()["margin"]["per_day"] == 150
    assert client.get("/api/consultants/").json()[0]["margin"]["per_month"] == 3000

    # Sans TJM client explicite : TJM max de la mission (800 ici)
    other = make_consultant(client, name="Marc", email="marc@example.com", tjm=700,
                            mission_id=c["mission"]["id"])
    assert (other["billing_tjm"], other["margin"]["per_day"]) == (None, 100)
    # Ni mission ni TJM client : pas de marge
    assert make_consultant(client, name="Lea", email="lea@example.com")["margin"] is None
    assert client.put(f"/api/consultants/{c['id']}", json={"name": "Ahmed", "tjm": 650, "billing_tjm": -1}).status_code == 422

    with as_consultant() as me:
        for body in (me.get("/api/consultants/me").json(), me.get(f"/api/consultants/{c['id']}").json()):
            assert "billing_tjm" not in body and "margin" not in body


def test_consultant_depose_et_remplace_sa_facture(client):
    setup(client)
    with as_consultant() as me:
        r = deposit(me)
        assert r.status_code == 201, r.text
        inv = r.json()
        assert (inv["status"], inv["days"], inv["consultant_tjm"], inv["consultant_amount"]) == ("Déposée", 18, 650, 11700)
        assert (inv["billing_tjm"], inv["amount"], inv["margin"]) == (None, None, None)

        r = deposit(me, days=20, file=("v2.png", b"\x89PNG", "image/png"))
        assert r.status_code == 201 and r.json()["id"] == inv["id"] and r.json()["filename"] == "v2.png"
        assert len(me.get("/api/invoices/").json()) == 1

        assert deposit(me, file=("x.exe", b"MZ", "application/octet-stream")).status_code == 422
        assert deposit(me, file=("vide.pdf", b"", "application/pdf")).status_code == 422
        assert deposit(me, period="2026-13").status_code == 422
        assert deposit(me, days=0).status_code == 422
        assert deposit(me, days=32).status_code == 422

        r = me.get(f"/api/invoices/{inv['id']}/file")
        assert r.status_code == 200 and r.content == b"\x89PNG"
        assert r.headers["x-content-type-options"] == "nosniff"

    # Ni l'admin ni l'entreprise ne déposent
    assert deposit(client).status_code == 403
    with as_company() as co:
        assert deposit(co).status_code == 403


def test_admin_voit_la_marge_et_demande_le_paiement(client):
    setup(client)
    with as_consultant() as me:
        inv = deposit(me).json()

    rows = client.get("/api/invoices/").json()
    assert len(rows) == 1
    row = rows[0]
    assert (row["amount"], row["consultant_amount"], row["margin"]) == (14400, 11700, 2700)
    assert row["mission"]["company"]["name"] == "Banque"

    # Pas encore demandée : invisible pour l'entreprise
    with as_company() as co:
        assert co.get("/api/invoices/").json() == []
        assert co.get(f"/api/invoices/{inv['id']}/file").status_code == 404

    r = client.put(f"/api/invoices/{inv['id']}", json={"status": "Paiement demandé"})
    assert r.status_code == 200 and r.json()["requested_at"]

    with as_company() as co:
        rows = co.get("/api/invoices/").json()
        assert [(x["amount"], x["billing_tjm"], x["consultant_amount"], x["margin"], x["consultant_tjm"])
                for x in rows] == [(14400, 800, None, None, None)]
        assert co.get(f"/api/invoices/{inv['id']}/file").status_code == 200
        assert co.put(f"/api/invoices/{inv['id']}", json={"status": "Payée"}).status_code == 403
        assert co.delete(f"/api/invoices/{inv['id']}").status_code == 403

    with as_consultant() as me:
        # Paiement demandé : plus de remplacement ni de suppression
        assert deposit(me).status_code == 409
        assert me.delete(f"/api/invoices/{inv['id']}").status_code == 403
        assert me.put(f"/api/invoices/{inv['id']}", json={"status": "Payée"}).status_code == 403

    r = client.put(f"/api/invoices/{inv['id']}", json={"status": "Payée"})
    assert r.status_code == 200 and r.json()["paid_at"] and r.json()["requested_at"]
    assert client.put(f"/api/invoices/{inv['id']}", json={"status": "Inconnu"}).status_code == 422
    assert client.delete(f"/api/invoices/{inv['id']}").status_code == 204


def test_tarifs_figes_au_depot(client):
    c, _, _ = setup(client)
    with as_consultant() as me:
        inv = deposit(me, days=10).json()
    client.put(f"/api/consultants/{c['id']}", json={"name": "Ahmed", "tjm": 700, "billing_tjm": 900,
                                                    "mission_id": c["mission"]["id"]})
    row = client.get("/api/invoices/").json()[0]
    assert (row["id"], row["consultant_tjm"], row["billing_tjm"], row["margin"]) == (inv["id"], 650, 800, 1500)


def test_demande_de_paiement_impossible_sans_client(client):
    c = make_consultant(client, tjm=650, billing_tjm=800)
    make_account(client, c["id"])
    with as_consultant() as me:
        inv = deposit(me).json()
        assert me.delete(f"/api/invoices/{inv['id']}").status_code == 204
        inv = deposit(me).json()
    assert client.put(f"/api/invoices/{inv['id']}", json={"status": "Paiement demandé"}).status_code == 422


def test_consultant_ne_voit_que_ses_factures(client):
    setup(client)
    other = make_consultant(client, name="Marc", email="marc@example.com")
    make_account(client, other["id"], email="marc@example.com")
    with as_consultant("marc@example.com") as marc:
        mine = deposit(marc).json()
    with as_consultant() as me:
        assert me.get("/api/invoices/").json() == []
        assert me.get(f"/api/invoices/{mine['id']}/file").status_code == 404
        assert me.delete(f"/api/invoices/{mine['id']}").status_code == 404
