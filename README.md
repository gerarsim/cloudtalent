# CloudTalent MVP — Docker Windows

## Prérequis
- Windows 10/11
- Docker Desktop avec WSL2
- Git recommandé

## Démarrage

Dans PowerShell :

```powershell
cd cloudtalent-mvp
docker compose up --build
```

Puis ouvrir :
- Application : http://localhost:3000
- API Swagger : http://localhost:8000/docs
- Health : http://localhost:8000/api/health

> **Mise à jour depuis la v0.1** : le schéma de base a changé (table de compétences)
> et il est désormais géré par Alembic. Supprimez une fois l'ancienne base :
> `docker compose down -v`, puis `docker compose up --build`.

## Comptes et rôles

L'accueil propose trois espaces sous forme d'icônes (Administrateur, Consultant, Entreprise partenaire) ; on choisit son espace puis on se connecte. Un compte ne peut entrer que dans l'espace de son rôle. Trois rôles :

| Rôle | Droits |
|------|--------|
| **Administrateur** | Accès complet : consultants, entreprises, missions, formations, matching, gestion des comptes (onglet « Utilisateurs »). Fixe pour chaque consultant son **TJM consultant** et son **TJM facturé au client** (vide = TJM max de la mission) et voit sa **marge par jour, semaine (5 j) et mois** (dashboard « Ma marge », liste et fiche consultant). Onglet « Factures » : télécharge les factures signées, **demande le paiement** à l'entreprise cliente puis les marque payées. |
| **Consultant** | Voit **uniquement son profil** (« Mon profil ») : sa mission en cours, son TJM, le calcul de son salaire mensuel, son CV et ses compétences. Reçoit automatiquement ses **offres** : les missions ouvertes pour lesquelles il est éligible au matching, avec le **TJM proposé par CloudTalent** et son salaire estimé. Il choisit son **pourcentage de réserve** et ses jours facturés, envoie son CV (PDF/DOC/DOCX/ODT, 5 Mo), **dépose chaque mois sa facture signée** par lui et son client (PDF/JPG/PNG, 10 Mo, remplaçable tant que le paiement n'est pas demandé), et modifie profil, compétences, disponibilité et mot de passe. Nom, email, TJM, statut et mission sont gérés par l'admin. Tout le reste renvoie 403. |
| **Entreprise partenaire** | Gère **sa fiche entreprise** (coordonnées, TVA, site, présentation) et **publie ses missions** (postes à pourvoir : descriptif, compétences, TJM max, dates, statut). Voit le **profil et le CV des consultants que CloudTalent lui propose** pour ses missions (sans email, TJM, réserve ni salaire) et les retient ou refuse. Voit les **factures dont CloudTalent lui demande le paiement** (TJM client et montant uniquement). Consulte le **catalogue de formations** et y **inscrit ses collaborateurs** ; CloudTalent confirme. Ne voit ni les autres consultants ni le matching. |

- Le compte admin est créé au démarrage depuis `ADMIN_EMAIL` / `ADMIN_PASSWORD` s'il n'existe aucun admin
  (en dev : `admin@cloudtalent.lu` / `admin1234`, voir `docker-compose.yml`).
- Données de démo : compte consultant `ahmed.benali@example.com` / `consultant123`,
  compte entreprise `rh@demobank.example.com` / `entreprise123` (Demo Bank Luxembourg).
- Un compte entreprise est créé par l'admin (onglet « Utilisateurs », rôle « Entreprise partenaire ») et rattaché à une
  entreprise ; supprimer l'entreprise supprime ses comptes, ses missions sont conservées.
- Un compte consultant est rattaché à une fiche consultant ; supprimer la fiche supprime le compte.
- TJM proposé au consultant : fixé par l'admin sur la mission, sinon TJM max − `CONSULTANT_MARGIN_PCT` (15 % par défaut).
  Jamais visible par l'entreprise. Le consultant ne voit ni le nom de l'entreprise ni son TJM max, seulement son secteur.
- Salaire mensuel affiché = TJM × jours facturés − réserve (% du chiffre d'affaires), **avant charges sociales**.
- `SECRET_KEY` signe les jetons de session (12 h, `TOKEN_TTL_SECONDS`). **À changer hors poste local.**

## Arrêt

```powershell
docker compose down        # garde les données
docker compose down -v     # supprime aussi la base PostgreSQL
```

## Tests

```powershell
docker compose run --rm backend pytest -v
```

Les tests tournent sur une base SQLite temporaire, jamais sur la base de dev. Ils
passent par la vraie migration Alembic, donc une migration qui diverge des modèles
fait échouer la suite. Pour tester sur Postgres, définir `TEST_DATABASE_URL` vers une
base **dédiée** (les tests vident les tables).

## Migrations (Alembic)

Le backend applique `alembic upgrade head` à chaque démarrage (voir la commande du `backend/Dockerfile`).
Après une modification de `app/models.py` :

```powershell
docker compose run --rm backend alembic revision --autogenerate -m "description"
# relire le fichier généré dans backend/migrations/versions/, puis :
docker compose restart backend
```

## Matching

`GET /api/missions/{id}/matches?min_score=0&only_eligible=false` renvoie toujours une
liste de `{consultant, score, skill_score, eligible, tjm_ok, available, matched, missing}`.

- Les compétences sont un référentiel (`skills`) relié aux consultants (avec un
  **niveau 1-5**) et aux missions (**obligatoire/souhaitée** + **niveau minimum**).
- Les noms sont normalisés (casse, espaces) et les synonymes courants unifiés
  (`k8s` → Kubernetes, `tf` → Terraform, `gitlab ci` → GitLab CI/CD…), voir `app/skills.py`.
- Score = **70 % compétences** (obligatoire ×3, souhaitée ×1, au prorata du niveau)
  \+ **15 % TJM** (pénalité linéaire jusqu'à +20 % au-dessus du max)
  \+ **15 % disponibilité** (pénalité linéaire jusqu'à 60 jours de retard).
- **Éligible** = possède toutes les compétences obligatoires. Les éligibles sont classés en premier.

## Factures et marge

- Le TJM client et le TJM consultant sont **figés au dépôt** de la facture : modifier les tarifs
  ensuite ne change pas les factures déjà déposées.
- Montant client = jours × TJM client ; dû au consultant = jours × TJM consultant ; marge = la différence.
- Le consultant ne voit jamais le TJM client ni la marge ; l'entreprise ne voit jamais le TJM consultant ni la marge.
- « Demander le paiement » rend la facture visible dans l'espace de l'entreprise (aucun email n'est envoyé).

## Fiches de paie (Luxembourg)

L'admin établit chaque mois la fiche de paie d'un consultant (bouton « Fiches de paie » dans la liste) :
brut proposé = salaire mensuel du consultant, classe d'impôt 1 ou 2, fiche officielle de la fiduciaire
en pièce jointe facultative. Le consultant voit son **net estimé** dans « Mon salaire » et télécharge
ses fiches (PDF généré + fiche officielle) dans « Mes fiches de paie ».

Le calcul (`app/payroll.py`) est une **simulation indicative** : pension 8,5 %, maladie 3,05 %
(plafonnées à 5 × SSM), dépendance 1,4 %, barème d'impôt 2025 avec splitting en classe 2, fonds
pour l'emploi, crédit d'impôt salarié simplifié, et charges patronales pour information. Le SSM se
règle avec `LU_SSM_MONTHLY`. À faire valider par la fiduciaire avant tout usage réel.

## Ce MVP contient

- Consultants, entreprises, missions, formations : CRUD complet avec validation
- Référentiel de compétences + matching pondéré, visible dans l'interface (bouton « Matching »)
- PostgreSQL + migrations Alembic
- API FastAPI (schémas de réponse typés dans Swagger)
- Frontend React/Vite (formulaires, gestion des erreurs, proxy API)
- Docker Compose avec healthchecks
- Données de démonstration (désactivables avec `SEED_DEMO=false`)

## Important

C'est un prototype local, pas encore une plateforme de production. Il manque notamment :
sécurité de production (HTTPS, limitation des tentatives de connexion, réinitialisation de mot de passe), RGPD, contrats, paiement, facturation,
gestion du portage salarial, stockage de CV et workflow commercial.
