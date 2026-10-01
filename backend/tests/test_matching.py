"""Tests unitaires du moteur de matching (sans base de données)."""
from datetime import date
from types import SimpleNamespace as NS

from app.matching import rank, score_consultant

TODAY = date(2026, 10, 1)
SKILLS = {n: NS(id=i, name=n) for i, n in enumerate(["AWS", "EKS", "Kubernetes", "Terraform", "ArgoCD", "Azure"], 1)}


def mission(spec, tjm_max=800, start=TODAY):
    return NS(
        tjm_max=tjm_max, start_date=start,
        skills=[NS(skill_id=SKILLS[n].id, skill=SKILLS[n], required=r, min_level=l) for n, (r, l) in spec.items()],
    )


def consultant(spec, tjm=700, available_from=None, name="X"):
    return NS(name=name, tjm=tjm, available_from=available_from,
              skills=[NS(skill_id=SKILLS[n].id, level=l) for n, l in spec.items()])


M = mission({"AWS": (True, 4), "Kubernetes": (True, 4), "Terraform": (True, 3), "ArgoCD": (False, 3)})


def test_parfait_100():
    m = score_consultant(M, consultant({"AWS": 5, "Kubernetes": 4, "Terraform": 3, "ArgoCD": 3}), TODAY)
    assert m.score == 100 and m.eligible and m.tjm_ok and m.available and not m.missing


def test_pas_de_faux_positif_par_sous_chaine():
    # L'ancien matching trouvait "eks" dans n'importe quelle chaîne le contenant.
    mm = mission({"EKS": (True, 3)})
    assert score_consultant(mm, consultant({"Kubernetes": 5}), TODAY) is None


def test_competence_obligatoire_manquante_non_eligible():
    m = score_consultant(M, consultant({"AWS": 5, "Kubernetes": 5, "ArgoCD": 5}), TODAY)
    assert not m.eligible
    assert [x["name"] for x in m.missing] == ["Terraform"]
    # 3 obligatoires (poids 3) + 1 souhaitée (poids 1) = 10 ; Terraform manque -> 7/10
    assert m.skill_score == 70


def test_niveau_insuffisant_au_prorata():
    m = score_consultant(mission({"AWS": (True, 4)}), consultant({"AWS": 2}), TODAY)
    assert m.skill_score == 50 and m.eligible


def test_souhaitee_pese_moins_que_obligatoire():
    sans_opt = score_consultant(M, consultant({"AWS": 4, "Kubernetes": 4, "Terraform": 3}), TODAY)
    sans_obl = score_consultant(M, consultant({"AWS": 4, "Kubernetes": 4, "ArgoCD": 3}), TODAY)
    assert sans_opt.skill_score == 90 and sans_obl.skill_score == 70


def test_tjm_au_dessus_du_max_penalise():
    ok = score_consultant(M, consultant({"AWS": 4}, tjm=800), TODAY)
    plus10 = score_consultant(M, consultant({"AWS": 4}, tjm=880), TODAY)
    plus30 = score_consultant(M, consultant({"AWS": 4}, tjm=1040), TODAY)
    assert ok.tjm_ok and not plus10.tjm_ok
    assert ok.score - plus10.score == 8      # 15 % * 50 %
    assert ok.score - plus30.score == 15     # au-delà de +20 % : 0


def test_tjm_max_zero_ignore():
    m = score_consultant(mission({"AWS": (True, 3)}, tjm_max=0), consultant({"AWS": 3}, tjm=5000), TODAY)
    assert m.tjm_ok and m.score == 100


def test_disponibilite():
    full = {"AWS": 4, "Kubernetes": 4, "Terraform": 3, "ArgoCD": 3}
    late30 = score_consultant(M, consultant(full, available_from=date(2026, 10, 31)), TODAY)
    late90 = score_consultant(M, consultant(full, available_from=date(2026, 12, 30)), TODAY)
    before = score_consultant(M, consultant(full, available_from=date(2026, 9, 1)), TODAY)
    assert before.available and not late30.available
    assert before.score == 100
    assert late30.score == 93   # 100 - 15 % * 50 % = 92.5 -> 93
    assert late90.score == 85   # au-delà de 60 jours : 0 sur ce critère


def test_mission_sans_competences():
    assert score_consultant(mission({}), consultant({"AWS": 5}), TODAY) is None


def test_classement_eligibles_dabord():
    a = consultant({"AWS": 5, "Kubernetes": 5, "Terraform": 5}, tjm=900, name="eligible_cher")
    b = consultant({"AWS": 5, "Kubernetes": 5, "ArgoCD": 5}, tjm=500, name="non_eligible")
    c = consultant({"Azure": 5}, name="hors_sujet")
    ranked = rank(M, [b, c, a], TODAY)
    assert [m.consultant.name for m in ranked] == ["eligible_cher", "non_eligible"]
