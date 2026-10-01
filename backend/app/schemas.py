from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=150)]
Level = Annotated[int, Field(ge=1, le=5, description="1 = notions, 3 = autonome, 5 = expert")]
Money = Annotated[float, Field(ge=0, le=10_000)]

ConsultantStatus = Literal["Freelance", "Portage", "CDI", "Salarié"]
MissionStatus = Literal["Ouverte", "Pourvue", "Fermée"]
TrainingLevel = Literal["Débutant", "Intermédiaire", "Avancé"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Compétences -----------------------------------------------------------

class SkillOut(ORM):
    id: int
    name: str
    category: str


class SkillLevelIn(BaseModel):
    name: Name
    level: Level = 3


class MissionSkillIn(BaseModel):
    name: Name
    required: bool = True
    min_level: Level = 3


class ConsultantSkillOut(ORM):
    skill: SkillOut
    level: int


class MissionSkillOut(ORM):
    skill: SkillOut
    required: bool
    min_level: int


# --- Consultants -----------------------------------------------------------

class ConsultantIn(BaseModel):
    name: Name
    title: Name
    email: EmailStr | None = None
    experience_years: Annotated[int, Field(ge=0, le=60)] = 0
    tjm: Money = 0
    available_from: date | None = None
    status: ConsultantStatus = "Freelance"
    skills: list[SkillLevelIn] = []


class ConsultantOut(ORM):
    id: int
    name: str
    title: str
    email: str | None
    experience_years: int
    tjm: float
    available_from: date | None
    status: str
    skills: list[ConsultantSkillOut]


# --- Entreprises -----------------------------------------------------------

class CompanyIn(BaseModel):
    name: Name
    sector: ShortText = ""
    city: ShortText = "Luxembourg"
    contact_name: ShortText = ""
    email: EmailStr | None = None


class CompanyOut(ORM):
    id: int
    name: str
    sector: str
    city: str
    contact_name: str
    email: str | None


class CompanyRef(ORM):
    id: int
    name: str


# --- Missions --------------------------------------------------------------

class MissionIn(BaseModel):
    title: Name
    company_id: int | None = None
    location: ShortText = "Luxembourg"
    duration_months: Annotated[int, Field(gt=0, le=60)] | None = None
    start_date: date | None = None
    tjm_max: Money = 0
    status: MissionStatus = "Ouverte"
    skills: list[MissionSkillIn] = []


class MissionOut(ORM):
    id: int
    title: str
    company: CompanyRef | None
    location: str
    duration_months: int | None
    start_date: date | None
    tjm_max: float
    status: str
    skills: list[MissionSkillOut]


# --- Formations ------------------------------------------------------------

class TrainingIn(BaseModel):
    title: Name
    skill: Name | None = None
    level: TrainingLevel = "Débutant"
    duration_days: Annotated[int, Field(gt=0, le=60)] | None = None
    price: Annotated[float, Field(ge=0, le=100_000)] = 0
    online: bool = True


class TrainingOut(ORM):
    id: int
    title: str
    skill: SkillOut | None
    level: str
    duration_days: int | None
    price: float
    online: bool


# --- Matching --------------------------------------------------------------

class SkillMatch(BaseModel):
    name: str
    required: bool
    min_level: int
    level: int | None = Field(description="Niveau du consultant, None s'il ne l'a pas")


class MatchOut(BaseModel):
    consultant: ConsultantOut
    score: int = Field(description="Score global 0-100")
    skill_score: int
    tjm_ok: bool
    available: bool
    eligible: bool = Field(description="Possède toutes les compétences obligatoires")
    matched: list[SkillMatch]
    missing: list[SkillMatch]
