import React, { useState } from "react";
import { ROLES } from "../api.js";
import { PasswordForm } from "./forms.jsx";

export default function Header({ user, onLogout }) {
  const [pwd, setPwd] = useState(false);
  return (
    <header>
      <div className="logo">Cloud<span>Talent</span></div>
      <div className="subtitle">Cloud & DevOps Talent Platform</div>
      {user && (
        <div className="session">
          <span>{user.email} · <b>{ROLES[user.role]}</b></span>
          <button className="link" onClick={() => setPwd(true)}>Mot de passe</button>
          <button className="link" onClick={onLogout}>Déconnexion</button>
        </div>
      )}
      {pwd && <PasswordForm onClose={() => setPwd(false)} onSaved={() => setPwd(false)} />}
    </header>
  );
}
