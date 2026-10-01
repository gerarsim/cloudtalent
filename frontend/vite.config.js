import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Le navigateur appelle /api sur la même origine ; Vite relaie vers le backend.
// En Docker : API_PROXY_TARGET=http://backend:8000 (voir docker-compose.yml).
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": { target: process.env.API_PROXY_TARGET || "http://localhost:8000", changeOrigin: true },
    },
  },
});
