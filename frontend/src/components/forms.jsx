import React, { useState } from "react";
import { api, orNull, CONSULTANT_STATUSES, MISSION_STATUSES, TRAINING_LEVELS } from "../api.js";
import { Alert, Field, Modal } from "./ui.jsx";
import SkillsEditor, { cleanSkills, toEditor } from "./SkillsEditor.jsx";

/** Logique commune : état local, POST (création) ou PUT (édition), erreurs API. */
function useForm(initial, { path, item, toBody, onSaved }) {
  const [v, setV] = useState(initial);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setV({ ...v, [k]: e?.target ? (e.target.type === "checkbox" ? e.target.checked : e.target.value) : e });
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api(item ? `${path}${item.id}` : path, { method: item ? "PUT" : "POST", body: toBody(v) });
      onSaved();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };
  return { v, set, setV, submit, error, setError, busy };
}

function Actions({ busy, onClose, item }) {
  return (
    <div className="form-actions">
      <button type="button" onClick={onClose}>Annuler</button>
      <button className="primary" disabled={busy}>{busy ? "Enregistrement…" : item ? "Enregistrer" : "Créer"}</button>
    </div>
  );
}

const num = (x) => (x === "" || x === null || x === undefined ? 0 : Number(x));
const intOrNull = (x) => (x === "" || x === null || x === undefined ? null : parseInt(x, 10));

export function ConsultantForm({ item, catalog, onClose, onSaved }) {
  const f = useForm(
    {
      name: item?.name ?? "", title: item?.title ?? "", email: item?.email ?? "",
      experience_years: item?.experience_years ?? 0, tjm: item?.tjm ?? "",
      available_from: item?.available_from ?? "", status: item?.status ?? "Freelance",
      skills: item ? toEditor(item.skills, "consultant") : [{ name: "", level: 3 }],
    },
    {
      path: "/consultants/", item, onSaved,
      toBody: (v) => ({
        ...v, email: orNull(v.email.trim()), available_from: orNull(v.available_from),
        experience_years: num(v.experience_years), tjm: num(v.tjm), skills: cleanSkills(v.skills),
      }),
    }
  );
  const { v, set } = f;
  return (
    <Modal title={item ? "Modifier le consultant" : "Nouveau consultant"} onClose={onClose}>
      <form onSubmit={f.submit} className="grid-form">
        <Field label="Nom *"><input required value={v.name} onChange={set("name")} autoFocus /></Field>
        <Field label="Profil *"><input required value={v.title} onChange={set("title")} placeholder="Senior DevOps Engineer" /></Field>
        <Field label="Email"><input type="email" value={v.email} onChange={set("email")} /></Field>
        <Field label="Statut">
          <select value={v.status} onChange={set("status")}>{CONSULTANT_STATUSES.map((s) => <option key={s}>{s}</option>)}</select>
        </Field>
        <Field label="Expérience (ans)"><input type="number" min="0" max="60" value={v.experience_years} onChange={set("experience_years")} /></Field>
        <Field label="TJM (€)"><input type="number" min="0" step="10" value={v.tjm} onChange={set("tjm")} /></Field>
        <Field label="Disponible à partir du"><input type="date" value={v.available_from} onChange={set("available_from")} /></Field>
        <Field label="Compétences" wide>
          <SkillsEditor mode="consultant" value={v.skills} onChange={set("skills")} catalog={catalog} />
        </Field>
        <Alert onClose={() => f.setError(null)}>{f.error}</Alert>
        <Actions busy={f.busy} onClose={onClose} item={item} />
      </form>
    </Modal>
  );
}

