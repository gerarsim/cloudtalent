"""Fiche de paie au format PDF, générée à partir du calcul figé (app/payroll.py)."""
from datetime import date
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre",
          "octobre", "novembre", "décembre"]


def euro(x: float) -> str:
    return f"{x:,.2f} €".replace(",", " ").replace(".", ",")


def pct(x: float) -> str:
    return f"{x:g} %".replace(".", ",")


def month_label(period: str) -> str:
    year, month = period.split("-")
    return f"{MONTHS[int(month) - 1]} {year}"


def render(consultant_name: str, consultant_title: str, period: str, d: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            title=f"Fiche de paie {month_label(period)} - {consultant_name}")
    st = getSampleStyleSheet()
    small = st["Normal"].clone("small", fontSize=8, textColor=colors.HexColor("#64748b"), leading=10)

    def table(rows, total_rows=()):
        t = Table(rows, colWidths=[78 * mm, 34 * mm, 20 * mm, 32 * mm])
        style = [
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]
        for i in total_rows:
            style.append(("FONTNAME", (0, i), (-1, i), "Helvetica-Bold"))
        t.setStyle(TableStyle(style))
        return t

    head = ["", "Base", "Taux", "Montant"]
    salary = [head, ["Salaire brut", "", "", euro(d["gross"])]]
    salary += [[f"{x['label']} (part salariale)", euro(x["base"]), pct(x["rate"]), "- " + euro(x["amount"])]
               for x in d["lines"]]
    salary += [
        ["Total cotisations sociales", "", "", "- " + euro(d["social"])],
        [f"Impôt sur le revenu, classe {d['tax_class']} (fonds pour l'emploi inclus)",
         euro(d["taxable_month"]), "", "- " + euro(d["tax"])],
        ["Crédit d'impôt salarié (CIS)", "", "", "+ " + euro(d["tax_credit"])],
        ["Net à payer", "", "", euro(d["net"])],
    ]
    employer = [head] + [[x["label"], euro(x["base"]), pct(x["rate"]), euro(x["amount"])] for x in d["employer_lines"]]
    employer += [["Total charges patronales", "", "", euro(d["employer_total"])],
                 ["Coût total employeur", "", "", euro(d["employer_cost"])]]

    story = [
        Paragraph("<b>CloudTalent</b> · Luxembourg", st["Normal"]),
        Spacer(1, 4 * mm),
        Paragraph(f"Fiche de paie · {month_label(period)}", st["Title"]),
        Paragraph(f"<b>{consultant_name}</b> · {consultant_title}", st["Normal"]),
        Spacer(1, 6 * mm),
        table(salary, total_rows=(1, len(salary) - 1)),
        Spacer(1, 8 * mm),
        Paragraph("Charges patronales (information)", st["Heading3"]),
        table(employer, total_rows=(len(employer) - 1,)),
        Spacer(1, 10 * mm),
        Paragraph(
            "Simulation indicative établie selon les taux luxembourgeois usuels (cotisations plafonnées à "
            "5 × le salaire social minimum, barème d'impôt 2025, crédit d'impôt simplifié). Elle ne remplace "
            f"pas la fiche de paie officielle de la fiduciaire. Document généré le {date.today():%d/%m/%Y}.",
            small,
        ),
    ]
    doc.build(story)
    return buf.getvalue()
