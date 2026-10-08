from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, computed_field

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=150)]
Level = Annotated[int, Field(ge=1, le=5, description="1 = notions, 3 = autonome, 5 = expert")]
Money = Annotated[float, Field(ge=0, le=10_000)]
Percent = Annotated[float, Field(ge=0, le=100, description="Pourcentage 0-100")]

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

DaysPerMonth = Annotated[int, Field(ge=0, le=31, description="Jours facturés par mois")]


class ConsultantSelfIn(BaseModel):
    """Ce qu'un consultant peut modifier sur sa propre fiche. Nom, email, TJM, statut et
    mission sont gérés par un admin."""
    title: Name
    experience_years: Annotated[int, Field(ge=0, le=60)] = 0
    reserve_pct: Percent = 0
    days_per_month: DaysPerMonth = 20
    available_from: date | None = None
    skills: list[SkillLevelIn] = []


class ConsultantIn(ConsultantSelfIn):
    name: Name
    email: EmailStr | None = None
    tjm: Money = 0
    status: ConsultantStatus = "Freelance"
    mission_id: int | None = None


class CvOut(ORM):
    filename: str
    content_type: str
    size: int
    uploaded_at: datetime


class ConsultantMissionOut(ORM):
    id: int
    title: str
    company: "CompanyRef | None"
    location: str
    start_date: date | None
    duration_months: int | None
    status: str


class SalaryOut(BaseModel):
    """Estimation mensuelle : chiffre d'affaires, réserve, salaire (avant charges sociales)."""
    days_per_month: int
    revenue: float = Field(description="TJM × jours facturés")
    reserve: float = Field(description="Chiffre d'affaires × réserve %")
    salary: float = Field(description="Chiffre d'affaires − réserve, avant charges sociales")


class ConsultantOut(ORM):
    id: int
    name: str
    title: str
    email: str | None
    experience_years: int
    tjm: float
    reserve_pct: float
    days_per_month: int
    available_from: date | None
    status: str
    skills: list[ConsultantSkillOut]
    mission: ConsultantMissionOut | None
    cv: CvOut | None

    @computed_field(description="Montant mis en réserve par jour (TJM × réserve %)")
    @property
    def reserve_amount(self) -> float:
        return round(self.tjm * self.reserve_pct / 100, 2)

    @computed_field(description="TJM restant après réserve")
    @property
    def tjm_net(self) -> float:
        return round(self.tjm - self.reserve_amount, 2)

    @computed_field(description="Calcul du salaire mensuel")
    @property
    def monthly(self) -> SalaryOut:
        revenue = round(self.tjm * self.days_per_month, 2)
        reserve = round(revenue * self.reserve_pct / 100, 2)
        return SalaryOut(days_per_month=self.days_per_month, revenue=revenue, reserve=reserve,
                         salary=round(revenue - reserve, 2))


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


ConsultantMissionOut.model_rebuild()  # CompanyRef est déclaré après


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


# --- Comptes & authentification -------------------------------------------

Role = Literal["admin", "consultant"]
Password = Annotated[str, StringConstraints(min_length=8, max_length=128)]


class LoginIn(BaseModel):
    email: EmailStr
    password: Annotated[str, StringConstraints(max_length=128)]


class UserOut(ORM):
    id: int
    email: str
    role: str
    consultant_id: int | None
    active: bool


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserIn(BaseModel):
    """Création d'un compte par un admin. `consultant_id` obligatoire pour le rôle consultant."""
    email: EmailStr
    password: Password
    role: Role
    consultant_id: int | None = None
    active: bool = True


class UserUpdate(BaseModel):
    """Modification par un admin. Mot de passe inchangé si absent."""
    email: EmailStr
    password: Password | None = None
    role: Role
    consultant_id: int | None = None
    active: bool = True


class PasswordChange(BaseModel):
    current_password: Annotated[str, StringConstraints(max_length=128)]
    new_password: Password
