import pytest

from app import payroll
from tests.test_api import make_consultant
from tests.test_auth import as_consultant, make_account
from tests.test_company import as_company, make_company, make_company_account


def test_calcul_brut_net_luxembourg():
    r = payroll.compute(5000, "1")
    # pension 8,5 % + maladie 3,05 % sur 5 000 €, dépendance 1,4 % sur 5 000 − SSM / 4
    assert [x["amount"] for x in r["lines"]] == pytest.approx([425.0, 152.5, (5000 - payroll.SSM / 4) * 0.014], abs=0.01)
    assert r["net"] == pytest.approx(r["gross"] - r["social"] - r["tax"] + r["tax_credit"], abs=0.01)
    assert 3500 < r["net"] < 3800
    assert r["employer_cost"] > r["gross"]

    # Classe 2 (splitting) : moins d'impôt pour le même brut
    assert payroll.compute(8000, "2")["tax"] < payroll.compute(8000, "1")["tax"]
    # Cotisations plafonnées à 5 × SSM, pas la dépendance
    high = payroll.compute(30000, "1")
    assert high["lines"][0]["base"] == round(5 * payroll.SSM, 2)
    assert high["lines"][2]["base"] == pytest.approx(30000 - payroll.SSM / 4, abs=0.01)
    assert payroll.compute(0)["net"] == 0


def test_barème_progressif():
    assert payroll._tariff(13230) == 0
    assert payroll._tariff(15435) == pytest.approx(2205 * 0.08)
    assert payroll.annual_tax(200_000, "1") == pytest.approx(payroll._tariff(200_000) * 1.09)


def test_admin_etablit_la_fiche_et_le_consultant_la_telecharge(client):
    c = make_consultant(client, tjm=650, reserve_pct=10, days_per_month=20, tax_class="2")
    assert c["tax_class"] == "2"
    assert c["payroll"]["gross"] == c["monthly"]["salary"] == 11700
    make_account(client, c["id"])

    sim = client.get("/api/payslips/simulate", params={"gross": 5000}).json()
    assert sim["net"] == payroll.compute(5000, "1")["net"]

    # Brut par défaut = salaire mensuel, classe par défaut = celle du consultant
    r = client.post("/api/payslips/", data={"consultant_id": c["id"], "period": "2026-09"})
    assert r.status_code == 201, r.text
    slip = r.json()
    assert (slip["gross"], slip["tax_class"], slip["filename"]) == (11700, "2", None)
    assert slip["net"] == payroll.compute(11700, "2")["net"]

    # Recalcul du même mois avec un autre brut et la fiche officielle jointe
    r = client.post("/api/payslips/", data={"consultant_id": c["id"], "period": "2026-09", "gross": "9000", "tax_class": "1"},
                    files={"file": ("fiche-officielle.pdf", b"%PDF-1.4 officielle", "application/pdf")})
    assert r.status_code == 201 and r.json()["id"] == slip["id"]
    assert (r.json()["gross"], r.json()["filename"]) == (9000, "fiche-officielle.pdf")
    # Un nouveau calcul sans fichier garde la pièce jointe
    r = client.post("/api/payslips/", data={"consultant_id": c["id"], "period": "2026-09", "gross": "9100"})
    assert r.json()["filename"] == "fiche-officielle.pdf"

    assert client.post("/api/payslips/", data={"consultant_id": c["id"], "period": "2026-10"},
                       files={"file": ("x.docx", b"PK", "application/octet-stream")}).status_code == 422
    assert client.post("/api/payslips/", data={"consultant_id": 999, "period": "2026-10"}).status_code == 404
    assert client.post("/api/payslips/", data={"consultant_id": c["id"], "period": "2026-13"}).status_code == 422

    with as_consultant() as me:
        rows = me.get("/api/payslips/").json()
        assert [x["period"] for x in rows] == ["2026-09"]
        pdf = me.get(f"/api/payslips/{slip['id']}/pdf")
        assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
        assert "fiche-de-paie-2026-09.pdf" in pdf.headers["content-disposition"]
        assert me.get(f"/api/payslips/{slip['id']}/file").content == b"%PDF-1.4 officielle"
        # Lecture seule pour le consultant
        assert me.post("/api/payslips/", data={"consultant_id": c["id"], "period": "2026-10"}).status_code == 403
        assert me.delete(f"/api/payslips/{slip['id']}").status_code == 403
        assert me.get("/api/payslips/simulate", params={"gross": 1000}).status_code == 403

    assert client.delete(f"/api/payslips/{slip['id']}").status_code == 204


def test_fiches_de_paie_privees(client):
    a = make_consultant(client)
    b = make_consultant(client, name="Marc", email="marc@example.com")
    make_account(client, a["id"])
    slip = client.post("/api/payslips/", data={"consultant_id": b["id"], "period": "2026-09"}).json()
    assert client.get(f"/api/payslips/{slip['id']}/file").status_code == 404  # pas de fiche officielle
    assert [x["id"] for x in client.get("/api/payslips/", params={"consultant_id": b["id"]}).json()] == [slip["id"]]

    with as_consultant() as me:
        assert me.get("/api/payslips/").json() == []
        assert me.get(f"/api/payslips/{slip['id']}/pdf").status_code == 404

    make_company_account(client, make_company(client)["id"])
    with as_company() as co:
        assert co.get("/api/payslips/").status_code == 403
        assert co.get(f"/api/payslips/{slip['id']}/pdf").status_code == 403
