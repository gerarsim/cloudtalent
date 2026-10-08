import React, { useCallback, useEffect, useState } from "react";
import { api, euro, frDate } from "../api.js";
import { Alert, Page, SkillChips, Table } from "./ui.jsx";
import { CompanyForm, MissionForm } from "./forms.jsx";
import Header from "./Header.jsx";

/** Espace entreprise partenaire : sa fiche et les missions (postes à pourvoir) qu'elle publie. */
export default function CompanySpace({ user, onLogout }) {
  const [company, setCompany] = useState(null);
  const [missions, setMissions] = useState([]);
  const [catalog, setCatalog] = useState([]);
  const [error, setError] = useState(null);
  // modal = {kind: "company"|"mission", item?}
  const [modal, setModal] = useState(null);

  const load = useCallback(async () => {
    try {
      const [c, m, skills] = await Promise.all([api("/companies/me"), api("/missions/"), api("/skills/")]);
      setCompany(c);
      setMissions(m);
      setCatalog(skills);
      setError(null);
    } catch (e) {
      setError(e.message);
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  const close = useCallback(() => setModal(null), []);
  const saved = () => { setModal(null); load(); };
  const remove = async (m) => {
    if (!window.confirm(`Supprimer la mission « ${m.title} » ?`)) return;
    try {
      await api(`/missions/${m.id}`, { method: "DELETE" });
      load();
    } catch (e) {
      setError(e.message);
    }
  };
  const open = missions.filter((m) => m.status === "Ouverte").length;

  return (
    <div className="app">
      <Header user={user} onLogout={onLogout} />
      <main>
        <Alert onClose={() => setError(null)}>{error}</Alert>
        {!company ? (!error && <p className="muted">Chargement…</p>) : (
          <div className="my-profile">
            <section>
              <div className="titlebar">
                <h1>{company.name}</h1>
                <button onClick={() => setModal({ kind: "company" })}>Modifier mon entreprise</button>
              </div>
              <div className="card profile">
                <div className="company-info">
                  <Info label="Secteur" value={company.sector} />
                  <Info label="N° TVA" value={company.vat_number} />
                  <Info label="Adresse" value={[company.address, company.city].filter(Boolean).join(", ")} />
                  <Info label="Site web" value={company.website && <a href={company.website} target="_blank" rel="noreferrer">{company.website}</a>} />
                  <Info label="Contact" value={company.contact_name} />
                  <Info label="Email" value={company.email} />
                  <Info label="Téléphone" value={company.phone} />
                </div>
                {company.description
                  ? <p className="pre">{company.description}</p>
                  : <p className="muted">Ajoutez une présentation de votre entreprise pour nos consultants.</p>}
              </div>
            </section>

            <Page title={`Mes missions (${open} ouverte${open > 1 ? "s" : ""})`} onAdd={() => setModal({ kind: "mission" })}>
              <Table rows={missions} empty="Aucune mission publiée. Ajoutez vos postes à pourvoir."
                actions={(r) => (
                  <>
                    <button className="link" onClick={() => setModal({ kind: "mission", item: r })}>Modifier</button>
                    <button className="link danger" onClick={() => remove(r)}>Supprimer</button>
                  </>
                )}
                columns={[
                  { key: "title", label: "Poste", render: (x) => <><b>{x.title}</b><div className="muted">{x.location}</div></> },
                  { key: "skills", label: "Compétences", render: (x) => <SkillChips items={x.skills} /> },
                  { key: "start", label: "Démarrage", render: (x) => frDate(x.start_date) },
                  { key: "dur", label: "Durée", render: (x) => (x.duration_months ? `${x.duration_months} mois` : "—") },
                  { key: "tjm", label: "TJM max", render: (x) => euro(x.tjm_max) },
                  { key: "status", label: "Statut", render: (x) => <span className={`status s-${x.status}`}>{x.status}</span> },
                ]} />
              <p className="muted">CloudTalent étudie chaque mission ouverte et vous propose ses consultants.</p>
            </Page>
          </div>
        )}
      </main>
      {modal?.kind === "company" && <CompanyForm self item={company} onClose={close} onSaved={saved} />}
      {modal?.kind === "mission" && <MissionForm own item={modal.item} catalog={catalog} onClose={close} onSaved={saved} />}
    </div>
  );
}

function Info({ label, value }) {
  return <div><span className="muted">{label}</span><div>{value || "—"}</div></div>;
}
