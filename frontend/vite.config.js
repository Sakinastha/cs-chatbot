// vite.config.js
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // any request to /api, /ingest, /clear-index, /chat will forward to port 5000
      "/api": "http://localhost:5000",
      "/ingest": "http://localhost:5000",
      "/clear-index": "http://localhost:5000",
      "/chat": "http://localhost:5000",
    },
  },
});
