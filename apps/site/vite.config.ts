import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist",
    sourcemap: false,
    cssCodeSplit: true,
    target: "es2022",
    rollupOptions: {
      output: {
        manualChunks: {
          motion: ["motion/react"],
        },
      },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    exclude: ["e2e/**", "node_modules/**", "dist/**"],
    css: true,
    clearMocks: true,
  },
});
