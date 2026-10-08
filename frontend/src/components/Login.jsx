import React, { useState } from "react";
import { api, setToken, ROLES } from "../api.js";
import { Alert, Field } from "./ui.jsx";
import Header from "./Header.jsx";

const stroke = { fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round" };

/** Les trois espaces proposés à l'accueil, chacun lié à un rôle. */
const SPACES = [
  {
    role: "admin", title: "Administrateur", text: "Consultants, entreprises, missions, matching et comptes.",
    icon: <svg viewBox="0 0 24 24" {...stroke}><path d="M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6z" /><path d="M9 12l2 2 4-4" /></svg>,
  },
  {
    role: "consultant", title: "Consultant", text: "Ma mission, mon salaire, ma réserve et mon CV.",
    icon: <svg viewBox="0 0 24 24" {...stroke}><circle cx="12" cy="8" r="4" /><path d="M4 21c0-4 3.6-7 8-7s8 3 8 7" /></svg>,
  },
  {
    role: "company", title: "Entreprise partenaire", text: "Ma fiche entreprise et mes postes à pourvoir.",
    icon: <svg viewBox="0 0 24 24" {...stroke}><path d="M4 21V5a1 1 0 011-1h9a1 1 0 011 1v16" /><path d="M15 9h4a1 1 0 011 1v11" /><path d="M3 21h18" /><path d="M8 8h3M8 12h3M8 16h3" /></svg>,
  },
];

/** Accueil : choix de l'espace (icônes), puis connexion à cet espace. */
export default function Login({ onLogin }) {
  const [space, setSpace] = useState(null);
  return (
    <div className="app">
      <Header />
      <main>
        {space ? <LoginForm space={space} onBack={() => setSpace(null)} onLogin={onLogin} /> : (
          <section className="portal">
            <h1>Choisissez votre espace</h1>
            <div className="portal-grid">
              {SPACES.map((s) => (
                <button key={s.role} className="card portal-card" onClick={() => setSpace(s)}>
                  <span className={`portal-icon i-${s.role}`}>{s.icon}</span>
                  <b>{s.title}</b>
                  <span>{s.text}</span>
                </button>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

function LoginForm({ space, onBack, onLogin }) {
  const [v, setV] = useState({ email: "", password: "" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setV({ ...v, [k]: e.target.value });
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const r = await api("/auth/login", { method: "POST", body: { email: v.email.trim(), password: v.password } });
      // Le jeton n'est gardé que si le compte correspond à l'espace choisi
      if (r.user.role !== space.role) {
        setError(`Ce compte n'a pas accès à l'espace ${space.title}. Choisissez l'espace ${ROLES[r.user.role]}.`);
        return;
      }
      setToken(r.access_token);
      onLogin(r.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <form className="card login" onSubmit={submit}>
      <button type="button" className="link back" onClick={onBack}>← Changer d'espace</button>
      <div className="login-head">
        <span className={`portal-icon i-${space.role}`}>{space.icon}</span>
        <h1>{space.title}</h1>
      </div>
      <Field label="Email"><input type="email" required autoFocus autoComplete="username" value={v.email} onChange={set("email")} /></Field>
      <Field label="Mot de passe"><input type="password" required autoComplete="current-password" value={v.password} onChange={set("password")} /></Field>
      <Alert onClose={() => setError(null)}>{error}</Alert>
      <button className="primary" disabled={busy}>{busy ? "Connexion…" : "Se connecter"}</button>
    </form>
  );
}
