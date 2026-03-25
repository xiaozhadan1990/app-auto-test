import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

function getPackageName(id: string): string | undefined {
  const nodeModulesIndex = id.lastIndexOf("/node_modules/");
  if (nodeModulesIndex === -1) return undefined;

  const modulePath = id.slice(nodeModulesIndex + "/node_modules/".length);
  const segments = modulePath.split("/");
  if (segments.length === 0) return undefined;

  if (segments[0].startsWith("@") && segments.length > 1) {
    return `${segments[0]}/${segments[1]}`;
  }
  return segments[0];
}

function getVendorChunkName(id: string): string | undefined {
  const packageName = getPackageName(id);
  if (!packageName) {
    return undefined;
  }

  if (
    [
      "react",
      "react-dom",
      "scheduler",
      "use-sync-external-store",
    ].includes(packageName)
  ) {
    return "react-vendor";
  }
  return undefined;
}

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          return getVendorChunkName(id);
        },
      },
    },
  },
});
