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

export async function api(path, { method = "GET", body } = {}) {
  let res;
  try {
    res = await fetch(BASE + path, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error("API injoignable. Le backend est-il démarré ?");
  }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(errorMessage(res.status, data));
  return data;
}

export const LEVELS = { 1: "Notions", 2: "Junior", 3: "Autonome", 4: "Confirmé", 5: "Expert" };
export const CONSULTANT_STATUSES = ["Freelance", "Portage", "CDI", "Salarié"];
export const MISSION_STATUSES = ["Ouverte", "Pourvue", "Fermée"];
export const TRAINING_LEVELS = ["Débutant", "Intermédiaire", "Avancé"];

// "" -> null pour les champs optionnels (l'API refuse un email vide, une date vide…)
export const orNull = (v) => (v === "" || v === undefined ? null : v);
export const euro = (n) => (n ? `${Number(n).toLocaleString("fr-FR")} €` : "—");
export const frDate = (d) => (d ? new Date(d + "T00:00:00").toLocaleDateString("fr-FR") : "—");
