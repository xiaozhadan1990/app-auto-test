import { defineConfig, splitVendorChunkPlugin } from "vite";
import react from "@vitejs/plugin-react";

function getVendorChunkName(id: string): string | undefined {
  if (
    id.includes("/react/") ||
    id.includes("/react-dom/") ||
    id.includes("/scheduler/") ||
    id.includes("/use-sync-external-store/")
  ) {
    return "react-vendor";
  }

  if (
    id.includes("/antd/") ||
    id.includes("/@ant-design/") ||
    id.includes("/rc-") ||
    id.includes("/@rc-component/")
  ) {
    return "antd-vendor";
  }

  return undefined;
}

export default defineConfig({
  plugins: [react(), splitVendorChunkPlugin()],
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
