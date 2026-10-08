import React, { useState } from "react";
import { api, euro, orNull, CONSULTANT_STATUSES, MISSION_STATUSES, ROLES, TRAINING_LEVELS } from "../api.js";
import { Alert, Field, Modal } from "./ui.jsx";
import SkillsEditor, { cleanSkills, toEditor } from "./SkillsEditor.jsx";

/** Logique commune : état local, POST (création) ou PUT (édition), erreurs API.
 *  `url` remplace l'URL calculée (ex. PUT /consultants/me pour sa propre fiche). */
function useForm(initial, { path, item, url, toBody, onSaved }) {
  const [v, setV] = useState(initial);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setV({ ...v, [k]: e?.target ? (e.target.type === "checkbox" ? e.target.checked : e.target.value) : e });
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api(url ?? (item ? `${path}${item.id}` : path), { method: item ? "PUT" : "POST", body: toBody(v) });
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

/** Calcul mensuel affiché au consultant et à l'admin (même formule que l'API). */
export function salary(tjm, reservePct, days) {
  const revenue = num(tjm) * num(days);
  const reserve = revenue * num(reservePct) / 100;
  return { revenue, reserve, salary: revenue - reserve };
}

/** `self` : le consultant modifie sa propre fiche (PUT /consultants/me). Nom, email, statut,
 *  TJM et mission restent gérés par l'admin ; réserve et jours se règlent sur « Mon profil ». */
export function ConsultantForm({ item, catalog, missions = [], self, onClose, onSaved }) {
  const f = useForm(
    {
      name: item?.name ?? "", title: item?.title ?? "", email: item?.email ?? "",
      experience_years: item?.experience_years ?? 0, tjm: item?.tjm ?? "",
      reserve_pct: item?.reserve_pct ?? 0, days_per_month: item?.days_per_month ?? 20,
      mission_id: item?.mission?.id ?? "",
      available_from: item?.available_from ?? "", status: item?.status ?? "Freelance",
      skills: item ? toEditor(item.skills, "consultant") : [{ name: "", level: 3 }],
    },
    {
      path: "/consultants/", item, onSaved, url: self ? "/consultants/me" : undefined,
      toBody: (v) => {
        const common = {
          title: v.title, experience_years: num(v.experience_years), reserve_pct: num(v.reserve_pct),
          days_per_month: num(v.days_per_month), available_from: orNull(v.available_from),
          skills: cleanSkills(v.skills),
        };
        return self ? common : {
          ...common, name: v.name, email: orNull(v.email.trim()), tjm: num(v.tjm), status: v.status,
          mission_id: intOrNull(v.mission_id),
        };
      },
    }
  );
  const { v, set } = f;
  const pay = salary(v.tjm, v.reserve_pct, v.days_per_month);
  return (
    <Modal title={self ? "Modifier mon profil" : item ? "Modifier le consultant" : "Nouveau consultant"} onClose={onClose}>
      <form onSubmit={f.submit} className="grid-form">
        {!self && <Field label="Nom *"><input required value={v.name} onChange={set("name")} autoFocus /></Field>}
        <Field label="Profil *"><input required value={v.title} onChange={set("title")} placeholder="Senior DevOps Engineer" autoFocus={self} /></Field>
        {!self && <>
          <Field label="Email"><input type="email" value={v.email} onChange={set("email")} /></Field>
          <Field label="Statut">
            <select value={v.status} onChange={set("status")}>{CONSULTANT_STATUSES.map((s) => <option key={s}>{s}</option>)}</select>
          </Field>
        </>}
        <Field label="Expérience (ans)"><input type="number" min="0" max="60" value={v.experience_years} onChange={set("experience_years")} /></Field>
        {!self && <>
          <Field label="TJM (€)"><input type="number" min="0" step="10" value={v.tjm} onChange={set("tjm")} /></Field>
          <Field label="Mission en cours">
            <select value={v.mission_id} onChange={set("mission_id")}>
              <option value="">Aucune</option>
              {missions.map((m) => <option key={m.id} value={m.id}>{m.title}{m.company ? ` · ${m.company.name}` : ""}</option>)}
            </select>
          </Field>
          <Field label="Réserve (% du CA)"><input type="number" min="0" max="100" step="1" value={v.reserve_pct} onChange={set("reserve_pct")} /></Field>
          <Field label="Jours facturés / mois">
            <input type="number" min="0" max="31" value={v.days_per_month} onChange={set("days_per_month")} />
            <small className="muted">CA {euro(pay.revenue)} · réserve {euro(pay.reserve)} · salaire {euro(pay.salary)}</small>
          </Field>
        </>}
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

export function UserForm({ item, consultants, onClose, onSaved }) {
  const f = useForm(
    {
      email: item?.email ?? "", password: "", role: item?.role ?? "consultant",
      consultant_id: item?.consultant_id ?? "", active: item?.active ?? true,
    },
    {
      path: "/users/", item, onSaved,
      toBody: (v) => ({
        ...v, email: v.email.trim(), password: orNull(v.password),
        consultant_id: v.role === "consultant" ? (v.consultant_id === "" ? null : Number(v.consultant_id)) : null,
      }),
    }
  );
  const { v, set } = f;
  return (
    <Modal title={item ? "Modifier le compte" : "Nouveau compte"} onClose={onClose}>
      <form onSubmit={f.submit} className="grid-form">
        <Field label="Email de connexion *"><input type="email" required value={v.email} onChange={set("email")} autoFocus /></Field>
        <Field label={item ? "Nouveau mot de passe" : "Mot de passe *"}>
          <input type="password" minLength={8} required={!item} value={v.password} onChange={set("password")}
                 autoComplete="new-password" placeholder={item ? "inchangé si vide" : "8 caractères min."} />
        </Field>
        <Field label="Rôle">
          <select value={v.role} onChange={set("role")}>
            {Object.entries(ROLES).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
          </select>
        </Field>
        {v.role === "consultant" && (
          <Field label="Fiche consultant *">
            <select required value={v.consultant_id} onChange={set("consultant_id")}>
              <option value="">—</option>
              {consultants.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </Field>
        )}
        <label className="check field"><input type="checkbox" checked={v.active} onChange={set("active")} /> Compte actif</label>
        <Alert onClose={() => f.setError(null)}>{f.error}</Alert>
        <Actions busy={f.busy} onClose={onClose} item={item} />
      </form>
    </Modal>
  );
}

export function PasswordForm({ onClose, onSaved }) {
  const f = useForm(
    { current_password: "", new_password: "" },
    { path: "/auth/password", onSaved, toBody: (v) => v }
  );
  const { v, set } = f;
  return (
    <Modal title="Changer mon mot de passe" onClose={onClose}>
      <form onSubmit={f.submit} className="grid-form">
        <Field label="Mot de passe actuel"><input type="password" required value={v.current_password} onChange={set("current_password")} autoComplete="current-password" autoFocus /></Field>
        <Field label="Nouveau mot de passe"><input type="password" required minLength={8} value={v.new_password} onChange={set("new_password")} autoComplete="new-password" /></Field>
        <Alert onClose={() => f.setError(null)}>{f.error}</Alert>
        <Actions busy={f.busy} onClose={onClose} item />
      </form>
    </Modal>
  );
}
