import React, { useCallback, useEffect, useRef, useState } from "react";
import { api, download, euro, frMonth, upload, TAX_CLASSES } from "../api.js";
import { Alert, Field, Modal } from "./ui.jsx";

const money = (n) => `${Number(n || 0).toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €`;
const pct = (n) => `${n.toLocaleString("fr-FR")} %`;

/** Détail brut → net luxembourgeois (simulation de app/payroll.py). */
export function PayrollTable({ p, employer = false }) {
  return (
    <table className="pay-calc payroll">
      <tbody>
        <tr><td>Salaire brut</td><td /><td><b>{money(p.gross)}</b></td></tr>
        {p.lines.map((l) => (
          <tr key={l.label}><td>{l.label}</td><td className="muted">{pct(l.rate)} de {money(l.base)}</td><td>− {money(l.amount)}</td></tr>
        ))}
        <tr><td>Impôt sur le revenu</td><td className="muted">classe {p.tax_class}, fonds pour l'emploi inclus</td><td>− {money(p.tax)}</td></tr>
        <tr><td>Crédit d'impôt salarié</td><td /><td>+ {money(p.tax_credit)}</td></tr>
        <tr className="total"><td>Net à payer</td><td /><td><b>{money(p.net)}</b></td></tr>
        {employer && <>
          <tr><td colSpan="3" className="muted">Charges patronales : {p.employer_lines.map((l) => `${l.label.replace("Assurance ", "")} ${pct(l.rate)}`).join(" · ")}</td></tr>
          <tr><td>Coût total employeur</td><td className="muted">brut + {money(p.employer_total)}</td><td><b>{money(p.employer_cost)}</b></td></tr>
        </>}
      </tbody>
    </table>
  );
}

export const PAYROLL_NOTE = "Simulation indicative selon les taux luxembourgeois usuels (barème 2025, cotisations plafonnées). Elle ne remplace pas la fiche officielle de la fiduciaire.";

/** Liste des fiches de paie avec téléchargements ; `onDelete` pour l'admin. */
export function PayslipList({ rows, onError, onDelete }) {
  if (rows.length === 0) return <p className="muted">Aucune fiche de paie pour le moment.</p>;
  const dl = (path, name) => download(path, name).catch((e) => onError(e.message));
  return (
    <table className="pay-calc">
      <tbody>
        {rows.map((r) => (
          <tr key={r.id}>
            <td><b>{frMonth(r.period)}</b><div className="muted">brut {euro(r.gross)} · classe {r.tax_class}</div></td>
            <td>Net <b>{money(r.net)}</b></td>
            <td>
              <button className="link" onClick={() => dl(`/payslips/${r.id}/pdf`, `fiche-de-paie-${r.period}.pdf`)}>Fiche de paie (PDF)</button>
              {r.filename && <button className="link" onClick={() => dl(`/payslips/${r.id}/file`, r.filename)}>Fiche officielle</button>}
              {onDelete && <button className="link danger" onClick={() => onDelete(r)}>Supprimer</button>}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

const currentMonth = () => new Date().toISOString().slice(0, 7);

/** Admin : établir la fiche de paie mensuelle d'un consultant. */
export default function Payslips({ consultant: c, onClose }) {
  const [rows, setRows] = useState([]);
  const [period, setPeriod] = useState(currentMonth);
  const [gross, setGross] = useState(c.monthly.salary);
  const [taxClass, setTaxClass] = useState(c.tax_class);
  const [sim, setSim] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const file = useRef(null);

  const load = useCallback(() => api(`/payslips/?consultant_id=${c.id}`).then(setRows).catch((e) => setError(e.message)), [c.id]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    const t = setTimeout(() => {
      api(`/payslips/simulate?gross=${Number(gross) || 0}&tax_class=${taxClass}`).then(setSim).catch((e) => setError(e.message));
    }, 250);
    return () => clearTimeout(t);
  }, [gross, taxClass]);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const f = file.current.files?.[0];
      const fields = { consultant_id: c.id, period, gross: Number(gross) || 0, tax_class: taxClass };
      if (f) await upload("/payslips/", f, "POST", fields);
      else {
        const form = new FormData();
        Object.entries(fields).forEach(([k, v]) => form.append(k, v));
        await api("/payslips/", { method: "POST", form });
      }
      file.current.value = "";
      setError(null);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };
  const remove = async (r) => {
    if (!window.confirm(`Supprimer la fiche de paie de ${frMonth(r.period)} ?`)) return;
    try { await api(`/payslips/${r.id}`, { method: "DELETE" }); await load(); } catch (err) { setError(err.message); }
  };
  const exists = rows.some((r) => r.period === period);

  return (
    <Modal title={`Fiches de paie · ${c.name}`} onClose={onClose}>
      <form className="grid-form" onSubmit={submit}>
        <Field label="Mois de paie"><input type="month" required value={period} onChange={(e) => setPeriod(e.target.value)} /></Field>
        <Field label="Salaire brut (€)">
          <input type="number" min="0" step="0.01" required value={gross} onChange={(e) => setGross(e.target.value)} />
          <small className="muted">Proposé : salaire mensuel du consultant ({euro(c.monthly.salary)})</small>
        </Field>
        <Field label="Classe d'impôt">
          <select value={taxClass} onChange={(e) => setTaxClass(e.target.value)}>
            {Object.entries(TAX_CLASSES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </Field>
        <Field label="Fiche officielle de la fiduciaire (PDF, facultatif)"><input ref={file} type="file" accept=".pdf" /></Field>
        <div className="wide">
          {sim && <PayrollTable p={sim} employer />}
          <small className="muted">{PAYROLL_NOTE}</small>
        </div>
        <Alert onClose={() => setError(null)}>{error}</Alert>
        <div className="form-actions wide">
          <button type="button" onClick={onClose}>Fermer</button>
          <button className="primary" disabled={busy}>{busy ? "Enregistrement…" : exists ? "Mettre à jour la fiche du mois" : "Établir la fiche de paie"}</button>
        </div>
      </form>
      <h2>Fiches établies</h2>
      <PayslipList rows={rows} onError={setError} onDelete={remove} />
    </Modal>
  );
}
