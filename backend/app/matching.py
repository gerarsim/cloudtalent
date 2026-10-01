"""Moteur de matching mission -> consultants.

Score global (0-100) = 70 % compétences + 15 % TJM + 15 % disponibilité.

Compétences : chaque compétence de la mission pèse 3 si obligatoire, 1 si souhaitée.
Un consultant qui la possède au niveau requis la couvre à 100 %, en dessous au
prorata (niveau 2 pour 4 requis = 50 %). Absente = 0.

TJM : 100 % si TJM <= TJM max (ou pas de max), puis décroît linéairement jusqu'à
0 % à +20 % au-dessus du max.

Disponibilité : 100 % si disponible au démarrage de la mission (ou aujourd'hui
si pas de date), puis décroît linéairement jusqu'à 0 % à 60 jours de retard.

Un consultant est « éligible » s'il possède toutes les compétences obligatoires
(quel que soit le niveau). Les consultants sans aucune compétence en commun
sont exclus.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pas de dépendance runtime : le moteur reste testable sans base
    from .models import Consultant, Mission

W_REQUIRED, W_OPTIONAL = 3, 1
W_SKILLS, W_TJM, W_AVAIL = 0.70, 0.15, 0.15
TJM_TOLERANCE = 0.20
AVAIL_TOLERANCE_DAYS = 60


def _pct(x: float) -> int:
    """0.925 -> 93 (arrondi classique, pas l'arrondi bancaire de round())."""
    return math.floor(100 * x + 0.5)


@dataclass
class Match:
    consultant: Consultant
    score: int
    skill_score: int
    tjm_ok: bool
    available: bool
    eligible: bool
    matched: list[dict]
    missing: list[dict]


def _tjm_factor(tjm: float, tjm_max: float) -> float:
    if not tjm_max or tjm <= tjm_max:
        return 1.0
    over = (tjm - tjm_max) / (tjm_max * TJM_TOLERANCE)
    return max(0.0, 1.0 - over)


def _availability_factor(available_from: date | None, start: date) -> float:
    if available_from is None or available_from <= start:
        return 1.0
    late = (available_from - start).days
    return max(0.0, 1.0 - late / AVAIL_TOLERANCE_DAYS)


def score_consultant(mission: Mission, consultant: Consultant, today: date | None = None) -> Match | None:
    if not mission.skills:
        return None

    levels = {cs.skill_id: cs.level for cs in consultant.skills}
    total_w = covered_w = 0.0
    matched, missing = [], []
    eligible = True

    for ms in mission.skills:
        w = W_REQUIRED if ms.required else W_OPTIONAL
        total_w += w
        level = levels.get(ms.skill_id)
        entry = {"name": ms.skill.name, "required": ms.required, "min_level": ms.min_level, "level": level}
        if level is None:
            missing.append(entry)
            if ms.required:
                eligible = False
        else:
            covered_w += w * min(1.0, level / ms.min_level)
            matched.append(entry)

    if not matched:
        return None

    skill_f = covered_w / total_w
    tjm_f = _tjm_factor(consultant.tjm, mission.tjm_max)
    start = mission.start_date or today or date.today()
    avail_f = _availability_factor(consultant.available_from, start)

    return Match(
        consultant=consultant,
        score=_pct(W_SKILLS * skill_f + W_TJM * tjm_f + W_AVAIL * avail_f),
        skill_score=_pct(skill_f),
        tjm_ok=tjm_f == 1.0,
        available=avail_f == 1.0,
        eligible=eligible,
        matched=matched,
        missing=missing,
    )


def rank(mission: Mission, consultants: list[Consultant], today: date | None = None) -> list[Match]:
    results = [m for c in consultants if (m := score_consultant(mission, c, today)) is not None]
    return sorted(results, key=lambda m: (m.eligible, m.score), reverse=True)
