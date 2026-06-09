import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(async () => ({
  plugins: [react(), tailwindcss()],
  clearScreen: false,
  server: {
    port: 5173,
    strictPort: true,
    watch: {
      ignored: ["**/src-tauri/**"],
    },
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8765",
      },
    },
  },
  envPrefix: ["VITE_", "TAURI_ENV_*"],
  build: {
    target: "chrome105",
    minify: !process.env.TAURI_ENV_DEBUG ? "esbuild" : false,
    sourcemap: !!process.env.TAURI_ENV_DEBUG,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) return undefined;

          if (
            id.includes("react-dom") ||
            id.includes("react/") ||
            id.includes("scheduler") ||
            id.includes("use-sync-external-store")
          ) {
            return "react-core";
          }
          if (id.includes("react-konva") || id.includes("konva")) return "canvas";
          if (id.includes("@radix-ui")) return "radix-ui";
          if (id.includes("lucide-react")) return "icons";
          if (id.includes("@tauri-apps")) return "tauri";
          if (id.includes("zustand")) return "state";

          return "vendor";
        },
      },
    },
  },
}));
