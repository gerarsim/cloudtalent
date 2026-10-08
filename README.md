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
| **Administrateur** | Accès complet : consultants, entreprises, missions, formations, matching, gestion des comptes (onglet « Utilisateurs »). |
| **Consultant** | Voit **uniquement son profil** (« Mon profil ») : sa mission en cours, son TJM, le calcul de son salaire mensuel, son CV et ses compétences. Il choisit son **pourcentage de réserve** et ses jours facturés, envoie son CV (PDF/DOC/DOCX/ODT, 5 Mo), et modifie profil, compétences, disponibilité et mot de passe. Nom, email, TJM, statut et mission sont gérés par l'admin. Tout le reste renvoie 403. |
| **Entreprise partenaire** | Gère **sa fiche entreprise** (coordonnées, TVA, site, présentation) et **publie ses missions** (postes à pourvoir : descriptif, compétences, TJM max, dates, statut). Ne voit que ses propres missions, ni les consultants ni le matching. |

- Le compte admin est créé au démarrage depuis `ADMIN_EMAIL` / `ADMIN_PASSWORD` s'il n'existe aucun admin
  (en dev : `admin@cloudtalent.lu` / `admin1234`, voir `docker-compose.yml`).
- Données de démo : compte consultant `ahmed.benali@example.com` / `consultant123`,
  compte entreprise `rh@demobank.example.com` / `entreprise123` (Demo Bank Luxembourg).
- Un compte entreprise est créé par l'admin (onglet « Utilisateurs », rôle « Entreprise partenaire ») et rattaché à une
  entreprise ; supprimer l'entreprise supprime ses comptes, ses missions sont conservées.
- Un compte consultant est rattaché à une fiche consultant ; supprimer la fiche supprime le compte.
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
