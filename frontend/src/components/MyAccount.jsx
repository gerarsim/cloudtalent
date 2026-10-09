import React, { useCallback, useEffect, useRef, useState } from "react";
import { api, download, euro, fileSize, frDate, upload } from "../api.js";
import { Alert, SkillChips } from "./ui.jsx";
import { ConsultantForm, salary } from "./forms.jsx";
import Header from "./Header.jsx";

/** Espace consultant : uniquement son profil. Il règle sa réserve, ses jours facturés et son CV ;
 *  nom, TJM, statut et mission sont gérés par l'admin. */
export default function MyAccount({ user, onLogout }) {
  const [me, setMe] = useState(null);
  const [catalog, setCatalog] = useState([]);
  const [offers, setOffers] = useState([]);
  const [error, setError] = useState(null);
  const [editing, setEditing] = useState(false);

  const load = useCallback(async () => {
    try {
      const [profile, skills, o] = await Promise.all([api("/consultants/me"), api("/skills/"), api("/consultants/me/offers")]);
      setMe(profile);
      setCatalog(skills);
      setOffers(o);
      setError(null);
    } catch (e) {
      setError(e.message);
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  return (
    <div className="app">
      <Header user={user} onLogout={onLogout} />
      <main>
        <Alert onClose={() => setError(null)}>{error}</Alert>
        {!me ? (!error && <p className="muted">Chargement…</p>) : (
          <section className="my-profile">
            <div className="titlebar">
              <h1>Mon profil</h1>
              <button className="primary" onClick={() => setEditing(true)}>Modifier mon profil</button>
            </div>

            <div className="card profile">
              <div>
                <b className="profile-name">{me.name}</b>
                <div className="muted">{me.title} · {me.status} · {me.experience_years} ans d'expérience</div>
                <div className="muted">{me.email ?? "—"}</div>
              </div>
              <div className="cards">
                <Stat label="TJM" value={euro(me.tjm)} sub="fixé par CloudTalent" />
                <Stat label="Disponibilité" value={me.available_from ? frDate(me.available_from) : "Immédiate"} />
              </div>
            </div>

            <div className="card profile">
              <h2>Ma mission</h2>
              {me.mission ? (
                <div>
                  <b className="profile-name">{me.mission.title}</b>
                  <div className="muted">
                    {me.mission.company?.name ?? "—"} · {me.mission.location}
                    {me.mission.start_date && ` · début le ${frDate(me.mission.start_date)}`}
                    {me.mission.duration_months && ` · ${me.mission.duration_months} mois`}
                  </div>
                </div>
              ) : <p className="muted">Aucune mission en cours.</p>}
            </div>

            <Offers offers={offers} />
            <Pay me={me} onSaved={(p) => { setMe(p); load(); }} onError={setError} />
            <Cv me={me} onSaved={setMe} onError={setError} />

            <div className="card profile">
              <h2>Compétences</h2>
              {me.skills.length ? <SkillChips items={me.skills} /> : <p className="muted">Aucune compétence renseignée.</p>}
            </div>
          </section>
        )}
      </main>
      {editing && (
        <ConsultantForm self item={me} catalog={catalog} onClose={() => setEditing(false)}
                        onSaved={() => { setEditing(false); load(); }} />
      )}
    </div>
  );
}

/** Choix de la réserve et des jours, avec le calcul du salaire mis à jour en direct. */
function Pay({ me, onSaved, onError }) {
  const [pct, setPct] = useState(me.reserve_pct);
  const [days, setDays] = useState(me.days_per_month);
  const [busy, setBusy] = useState(false);
  const dirty = Number(pct) !== me.reserve_pct || Number(days) !== me.days_per_month;
  const pay = salary(me.tjm, pct, days);

  const save = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      onSaved(await api("/consultants/me", { method: "PUT", body: {
        title: me.title, experience_years: me.experience_years, available_from: me.available_from,
        skills: me.skills.map((s) => ({ name: s.skill.name, level: s.level })),
        reserve_pct: Number(pct) || 0, days_per_month: Number(days) || 0,
      } }));
    } catch (err) {
      onError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="card profile" onSubmit={save}>
      <h2>Mon salaire</h2>
      <div className="pay-inputs">
        <label className="field">
          <span>Réserve : <b>{Number(pct) || 0} %</b></span>
          <input type="range" min="0" max="100" step="1" value={pct} onChange={(e) => setPct(e.target.value)} />
        </label>
        <label className="field">
          <span>Jours facturés par mois</span>
          <input type="number" min="0" max="31" value={days} onChange={(e) => setDays(e.target.value)} />
        </label>
      </div>
      <table className="pay-calc">
        <tbody>
          <tr><td>TJM × jours</td><td>{euro(me.tjm)} × {Number(days) || 0} j</td><td><b>{euro(pay.revenue)}</b></td></tr>
          <tr><td>Réserve</td><td>{Number(pct) || 0} % du chiffre d'affaires</td><td>− {euro(pay.reserve)}</td></tr>
          <tr className="total"><td>Salaire mensuel</td><td className="muted">avant charges sociales</td><td><b>{euro(pay.salary)}</b></td></tr>
        </tbody>
      </table>
      {dirty && (
        <div className="form-actions">
          <button type="button" onClick={() => { setPct(me.reserve_pct); setDays(me.days_per_month); }}>Annuler</button>
          <button className="primary" disabled={busy}>{busy ? "Enregistrement…" : "Enregistrer"}</button>
        </div>
      )}
    </form>
  );
}

function Cv({ me, onSaved, onError }) {
  const input = useRef(null);
  const [busy, setBusy] = useState(false);
  const run = (fn) => async (...args) => {
    setBusy(true);
    try { await fn(...args); } catch (err) { onError(err.message); } finally { setBusy(false); }
  };
  const send = run(async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (file) onSaved(await upload("/consultants/me/cv", file));
  });
  const remove = run(async () => {
    if (!window.confirm("Supprimer votre CV ?")) return;
    await api("/consultants/me/cv", { method: "DELETE" });
    onSaved({ ...me, cv: null });
  });

  return (
    <div className="card profile">
      <h2>Mon CV</h2>
      {me.cv ? (
        <div className="cv-row">
          <button className="link" onClick={run(() => download("/consultants/me/cv", me.cv.filename))}>{me.cv.filename}</button>
          <span className="muted">{fileSize(me.cv.size)} · mis à jour le {new Date(me.cv.uploaded_at).toLocaleDateString("fr-FR")}</span>
          <button className="link danger" onClick={remove} disabled={busy}>Supprimer</button>
        </div>
      ) : <p className="muted">Aucun CV envoyé.</p>}
      <div>
        <input ref={input} type="file" accept=".pdf,.doc,.docx,.odt" hidden onChange={send} />
        <button className="primary" onClick={() => input.current.click()} disabled={busy}>
          {busy ? "Envoi…" : me.cv ? "Remplacer mon CV" : "Envoyer mon CV"}
        </button>
        <small className="muted"> PDF, DOC, DOCX ou ODT · 5 Mo max.</small>
      </div>
    </div>
  );
}

/** Missions ouvertes qui correspondent au profil (matching), avec le TJM proposé par CloudTalent. */
function Offers({ offers }) {
  return (
    <div className="card profile">
      <h2>Offres pour moi {offers.length > 0 && <span className="count">{offers.length}</span>}</h2>
      {offers.length === 0 ? (
        <p className="muted">Aucune mission ouverte ne correspond à votre profil pour le moment. Complétez vos compétences pour en recevoir.</p>
      ) : offers.map((o) => (
        <div key={o.mission.id} className="offer">
          <div className="offer-main">
            <b className="offer-title">{o.mission.title}</b>
            <div className="muted">
              {[o.sector, o.mission.location, o.mission.start_date && `début le ${frDate(o.mission.start_date)}`,
                o.mission.duration_months && `${o.mission.duration_months} mois`].filter(Boolean).join(" · ")}
            </div>
            {o.mission.description && <p className="pre">{o.mission.description}</p>}
            <div className="chips">
              {o.matched.map((s) => <span key={s.name} className={s.level >= s.min_level ? "chip ok" : "chip under"}>{s.name}<small>{s.level}/{s.min_level}</small></span>)}
              {o.missing.map((s) => <span key={s.name} className="chip miss optional">{s.name}</span>)}
            </div>
            <div className="badges">
              <span className="badge ok">Correspondance {o.score} %</span>
              {!o.available && <span className="badge warn">Démarre avant votre disponibilité</span>}
              {o.proposal_status && <span className={`status s-${o.proposal_status}`}>
                {o.proposal_status === "Proposé" ? "Votre profil a été proposé" : o.proposal_status === "Retenu" ? "Vous êtes retenu" : "Non retenu"}
              </span>}
            </div>
          </div>
          <div className="offer-pay">
            <span className="muted">TJM proposé</span>
            <b>{o.tjm == null ? "À définir" : euro(o.tjm)}</b>
            {o.monthly && <small className="muted">≈ {euro(o.monthly.salary)} / mois<br />{o.monthly.days_per_month} j, après réserve</small>}
          </div>
        </div>
      ))}
    </div>
  );
}

function Stat({ label, value, sub }) {
  return <div className="stat"><span className="muted">{label}</span><b>{value}</b>{sub && <small className="muted">{sub}</small>}</div>;
}
