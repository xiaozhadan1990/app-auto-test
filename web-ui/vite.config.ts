import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const envLocal = loadEnv(mode, ".", "");
  const envRoot = loadEnv(mode, "..", "");
  const backendHost = envLocal.DESKTOP_WEB_HOST || envRoot.DESKTOP_WEB_HOST || "127.0.0.1";
  const backendPort = envLocal.DESKTOP_WEB_PORT || envRoot.DESKTOP_WEB_PORT || "17999";
  const apiProxyTarget =
    envLocal.VITE_API_PROXY_TARGET ||
    envRoot.VITE_API_PROXY_TARGET ||
    `http://${backendHost}:${backendPort}`;

  return {
    plugins: [react()],
    server: {
      host: "127.0.0.1",
      port: 5173,
      proxy: {
        "/api": {
          target: apiProxyTarget,
          changeOrigin: true,
        },
      },
    },
    preview: {
      host: "127.0.0.1",
      port: 4173,
    },
    build: {
      outDir: "../ui",
      emptyOutDir: true,
    },
  };
});
