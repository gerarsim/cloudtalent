import React, { useState } from "react";
import { api, setToken } from "../api.js";
import { Alert, Field } from "./ui.jsx";
import Header from "./Header.jsx";

export default function Login({ onLogin }) {
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
      setToken(r.access_token);
      onLogin(r.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="app">
      <Header />
      <main>
        <form className="card login" onSubmit={submit}>
          <h1>Connexion</h1>
          <Field label="Email"><input type="email" required autoFocus autoComplete="username" value={v.email} onChange={set("email")} /></Field>
          <Field label="Mot de passe"><input type="password" required autoComplete="current-password" value={v.password} onChange={set("password")} /></Field>
          <Alert onClose={() => setError(null)}>{error}</Alert>
          <button className="primary" disabled={busy}>{busy ? "Connexion…" : "Se connecter"}</button>
        </form>
      </main>
    </div>
  );
}
