import React, { useState } from "react";
import { download, euro, fileSize, frDate } from "../api.js";
import { Alert, Modal, SkillChips } from "./ui.jsx";

/** Profil consultant (partie commune admin / entreprise). `cvPath` : URL de téléchargement du CV,
 *  différente pour l'entreprise qui n'y accède que via une proposition. */
export function ProfileCard({ consultant: c, cvPath, children }) {
  const [error, setError] = useState(null);
  return (
    <div className="profile-card">
      <div>
        <b className="profile-name">{c.name}</b>
        <div className="muted">{c.title} · {c.status} · {c.experience_years} ans d'expérience</div>
        <div className="muted">
          Disponibilité : {c.available_from && c.available_from > new Date().toISOString().slice(0, 10) ? frDate(c.available_from) : "immédiate"}
        </div>
      </div>
      {c.skills.length ? <SkillChips items={c.skills} /> : <p className="muted">Aucune compétence renseignée.</p>}
      <div className="cv-row">
        <b className="cv-label">CV</b>
        {c.cv ? (
          <>
            <button className="link" onClick={() => download(cvPath, c.cv.filename).catch((e) => setError(e.message))}>
              {c.cv.filename}
            </button>
            <span className="muted">{fileSize(c.cv.size)} · mis à jour le {new Date(c.cv.uploaded_at).toLocaleDateString("fr-FR")}</span>
          </>
        ) : <span className="muted">Pas encore de CV</span>}
      </div>
      <Alert onClose={() => setError(null)}>{error}</Alert>
      {children}
    </div>
  );
}

/** Fiche complète pour l'admin : profil, CV, rémunération, mission. */
export default function ConsultantProfile({ consultant: c, onClose }) {
  return (
    <Modal title="Profil consultant" onClose={onClose}>
      <ProfileCard consultant={c} cvPath={`/consultants/${c.id}/cv`}>
        <div className="cards">
          <div className="stat"><span className="muted">Email</span><b className="small">{c.email ?? "—"}</b></div>
          <div className="stat"><span className="muted">Mission en cours</span><b className="small">{c.mission?.title ?? "Aucune"}</b></div>
          <div className="stat"><span className="muted">TJM</span><b>{euro(c.tjm)}</b></div>
          <div className="stat">
            <span className="muted">Salaire / mois</span><b>{euro(c.monthly.salary)}</b>
            <small className="muted">{c.days_per_month} j · réserve {c.reserve_pct} % ({euro(c.monthly.reserve)})</small>
          </div>
        </div>
      </ProfileCard>
    </Modal>
  );
}
