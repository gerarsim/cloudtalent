import React, { useEffect } from "react";
import { LEVELS } from "../api.js";

export function Modal({ title, onClose, children }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-label={title}>
        <div className="modal-head">
          <h2>{title}</h2>
          <button className="icon" onClick={onClose} aria-label="Fermer">×</button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Field({ label, children, wide }) {
  return (
    <label className={wide ? "field wide" : "field"}>
      <span>{label}</span>
      {children}
    </label>
  );
}

export function Alert({ children, onClose }) {
  if (!children) return null;
  return (
    <div className="alert" role="alert">
      <span>{children}</span>
      {onClose && <button className="icon" onClick={onClose} aria-label="Fermer">×</button>}
    </div>
  );
}

export function Page({ title, onAdd, children }) {
  return (
    <section>
      <div className="titlebar">
        <h1>{title}</h1>
        {onAdd && <button className="primary" onClick={onAdd}>+ Ajouter</button>}
      </div>
      {children}
    </section>
  );
}

/** columns: [{key, label, render?}] — rows doivent avoir un `id`. */
export function Table({ columns, rows, actions, empty = "Aucun élément" }) {
  return (
    <div className="tablewrap">
      <table>
        <thead>
          <tr>
            {columns.map((c) => <th key={c.key}>{c.label}</th>)}
            {actions && <th className="actions-col" />}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr><td className="empty" colSpan={columns.length + (actions ? 1 : 0)}>{empty}</td></tr>
          )}
          {rows.map((r) => (
            <tr key={r.id}>
              {columns.map((c) => <td key={c.key}>{c.render ? c.render(r) : r[c.key]}</td>)}
              {actions && <td className="actions">{actions(r)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function SkillChips({ items }) {
  return (
    <div className="chips">
      {items.map((s) => (
        <span key={s.skill.id} className={"chip" + (s.required === false ? " optional" : "")}
              title={s.level ? LEVELS[s.level] : `Niveau min. ${LEVELS[s.min_level]}${s.required ? "" : " (souhaitée)"}`}>
          {s.skill.name}
          <small>{s.level ?? s.min_level}</small>
        </span>
      ))}
    </div>
  );
}

const INVOICE_CLASS = { "Déposée": "s-deposee", "Paiement demandé": "s-demande", "À régler": "s-demande", "Payée": "s-payee" };
export function InvoiceStatus({ status }) {
  return <span className={`status ${INVOICE_CLASS[status] ?? ""}`}>{status}</span>;
}
