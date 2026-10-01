import React from "react";
import { LEVELS } from "../api.js";

/**
 * Éditeur de compétences.
 *  mode="consultant" : [{name, level}]
 *  mode="mission"    : [{name, min_level, required}]
 */
export default function SkillsEditor({ value, onChange, catalog, mode }) {
  const isMission = mode === "mission";
  const levelKey = isMission ? "min_level" : "level";
  const update = (i, patch) => onChange(value.map((s, j) => (j === i ? { ...s, ...patch } : s)));
  const remove = (i) => onChange(value.filter((_, j) => j !== i));
  const add = () => onChange([...value, isMission ? { name: "", min_level: 3, required: true } : { name: "", level: 3 }]);

  return (
    <div className="skills-editor">
      <datalist id="skills-catalog">
        {catalog.map((s) => <option key={s.id} value={s.name} />)}
      </datalist>
      {value.map((s, i) => (
        <div className="skill-row" key={i}>
          <input list="skills-catalog" placeholder="ex. Kubernetes" value={s.name}
                 onChange={(e) => update(i, { name: e.target.value })} aria-label="Compétence" />
          <select value={s[levelKey]} onChange={(e) => update(i, { [levelKey]: Number(e.target.value) })}
                  aria-label={isMission ? "Niveau minimum" : "Niveau"}>
            {Object.entries(LEVELS).map(([n, l]) => (
              <option key={n} value={n}>{isMission ? `min. ${n} · ${l}` : `${n} · ${l}`}</option>
            ))}
          </select>
          {isMission && (
            <label className="check">
              <input type="checkbox" checked={s.required} onChange={(e) => update(i, { required: e.target.checked })} />
              Obligatoire
            </label>
          )}
          <button type="button" className="icon" onClick={() => remove(i)} aria-label="Retirer">×</button>
        </div>
      ))}
      <button type="button" className="link" onClick={add}>+ Ajouter une compétence</button>
    </div>
  );
}

/** Convertit les compétences renvoyées par l'API vers le format de l'éditeur. */
export function toEditor(skills, mode) {
  return (skills || []).map((s) =>
    mode === "mission"
      ? { name: s.skill.name, min_level: s.min_level, required: s.required }
      : { name: s.skill.name, level: s.level }
  );
}

export function cleanSkills(skills) {
  return skills.filter((s) => s.name.trim() !== "").map((s) => ({ ...s, name: s.name.trim() }));
}
