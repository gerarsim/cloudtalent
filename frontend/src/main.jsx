import React, { useCallback, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";
import { api, download, euro, frDate, hasToken, setToken, setUnauthorizedHandler, ROLES } from "./api.js";
import { Alert, Page, SkillChips, Table } from "./components/ui.jsx";
import { CompanyForm, ConsultantForm, MissionForm, TrainingForm, UserForm } from "./components/forms.jsx";
import Header from "./components/Header.jsx";
import Login from "./components/Login.jsx";
import Matches from "./components/Matches.jsx";
import MyAccount from "./components/MyAccount.jsx";
import CompanySpace from "./components/CompanySpace.jsx";

const TABS = [
  ["dashboard", "Dashboard"],
  ["consultants", "Consultants"],
  ["companies", "Entreprises"],
  ["missions", "Missions"],
  ["trainings", "Formations"],
  ["users", "Utilisateurs"],
];

/** Choix de l'espace selon le rôle : admin = tout, consultant = sa fiche, entreprise = sa fiche et ses missions. */
function Root() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(hasToken());
  useEffect(() => {
    setUnauthorizedHandler(() => setUser(null));
    if (!hasToken()) return;
    api("/auth/me").then(setUser).catch(() => setToken(null)).finally(() => setChecking(false));
  }, []);
  const logout = () => { setToken(null); setUser(null); };

  if (checking) return <div className="app"><Header /><main><p className="muted">Chargement…</p></main></div>;
  if (!user) return <Login onLogin={setUser} />;
  if (user.role === "admin") return <App user={user} onLogout={logout} />;
  if (user.role === "company") return <CompanySpace user={user} onLogout={logout} />;
  return <MyAccount user={user} onLogout={logout} />;
}

