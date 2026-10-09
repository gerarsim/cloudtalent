from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, computed_field

from . import payroll

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


TaxClass = Literal["1", "2"]  # classe d'impôt luxembourgeoise


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
    billing_tjm: Money | None = Field(None, description="TJM facturé au client ; vide = TJM max de la mission")
    tax_class: TaxClass = "1"


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


class PayrollLine(BaseModel):
    label: str
    base: float
    rate: float
    amount: float


class PayrollOut(BaseModel):
    """Simulation brut → net luxembourgeoise (voir app/payroll.py)."""
    gross: float
    tax_class: str
    lines: list[PayrollLine] = Field(description="Cotisations sociales salariales")
    social: float
    taxable_month: float
    tax: float = Field(description="Impôt sur le revenu + fonds pour l'emploi")
    tax_credit: float = Field(description="Crédit d'impôt salarié")
    net: float
    employer_lines: list[PayrollLine]
    employer_total: float
    employer_cost: float


def monthly_salary(tjm: float, reserve_pct: float, days: int) -> SalaryOut:
    """TJM × jours − réserve (% du chiffre d'affaires), avant charges sociales."""
    revenue = round(tjm * days, 2)
    reserve = round(revenue * reserve_pct / 100, 2)
    return SalaryOut(days_per_month=days, revenue=revenue, reserve=reserve, salary=round(revenue - reserve, 2))


class ConsultantOut(ORM):
    id: int
    name: str
    title: str
    email: str | None
    experience_years: int
    tjm: float
    reserve_pct: float
    days_per_month: int
    tax_class: str
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
        return monthly_salary(self.tjm, self.reserve_pct, self.days_per_month)

    @computed_field(description="Simulation brut → net au Luxembourg, le salaire mensuel pris comme brut")
    @property
    def payroll(self) -> PayrollOut:
        return PayrollOut(**payroll.compute(self.monthly.salary, self.tax_class))


class MarginOut(BaseModel):
    """Ce que CloudTalent gagne sur ce consultant : TJM client − TJM consultant."""
    per_day: float
    per_week: float = Field(description="5 jours")
    per_month: float = Field(description="Jours facturés par mois du consultant")


class ConsultantAdminOut(ConsultantOut):
    """Vue admin : ajoute le TJM facturé au client et la marge (jamais montrés au consultant)."""
    billing_tjm: float | None
    effective_billing_tjm: float | None

    @computed_field(description="Marge CloudTalent (null sans TJM client)")
    @property
    def margin(self) -> MarginOut | None:
        if self.effective_billing_tjm is None:
            return None
        day = round(self.effective_billing_tjm - self.tjm, 2)
        return MarginOut(per_day=day, per_week=round(day * 5, 2), per_month=round(day * self.days_per_month, 2))


# --- Entreprises -----------------------------------------------------------

LongText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)]


class CompanyIn(BaseModel):
    name: Name
    sector: ShortText = ""
    city: ShortText = "Luxembourg"
    contact_name: ShortText = ""
    email: EmailStr | None = None
    phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=50)] = ""
    # http(s) uniquement : le lien est cliquable dans l'interface (pas de javascript:)
    website: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200,
                                              pattern=r"^(https?://\S+)?$")] = ""
    address: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] = ""
    vat_number: Annotated[str, StringConstraints(strip_whitespace=True, max_length=50)] = ""
    description: LongText = ""


class CompanyOut(ORM):
    id: int
    name: str
    sector: str
    city: str
    contact_name: str
    email: str | None
    phone: str
    website: str
    address: str
    vat_number: str
    description: str


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
    description: LongText = ""
    consultant_tjm: Money | None = Field(None, description="TJM proposé au consultant (admin) ; vide = TJM max − marge")
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
    description: str
    # Réservés à l'admin : toujours null dans les réponses faites à une entreprise
    consultant_tjm: float | None = None
    offered_tjm: float | None = Field(None, description="TJM proposé au consultant (fixé ou calculé)")
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


class TrainingRef(ORM):
    id: int
    title: str


# --- Propositions de consultants aux entreprises ----------------------------

ProposalStatus = Literal["Proposé", "Retenu", "Refusé"]


class ConsultantPublicOut(ORM):
    """Profil montré à une entreprise : ni email, ni TJM, ni réserve, ni salaire, ni mission en cours."""
    id: int
    name: str
    title: str
    experience_years: int
    available_from: date | None
    status: str
    skills: list[ConsultantSkillOut]
    cv: CvOut | None


