// URL relative : en dev le proxy Vite relaie /api vers le backend.
// En prod, définir VITE_API_URL (ex. https://api.cloudtalent.lu/api) au build.
const BASE = import.meta.env.VITE_API_URL || "/api";

function errorMessage(status, body) {
  const d = body?.detail;
  if (Array.isArray(d)) {
    // Erreurs de validation FastAPI : [{loc: ["body","tjm"], msg: "..."}]
    return d.map((e) => `${e.loc.filter((x) => x !== "body").join(".")} : ${e.msg}`).join(" · ");
  }
  if (typeof d === "string") return d;
  return `Erreur ${status}`;
}

// Jeton de session (localStorage peut être indisponible : navigation privée…)
const TOKEN_KEY = "cloudtalent.token";
let token = null;
try { token = localStorage.getItem(TOKEN_KEY); } catch { /* ignoré */ }

export function setToken(t) {
  token = t;
  try { t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY); } catch { /* ignoré */ }
}
export const hasToken = () => Boolean(token);

// Appelé quand l'API répond 401 (jeton expiré, compte désactivé) : retour à l'écran de connexion
let onUnauthorized = () => {};
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn; };

async function send(path, { method = "GET", body, form } = {}) {
  const headers = {};
  if (body) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;
  let res;
  try {
    res = await fetch(BASE + path, { method, headers, body: form ?? (body ? JSON.stringify(body) : undefined) });
  } catch {
    throw new Error("API injoignable. Le backend est-il démarré ?");
  }
  if (res.status === 401 && token) {
    setToken(null);
    onUnauthorized();
  }
  if (!res.ok) throw new Error(errorMessage(res.status, await res.json().catch(() => null)));
  return res;
}

export async function api(path, opts) {
  const res = await send(path, opts);
  return res.status === 204 ? null : res.json().catch(() => null);
}

/** Envoi d'un fichier (multipart, champ `file`). */
export const upload = (path, file, method = "PUT") => {
  const form = new FormData();
  form.append("file", file);
  return api(path, { method, form });
};

/** Téléchargement authentifié : le jeton ne passe pas dans un simple lien <a href>. */
export async function download(path, filename) {
  const blob = await (await send(path)).blob();
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement("a"), { href: url, download: filename });
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export const LEVELS = { 1: "Notions", 2: "Junior", 3: "Autonome", 4: "Confirmé", 5: "Expert" };
export const CONSULTANT_STATUSES = ["Freelance", "Portage", "CDI", "Salarié"];
export const MISSION_STATUSES = ["Ouverte", "Pourvue", "Fermée"];
export const ROLES = { admin: "Administrateur", consultant: "Consultant", company: "Entreprise partenaire" };
export const TRAINING_LEVELS = ["Débutant", "Intermédiaire", "Avancé"];

// "" -> null pour les champs optionnels (l'API refuse un email vide, une date vide…)
export const orNull = (v) => (v === "" || v === undefined ? null : v);
export const euro = (n) => (n ? `${Number(n).toLocaleString("fr-FR")} €` : "—");
export const fileSize = (n) => (n >= 1024 * 1024 ? `${(n / 1024 / 1024).toFixed(1)} Mo` : `${Math.ceil(n / 1024)} Ko`);
export const frDate = (d) => (d ? new Date(d + "T00:00:00").toLocaleDateString("fr-FR") : "—");