function App({ user, onLogout }) {
  const [tab, setTab] = useState("dashboard");
  const [data, setData] = useState({ consultants: [], companies: [], missions: [], trainings: [], skills: [], users: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  // modal = {kind: "consultant"|"company"|"mission"|"training"|"matches", item?}
  const [modal, setModal] = useState(null);

  const load = useCallback(async () => {
    try {
      const [consultants, companies, missions, trainings, skills, users] = await Promise.all(
        ["/consultants/", "/companies/", "/missions/", "/trainings/", "/skills/", "/users/"].map((p) => api(p))
      );
      setData({ consultants, companies, missions, trainings, skills, users });
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  const close = useCallback(() => setModal(null), []);
  const saved = () => { setModal(null); load(); };
  const remove = async (path, label) => {
    if (!window.confirm(`Supprimer « ${label} » ?`)) return;
    try {
      await api(path, { method: "DELETE" });
      load();
    } catch (e) {
      setError(e.message);
    }
  };
  const open = (kind, item) => () => setModal({ kind, item });
  const rowActions = (kind, path, label) => (r) => (
    <>
      <button className="link" onClick={open(kind, r)}>Modifier</button>
      <button className="link danger" onClick={() => remove(`${path}${r.id}`, r[label])}>Supprimer</button>
    </>
  );

  return (
    <div className="app">
      <Header user={user} onLogout={onLogout} />
      <nav>
        {TABS.map(([key, label]) => (
          <button key={key} className={tab === key ? "active" : ""} onClick={() => setTab(key)}>{label}</button>
        ))}
      </nav>
      <main>
        <Alert onClose={() => setError(null)}>{error}</Alert>
        {loading ? <p className="muted">Chargement…</p> : (
          <>
            {tab === "dashboard" && <Dashboard {...data} onMatch={(m) => setModal({ kind: "matches", item: m })} />}

            {tab === "consultants" && (
              <Page title="Consultants" onAdd={open("consultant")}>
                <Table rows={data.consultants} empty="Aucun consultant" actions={rowActions("consultant", "/consultants/", "name")}
                  columns={[
                    { key: "name", label: "Nom", render: (x) => <><b>{x.name}</b><div className="muted">{x.title}</div></> },
                    { key: "exp", label: "Exp.", render: (x) => `${x.experience_years} ans` },
                    { key: "skills", label: "Compétences", render: (x) => <SkillChips items={x.skills} /> },
                    { key: "tjm", label: "TJM", render: (x) => euro(x.tjm) },
                    { key: "reserve", label: "Réserve", render: (x) => x.reserve_pct ? <>{euro(x.reserve_amount)}<div className="muted">{x.reserve_pct} %</div></> : "—" },
                    { key: "salary", label: "Salaire / mois", render: (x) => <>{euro(x.monthly.salary)}<div className="muted">{x.days_per_month} j</div></> },
                    { key: "mission", label: "Mission", render: (x) => x.mission?.title ?? "—" },
                    { key: "cv", label: "CV", render: (x) => x.cv
                      ? <button className="link" onClick={() => download(`/consultants/${x.id}/cv`, x.cv.filename).catch((e) => setError(e.message))}>Télécharger</button>
                      : "—" },
                    { key: "avail", label: "Disponibilité", render: (x) => x.available_from && x.available_from > today() ? frDate(x.available_from) : "Immédiate" },
                    { key: "status", label: "Statut" },
                  ]} />
              </Page>
            )}

            {tab === "companies" && (
              <Page title="Entreprises" onAdd={open("company")}>
                <Table rows={data.companies} empty="Aucune entreprise" actions={rowActions("company", "/companies/", "name")}
                  columns={[
                    { key: "name", label: "Entreprise", render: (x) => <b>{x.name}</b> },
                    { key: "sector", label: "Secteur" },
                    { key: "city", label: "Ville" },
                    { key: "contact_name", label: "Contact" },
                    { key: "email", label: "Email", render: (x) => x.email ?? "—" },
                  ]} />
              </Page>
            )}

            {tab === "missions" && (
              <Page title="Missions" onAdd={open("mission")}>
                <Table rows={data.missions} empty="Aucune mission"
                  actions={(r) => (
                    <>
                      <button className="primary small" onClick={open("matches", r)}>Matching</button>
                      {rowActions("mission", "/missions/", "title")(r)}
                    </>
                  )}
                  columns={[
                    { key: "title", label: "Mission", render: (x) => <><b>{x.title}</b><div className="muted">{x.company?.name ?? "—"} · {x.location}</div></> },
                    { key: "skills", label: "Compétences", render: (x) => <SkillChips items={x.skills} /> },
                    { key: "start", label: "Démarrage", render: (x) => frDate(x.start_date) },
                    { key: "dur", label: "Durée", render: (x) => (x.duration_months ? `${x.duration_months} mois` : "—") },
                    { key: "tjm", label: "TJM max", render: (x) => euro(x.tjm_max) },
                    { key: "status", label: "Statut", render: (x) => <span className={`status s-${x.status}`}>{x.status}</span> },
                  ]} />
              </Page>
            )}

            {tab === "trainings" && (
              <Page title="Formations" onAdd={open("training")}>
                <Table rows={data.trainings} empty="Aucune formation" actions={rowActions("training", "/trainings/", "title")}
                  columns={[
                    { key: "title", label: "Formation", render: (x) => <b>{x.title}</b> },
                    { key: "skill", label: "Compétence", render: (x) => x.skill?.name ?? "—" },
                    { key: "level", label: "Niveau" },
                    { key: "dur", label: "Durée", render: (x) => (x.duration_days ? `${x.duration_days} j` : "—") },
                    { key: "price", label: "Prix", render: (x) => euro(x.price) },
                    { key: "online", label: "Format", render: (x) => (x.online ? "En ligne" : "Présentiel") },
                  ]} />
              </Page>
            )}

            {tab === "users" && (
              <Page title="Utilisateurs" onAdd={open("user")}>
                <Table rows={data.users} empty="Aucun compte"
                  actions={(r) => (
                    <>
                      <button className="link" onClick={open("user", r)}>Modifier</button>
                      {r.id !== user.id && <button className="link danger" onClick={() => remove(`/users/${r.id}`, r.email)}>Supprimer</button>}
                    </>
                  )}
                  columns={[
                    { key: "email", label: "Email", render: (x) => <b>{x.email}</b> },
                    { key: "role", label: "Rôle", render: (x) => ROLES[x.role] },
                    { key: "link", label: "Rattaché à", render: (x) =>
                      data.consultants.find((c) => c.id === x.consultant_id)?.name
                      ?? data.companies.find((c) => c.id === x.company_id)?.name ?? "—" },
                    { key: "active", label: "Statut", render: (x) => x.active ? "Actif" : <span className="status s-inactive">Désactivé</span> },
                  ]} />
                <p className="muted">Un administrateur a accès à tout. Un consultant ne voit et ne modifie que sa propre fiche. Une entreprise partenaire gère sa fiche et publie ses missions.</p>
              </Page>
            )}
          </>
        )}
      </main>

      {modal?.kind === "consultant" && <ConsultantForm item={modal.item} catalog={data.skills} missions={data.missions} onClose={close} onSaved={saved} />}
      {modal?.kind === "company" && <CompanyForm item={modal.item} onClose={close} onSaved={saved} />}
      {modal?.kind === "mission" && <MissionForm item={modal.item} catalog={data.skills} companies={data.companies} onClose={close} onSaved={saved} />}
      {modal?.kind === "training" && <TrainingForm item={modal.item} catalog={data.skills} onClose={close} onSaved={saved} />}
      {modal?.kind === "user" && <UserForm item={modal.item} consultants={data.consultants} companies={data.companies} onClose={close} onSaved={saved} />}
      {modal?.kind === "matches" && <Matches mission={modal.item} onClose={close} />}
    </div>
  );
}

const today = () => new Date().toISOString().slice(0, 10);

function Dashboard({ consultants, companies, missions, trainings, onMatch }) {
  const open = missions.filter((m) => m.status === "Ouverte");
  return (
    <>
      <h1>Dashboard</h1>
      <div className="cards">
        <Card n={consultants.length} t="Consultants" />
        <Card n={companies.length} t="Entreprises" />
        <Card n={open.length} t="Missions ouvertes" sub={`${missions.length} au total`} />
        <Card n={trainings.length} t="Formations" />
      </div>
      <section>
        <h2>Missions ouvertes</h2>
        {open.length === 0 ? <p className="muted">Aucune mission ouverte.</p> : (
          <div className="open-missions">
            {open.map((m) => (
              <div key={m.id} className="card mission-card">
                <div><b>{m.title}</b><div className="muted">{m.company?.name ?? "—"} · TJM max {euro(m.tjm_max)}</div></div>
                <button className="primary small" onClick={() => onMatch(m)}>Voir les profils</button>
              </div>
            ))}
          </div>
        )}
      </section>
      <section>
        <h2>Positionnement</h2>
        <p>Former → Qualifier → Matcher → Missionner → Freelance / Portage salarial</p>
      </section>
    </>
  );
}

function Card({ n, t, sub }) {
  return <div className="card"><b>{n}</b><span>{t}</span>{sub && <small className="muted">{sub}</small>}</div>;
}

createRoot(document.getElementById("root")).render(<Root />);
