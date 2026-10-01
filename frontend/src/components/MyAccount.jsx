import React, { useCallback, useEffect, useState } from "react";
import { api, euro, frDate } from "../api.js";
import { Alert, SkillChips } from "./ui.jsx";
import { ConsultantForm } from "./forms.jsx";
import Header from "./Header.jsx";

/** Espace consultant : uniquement sa propre fiche, consultable et modifiable. */
export default function MyAccount({ user, onLogout }) {
  const [me, setMe] = useState(null);
  const [catalog, setCatalog] = useState([]);
  const [error, setError] = useState(null);
  const [editing, setEditing] = useState(false);

  const load = useCallback(async () => {
    try {
      const [profile, skills] = await Promise.all([api("/consultants/me"), api("/skills/")]);
      setMe(profile);
      setCatalog(skills);
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
          <section>
            <div className="titlebar">
              <h1>Mon compte</h1>
              <button className="primary" onClick={() => setEditing(true)}>Modifier ma fiche</button>
            </div>
            <div className="card profile">
              <div>
                <b className="profile-name">{me.name}</b>
                <div className="muted">{me.title} · {me.status} · {me.experience_years} ans d'expérience</div>
                <div className="muted">{me.email ?? "—"}</div>
              </div>
              <div className="cards">
                <Stat label="TJM" value={euro(me.tjm)} />
                <Stat label={`Réserve (${me.reserve_pct} %)`} value={euro(me.reserve_amount)} sub="par jour" />
                <Stat label="TJM net" value={euro(me.tjm_net)} />
                <Stat label="Disponibilité" value={me.available_from ? frDate(me.available_from) : "Immédiate"} />
              </div>
              <div>
                <h2>Compétences</h2>
                {me.skills.length ? <SkillChips items={me.skills} /> : <p className="muted">Aucune compétence renseignée.</p>}
              </div>
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

function Stat({ label, value, sub }) {
  return <div className="stat"><span className="muted">{label}</span><b>{value}</b>{sub && <small className="muted">{sub}</small>}</div>;
}