export function MissionForm({ item, catalog, companies, onClose, onSaved }) {
  const f = useForm(
    {
      title: item?.title ?? "", company_id: item?.company?.id ?? "", location: item?.location ?? "Luxembourg",
      duration_months: item?.duration_months ?? "", start_date: item?.start_date ?? "",
      tjm_max: item?.tjm_max ?? "", status: item?.status ?? "Ouverte",
      skills: item ? toEditor(item.skills, "mission") : [{ name: "", min_level: 3, required: true }],
    },
    {
      path: "/missions/", item, onSaved,
      toBody: (v) => ({
        ...v, company_id: intOrNull(v.company_id), duration_months: intOrNull(v.duration_months),
        start_date: orNull(v.start_date), tjm_max: num(v.tjm_max), skills: cleanSkills(v.skills),
      }),
    }
  );
  const { v, set } = f;
  return (
    <Modal title={item ? "Modifier la mission" : "Nouvelle mission"} onClose={onClose}>
      <form onSubmit={f.submit} className="grid-form">
        <Field label="Intitulé *" wide><input required value={v.title} onChange={set("title")} autoFocus /></Field>
        <Field label="Entreprise">
          <select value={v.company_id} onChange={set("company_id")}>
            <option value="">—</option>
            {companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </Field>
        <Field label="Lieu"><input value={v.location} onChange={set("location")} /></Field>
        <Field label="Démarrage"><input type="date" value={v.start_date} onChange={set("start_date")} /></Field>
        <Field label="Durée (mois)"><input type="number" min="1" max="60" value={v.duration_months} onChange={set("duration_months")} /></Field>
        <Field label="TJM max (€)"><input type="number" min="0" step="10" value={v.tjm_max} onChange={set("tjm_max")} /></Field>
        <Field label="Statut">
          <select value={v.status} onChange={set("status")}>{MISSION_STATUSES.map((s) => <option key={s}>{s}</option>)}</select>
        </Field>
        <Field label="Compétences recherchées" wide>
          <SkillsEditor mode="mission" value={v.skills} onChange={set("skills")} catalog={catalog} />
        </Field>
        <Alert onClose={() => f.setError(null)}>{f.error}</Alert>
        <Actions busy={f.busy} onClose={onClose} item={item} />
      </form>
    </Modal>
  );
}

export function CompanyForm({ item, onClose, onSaved }) {
  const f = useForm(
    {
      name: item?.name ?? "", sector: item?.sector ?? "", city: item?.city ?? "Luxembourg",
      contact_name: item?.contact_name ?? "", email: item?.email ?? "",
    },
    { path: "/companies/", item, onSaved, toBody: (v) => ({ ...v, email: orNull(v.email.trim()) }) }
  );
  const { v, set } = f;
  return (
    <Modal title={item ? "Modifier l'entreprise" : "Nouvelle entreprise"} onClose={onClose}>
      <form onSubmit={f.submit} className="grid-form">
        <Field label="Nom *" wide><input required value={v.name} onChange={set("name")} autoFocus /></Field>
        <Field label="Secteur"><input value={v.sector} onChange={set("sector")} placeholder="Banking, Assurance…" /></Field>
        <Field label="Ville"><input value={v.city} onChange={set("city")} /></Field>
        <Field label="Contact"><input value={v.contact_name} onChange={set("contact_name")} /></Field>
        <Field label="Email"><input type="email" value={v.email} onChange={set("email")} /></Field>
        <Alert onClose={() => f.setError(null)}>{f.error}</Alert>
        <Actions busy={f.busy} onClose={onClose} item={item} />
      </form>
    </Modal>
  );
}

export function TrainingForm({ item, catalog, onClose, onSaved }) {
  const f = useForm(
    {
      title: item?.title ?? "", skill: item?.skill?.name ?? "", level: item?.level ?? "Débutant",
      duration_days: item?.duration_days ?? "", price: item?.price ?? "", online: item?.online ?? true,
    },
    {
      path: "/trainings/", item, onSaved,
      toBody: (v) => ({ ...v, skill: orNull(v.skill.trim()), duration_days: intOrNull(v.duration_days), price: num(v.price) }),
    }
  );
  const { v, set } = f;
  return (
    <Modal title={item ? "Modifier la formation" : "Nouvelle formation"} onClose={onClose}>
      <form onSubmit={f.submit} className="grid-form">
        <Field label="Intitulé *" wide><input required value={v.title} onChange={set("title")} autoFocus /></Field>
        <Field label="Compétence visée">
          <input list="skills-catalog-t" value={v.skill} onChange={set("skill")} placeholder="ex. Terraform" />
          <datalist id="skills-catalog-t">{catalog.map((s) => <option key={s.id} value={s.name} />)}</datalist>
        </Field>
        <Field label="Niveau">
          <select value={v.level} onChange={set("level")}>{TRAINING_LEVELS.map((s) => <option key={s}>{s}</option>)}</select>
        </Field>
        <Field label="Durée (jours)"><input type="number" min="1" max="60" value={v.duration_days} onChange={set("duration_days")} /></Field>
        <Field label="Prix (€)"><input type="number" min="0" step="50" value={v.price} onChange={set("price")} /></Field>
        <label className="check field"><input type="checkbox" checked={v.online} onChange={set("online")} /> En ligne</label>
        <Alert onClose={() => f.setError(null)}>{f.error}</Alert>
        <Actions busy={f.busy} onClose={onClose} item={item} />
      </form>
    </Modal>
  );
}
