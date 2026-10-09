"""Simulation brut → net d'un salarié au Luxembourg (exemple indicatif, pas un logiciel de paie).

Hypothèses (à faire valider par la fiduciaire, les montants changent avec l'index) :
- Cotisations salariales : pension 8,5 % (réforme 2026), maladie 3,05 % (soins 2,80 % + espèces
  0,25 %), plafonnées à 5 × le salaire social minimum (SSM) ; assurance dépendance 1,4 % sur le
  brut diminué d'un quart du SSM, sans plafond.
- Impôt : barème 2025, classes 1 et 2 (splitting), après frais d'obtention (540 €/an) et
  dépenses spéciales (480 €/an) forfaitaires, revenu arrondi à 50 € ; contribution au fonds
  pour l'emploi 7 % (9 % au-delà de 150 000 € / 300 000 €) ; crédit d'impôt salarié (CIS) simplifié.
- Charges patronales (information) : pension 8,5 %, maladie 3,05 %, accident 0,75 %,
  mutualité 0,72 %, santé au travail 0,14 %, sur le brut plafonné.
"""
import os

SSM = float(os.getenv("LU_SSM_MONTHLY", "2703.74"))  # salaire social minimum non qualifié, mensuel
CAP = 5 * SSM

EMPLOYEE = [("Assurance pension", 8.5, True), ("Assurance maladie", 3.05, True)]
DEPENDANCE_PCT = 1.4
EMPLOYER = [("Assurance pension", 8.5), ("Assurance maladie", 3.05), ("Assurance accident", 0.75),
            ("Mutualité des employeurs", 0.72), ("Santé au travail", 0.14)]

FRAIS_OBTENTION = 540
DEPENSES_SPECIALES = 480
# (plafond de tranche annuel, taux %) ; la dernière tranche n'a pas de plafond
BAREME = [(13230, 0), (15435, 8), (17640, 9), (19845, 10), (22050, 11), (24255, 12), (26550, 14),
          (28845, 16), (31140, 18), (33435, 20), (35730, 22), (38025, 24), (40320, 26), (42615, 28),
          (44910, 30), (47205, 32), (49500, 34), (51795, 36), (54090, 38), (117450, 39), (176160, 40),
          (234870, 41), (float("inf"), 42)]
TAX_CLASSES = ("1", "2")


def _r(x: float) -> float:
    return round(x + 1e-9, 2)


def _tariff(income: float) -> float:
    tax, low = 0.0, 0.0
    for high, rate in BAREME:
        if income <= low:
            break
        tax += (min(income, high) - low) * rate / 100
        low = high
    return tax


def annual_tax(taxable: float, tax_class: str) -> float:
    """Impôt annuel + contribution au fonds pour l'emploi."""
    if tax_class == "2":
        tax, threshold = 2 * _tariff(taxable / 2), 300_000
    else:
        tax, threshold = _tariff(taxable), 150_000
    return tax * (1.09 if taxable > threshold else 1.07)


def tax_credit(annual_gross: float) -> float:
    """Crédit d'impôt salarié (CIS), annuel, barème simplifié."""
    if annual_gross < 936:
        return 0.0
    if annual_gross < 11265:
        return 300 + (annual_gross - 936) * 0.029
    if annual_gross <= 40000:
        return 600.0
    return max(0.0, 600 - (annual_gross - 40000) * 0.015)


def compute(gross: float, tax_class: str = "1") -> dict:
    """Fiche de paie mensuelle simulée : lignes salariales, impôt, net, coût employeur."""
    gross = max(0.0, float(gross))
    base = min(gross, CAP)
    lines = [{"label": label, "base": _r(base), "rate": rate, "amount": _r(base * rate / 100)}
             for label, rate, _ in EMPLOYEE]
    dep_base = max(0.0, gross - SSM / 4)
    lines.append({"label": "Assurance dépendance", "base": _r(dep_base), "rate": DEPENDANCE_PCT,
                  "amount": _r(dep_base * DEPENDANCE_PCT / 100)})
    social = _r(sum(x["amount"] for x in lines))

    deductible = sum(x["amount"] for x in lines[:2])  # pension + maladie (pas la dépendance)
    taxable_year = max(0.0, (gross - deductible) * 12 - FRAIS_OBTENTION - DEPENSES_SPECIALES)
    taxable_year = taxable_year // 50 * 50
    tax = _r(annual_tax(taxable_year, tax_class) / 12)
    cis = _r(tax_credit(gross * 12) / 12 if gross > 0 else 0)
    net = _r(gross - social - tax + cis)

    employer = [{"label": label, "base": _r(base), "rate": rate, "amount": _r(base * rate / 100)}
                for label, rate in EMPLOYER]
    employer_total = _r(sum(x["amount"] for x in employer))
    return {
        "gross": _r(gross), "tax_class": tax_class, "lines": lines, "social": social,
        "taxable_month": _r(taxable_year / 12), "tax": tax, "tax_credit": cis, "net": net,
        "employer_lines": employer, "employer_total": employer_total, "employer_cost": _r(gross + employer_total),
    }
