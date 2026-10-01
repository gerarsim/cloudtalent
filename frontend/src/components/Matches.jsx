import React, { useEffect, useState } from "react";
import { api, euro, frDate, LEVELS } from "../api.js";
import { Alert, Modal } from "./ui.jsx";

// Un profil non éligible n'est jamais affiché en vert, même avec un bon score.
function scoreClass(m) {
  if (!m.eligible) return "low";
  return m.score >= 80 ? "good" : m.score >= 50 ? "mid" : "low";
}

function SkillTag({ s, missing }) {
  const under = !missing && s.level < s.min_level;
  const cls = missing ? (s.required ? "chip miss" : "chip miss optional") : under ? "chip under" : "chip ok";
  const title = missing
    ? `Manquante${s.required ? " (obligatoire)" : " (souhaitée)"}`
    : `${LEVELS[s.level]} — requis : ${LEVELS[s.min_level]}`;
  return (
    <span className={cls} title={title}>
      {s.name}
      {!missing && <small>{s.level}/{s.min_level}</small>}
    </span>
  );
}

export default function Matches({ mission, onClose }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [onlyEligible, setOnlyEligible] = useState(false);

  useEffect(() => {
    setData(null);
    api(`/missions/${mission.id}/matches?only_eligible=${onlyEligible}`).then(setData).catch((e) => setError(e.message));
  }, [mission.id, onlyEligible]);

  return (
    <Modal title={`Matching — ${mission.title}`} onClose={onClose}>
      <div className="match-head">
        <span className="muted">
          {mission.company?.name ?? "Sans entreprise"} · TJM max {euro(mission.tjm_max)} · démarrage {frDate(mission.start_date)}
        </span>
        <label className="check">
          <input type="checkbox" checked={onlyEligible} onChange={(e) => setOnlyEligible(e.target.checked)} />
          Uniquement les profils éligibles
        </label>
      </div>
      <Alert>{error}</Alert>
      {mission.skills.length === 0 && <p className="muted">Ajoutez des compétences à la mission pour lancer le matching.</p>}
      {data === null && !error && mission.skills.length > 0 && <p className="muted">Calcul…</p>}
      {data?.length === 0 && mission.skills.length > 0 && <p className="muted">Aucun consultant ne correspond.</p>}
      <ol className="matches">
        {data?.map((m) => (
          <li key={m.consultant.id} className={m.eligible ? "" : "not-eligible"}>
            <div className={`score ${scoreClass(m)}`} title={`Compétences ${m.skill_score} %`}>
              {m.score}
            </div>
            <div className="match-body">
              <div className="match-title">
                <b>{m.consultant.name}</b> <span className="muted">{m.consultant.title} · {m.consultant.experience_years} ans</span>
              </div>
              <div className="badges">
                <span className={m.eligible ? "badge ok" : "badge ko"}>{m.eligible ? "Éligible" : "Compétence obligatoire manquante"}</span>
                <span className={m.tjm_ok ? "badge ok" : "badge warn"}>TJM {euro(m.consultant.tjm)}</span>
                <span className={m.available ? "badge ok" : "badge warn"}>
                  {m.available ? "Disponible" : `Dispo le ${frDate(m.consultant.available_from)}`}
                </span>
                <span className="badge">Compétences {m.skill_score} %</span>
              </div>
              <div className="chips">
                {m.matched.map((s) => <SkillTag key={s.name} s={s} />)}
                {m.missing.map((s) => <SkillTag key={s.name} s={s} missing />)}
              </div>
            </div>
          </li>
        ))}
      </ol>
      <p className="legend muted">
        Score = 70 % compétences (obligatoires ×3, souhaitées ×1, au prorata du niveau) + 15 % TJM + 15 % disponibilité.
      </p>
    </Modal>
  );
}
