import React, { useCallback, useEffect, useState } from "react";
import { api, download, euro, frDate, frMonth } from "../api.js";
import { Alert, Field, InvoiceStatus, Modal, Page, SkillChips, Table } from "./ui.jsx";
import { CompanyForm, MissionForm } from "./forms.jsx";
import { ProfileCard } from "./ConsultantProfile.jsx";
import Header from "./Header.jsx";

/** Espace entreprise partenaire : sa fiche, ses missions (postes à pourvoir), les consultants que
 *  CloudTalent lui propose (profil + CV), et le catalogue de formations avec inscriptions. */
export default function CompanySpace({ user, onLogout }) {
  const [company, setCompany] = useState(null);
  const [missions, setMissions] = useState([]);
  const [catalog, setCatalog] = useState([]);
  const [proposals, setProposals] = useState([]);
  const [trainings, setTrainings] = useState([]);
  const [enrollments, setEnrollments] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [error, setError] = useState(null);
  // modal = {kind: "company"|"mission"|"proposals"|"enroll", item?}
  const [modal, setModal] = useState(null);

  const load = useCallback(async () => {
    try {
      const [c, m, skills, p, t, e, inv] = await Promise.all(
        ["/companies/me", "/missions/", "/skills/", "/proposals/", "/trainings/", "/enrollments/", "/invoices/"].map((x) => api(x))
      );
      setInvoices(inv);
      setCompany(c);
      setMissions(m);
      setCatalog(skills);
      setProposals(p);
      setTrainings(t);
      setEnrollments(e);
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
  const act = (fn) => async (...args) => {
    try {
      await fn(...args);
      load();
    } catch (e) {
      setError(e.message);
    }
  };
  const decide = act((p, status) => api(`/proposals/${p.id}`, { method: "PUT", body: { status } }));
  const cancel = act((e) => window.confirm(`Annuler l'inscription de ${e.participant_name} ?`)
    && api(`/enrollments/${e.id}`, { method: "PUT", body: { status: "Annulée" } }));
  const open = missions.filter((m) => m.status === "Ouverte").length;
  const due = invoices.filter((i) => i.status === "Paiement demandé");
  const proposed = (m) => proposals.filter((p) => p.mission.id === m.id);

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
                  { key: "proposals", label: "Consultants proposés", render: (x) => proposed(x).length
                    ? <button className="primary small" onClick={() => setModal({ kind: "proposals", item: x })}>Voir les profils ({proposed(x).length})</button>
                    : <span className="muted">En cours</span> },
                ]} />
              <p className="muted">CloudTalent étudie chaque mission ouverte et vous propose ses consultants.</p>
            </Page>

            <Page title="Factures à régler">
              <Table rows={invoices} empty="Aucune facture pour le moment."
                actions={(r) => <button className="link" onClick={() => download(`/invoices/${r.id}/file`, r.filename).catch((e) => setError(e.message))}>Télécharger</button>}
                columns={[
                  { key: "period", label: "Mois", render: (x) => <b>{frMonth(x.period)}</b> },
                  { key: "who", label: "Consultant", render: (x) => <>{x.consultant.name}<div className="muted">{x.mission?.title}</div></> },
                  { key: "days", label: "Jours", render: (x) => `${x.days} j` },
                  { key: "tjm", label: "TJM", render: (x) => euro(x.billing_tjm) },
                  { key: "amount", label: "Montant HT", render: (x) => <b>{euro(x.amount)}</b> },
                  { key: "status", label: "Statut", render: (x) => <InvoiceStatus status={x.status === "Paiement demandé" ? "À régler" : x.status} /> },
                ]} />
              {due.length > 0 && <p className="muted">Total à régler à CloudTalent : <b>{euro(due.reduce((s, i) => s + (i.amount ?? 0), 0))}</b> HT.</p>}
            </Page>

            <Page title="Nos formations">
              <Table rows={trainings} empty="Aucune formation au catalogue."
                actions={(r) => <button className="primary small" onClick={() => setModal({ kind: "enroll", item: r })}>Inscrire</button>}
                columns={[
                  { key: "title", label: "Formation", render: (x) => <b>{x.title}</b> },
                  { key: "skill", label: "Compétence", render: (x) => x.skill?.name ?? "—" },
                  { key: "level", label: "Niveau" },
                  { key: "dur", label: "Durée", render: (x) => (x.duration_days ? `${x.duration_days} j` : "—") },
                  { key: "price", label: "Prix", render: (x) => euro(x.price) },
                  { key: "online", label: "Format", render: (x) => (x.online ? "En ligne" : "Présentiel") },
                ]} />
              <h2>Mes inscriptions</h2>
              <Table rows={enrollments} empty="Aucune inscription."
                actions={(r) => r.status !== "Annulée" && <button className="link danger" onClick={() => cancel(r)}>Annuler</button>}
                columns={[
                  { key: "training", label: "Formation", render: (x) => <b>{x.training.title}</b> },
                  { key: "who", label: "Participant", render: (x) => <>{x.participant_name}<div className="muted">{x.participant_email}</div></> },
                  { key: "date", label: "Demandée le", render: (x) => new Date(x.created_at).toLocaleDateString("fr-FR") },
                  { key: "status", label: "Statut", render: (x) => <span className={`status s-${x.status}`}>{x.status}</span> },
                ]} />
            </Page>
          </div>
        )}
      </main>
      {modal?.kind === "company" && <CompanyForm self item={company} onClose={close} onSaved={saved} />}
      {modal?.kind === "mission" && <MissionForm own item={modal.item} catalog={catalog} onClose={close} onSaved={saved} />}
      {modal?.kind === "proposals" && (
        <Modal title={`Consultants proposés — ${modal.item.title}`} onClose={close}>
          {proposed(modal.item).map((p) => (
            <div key={p.id} className="proposal">
              <ProfileCard consultant={p.consultant} cvPath={`/proposals/${p.id}/cv`}>
                <div className="proposal-actions">
                  <span className={`status s-${p.status}`}>{p.status}</span>
                  {p.status !== "Retenu" && <button className="primary small" onClick={() => decide(p, "Retenu")}>Retenir</button>}
                  {p.status !== "Refusé" && <button className="link danger" onClick={() => decide(p, "Refusé")}>Refuser</button>}
                </div>
              </ProfileCard>
            </div>
          ))}
        </Modal>
      )}
      {modal?.kind === "enroll" && <EnrollForm training={modal.item} onClose={close} onSaved={saved} />}
    </div>
  );
}