class MissionRef(ORM):
    id: int
    title: str


class ProposalIn(BaseModel):
    mission_id: int
    consultant_id: int


class ProposalStatusIn(BaseModel):
    status: ProposalStatus


class ProposalOut(ORM):
    id: int
    status: str
    created_at: datetime
    mission: MissionRef
    consultant: ConsultantPublicOut


# --- Inscriptions aux formations -------------------------------------------

EnrollmentStatus = Literal["Demandée", "Confirmée", "Annulée"]


class EnrollmentIn(BaseModel):
    training_id: int
    participant_name: Name
    participant_email: EmailStr


class EnrollmentStatusIn(BaseModel):
    status: EnrollmentStatus


class EnrollmentOut(ORM):
    id: int
    training: TrainingRef
    company: CompanyRef
    participant_name: str
    participant_email: str
    status: str
    created_at: datetime


# --- Offres pour le consultant ----------------------------------------------

class OfferMissionOut(ORM):
    """Mission vue par un consultant : sans le nom de l'entreprise ni son TJM max."""
    id: int
    title: str
    location: str
    start_date: date | None
    duration_months: int | None
    description: str
    skills: list[MissionSkillOut]


class OfferOut(BaseModel):
    mission: OfferMissionOut
    sector: str = Field(description="Secteur de l'entreprise cliente")
    tjm: float | None = Field(description="TJM proposé par CloudTalent")
    monthly: SalaryOut | None = Field(description="Salaire mensuel estimé avec ce TJM, sa réserve et ses jours")
    score: int
    skill_score: int
    available: bool
    matched: list["SkillMatch"]
    missing: list["SkillMatch"]
    proposal_status: str | None = Field(description="Statut si CloudTalent l'a déjà proposé à l'entreprise")


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

Role = Literal["admin", "consultant", "company"]
Password = Annotated[str, StringConstraints(min_length=8, max_length=128)]


class LoginIn(BaseModel):
    email: EmailStr
    password: Annotated[str, StringConstraints(max_length=128)]


class UserOut(ORM):
    id: int
    email: str
    role: str
    consultant_id: int | None
    company_id: int | None
    active: bool


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserIn(BaseModel):
    """Création d'un compte par un admin. `consultant_id` obligatoire pour le rôle consultant,
    `company_id` pour le rôle company (entreprise partenaire)."""
    email: EmailStr
    password: Password
    role: Role
    consultant_id: int | None = None
    company_id: int | None = None
    active: bool = True


class UserUpdate(BaseModel):
    """Modification par un admin. Mot de passe inchangé si absent."""
    email: EmailStr
    password: Password | None = None
    role: Role
    consultant_id: int | None = None
    company_id: int | None = None
    active: bool = True


class PasswordChange(BaseModel):
    current_password: Annotated[str, StringConstraints(max_length=128)]
    new_password: Password


OfferOut.model_rebuild()  # SkillMatch est déclaré après


# --- Factures ----------------------------------------------------------------

InvoiceStatus = Literal["Déposée", "Paiement demandé", "Payée"]
Period = Annotated[str, StringConstraints(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]


class ConsultantRef(ORM):
    id: int
    name: str


class InvoiceMissionRef(ORM):
    id: int
    title: str
    company: CompanyRef | None


class InvoiceStatusIn(BaseModel):
    status: InvoiceStatus


class InvoiceOut(ORM):
    """Champs financiers selon le rôle : le consultant voit son montant, l'entreprise le montant
    facturé, l'admin tout (marge comprise). Les autres sont null."""
    id: int
    consultant: ConsultantRef
    mission: InvoiceMissionRef | None
    period: str
    days: float
    status: str
    filename: str
    size: int
    uploaded_at: datetime
    requested_at: datetime | None
    paid_at: datetime | None
    consultant_tjm: float | None
    consultant_amount: float | None
    billing_tjm: float | None
    amount: float | None
    margin: float | None


# --- Fiches de paie ----------------------------------------------------------

class PayslipOut(ORM):
    id: int
    consultant: ConsultantRef
    period: str
    tax_class: str
    gross: float
    net: float
    details: PayrollOut
    filename: str | None
    size: int | None
    created_at: datetime