function Info({ label, value }) {
  return <div><span className="muted">{label}</span><div>{value || "—"}</div></div>;
}

/** Inscription d'un collaborateur de l'entreprise à une formation. */
function EnrollForm({ training, onClose, onSaved }) {
  const [v, setV] = useState({ participant_name: "", participant_email: "" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setV({ ...v, [k]: e.target.value });
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api("/enrollments/", { method: "POST", body: { training_id: training.id, ...v } });
      onSaved();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal title={`Inscription — ${training.title}`} onClose={onClose}>
      <form onSubmit={submit} className="grid-form">
        <Field label="Nom du participant *"><input required value={v.participant_name} onChange={set("participant_name")} autoFocus /></Field>
        <Field label="Email *"><input type="email" required value={v.participant_email} onChange={set("participant_email")} /></Field>
        <p className="muted wide">{euro(training.price)} · {training.duration_days ? `${training.duration_days} j` : "durée à définir"} · CloudTalent confirme l'inscription.</p>
        <Alert onClose={() => setError(null)}>{error}</Alert>
        <div className="form-actions">
          <button type="button" onClick={onClose}>Annuler</button>
          <button className="primary" disabled={busy}>{busy ? "Inscription…" : "Inscrire"}</button>
        </div>
      </form>
    </Modal>
  );
}
