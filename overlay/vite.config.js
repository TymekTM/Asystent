import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path"; // Import path module
import fs from "fs";

// Plugin to copy settings.html after build
const copySettingsPlugin = () => ({
  name: "copy-settings",
  closeBundle() {
    const srcPath = path.resolve(__dirname, "src", "settings.html");
    const destPath = path.resolve(__dirname, "dist", "settings.html");

    if (fs.existsSync(srcPath)) {
      fs.copyFileSync(srcPath, destPath);
      console.log("settings.html copied to dist directory");
    } else {
      console.warn("settings.html not found in src directory");
    }
  },
});

// https://vitejs.dev/config/
export default defineConfig(async () => ({
  plugins: [react(), copySettingsPlugin()],
  root: "src", // Set the project root to the 'src' directory
  // Vite options tailored for Tauri development and only applied in `tauri dev` or `tauri build`
  // prevent vite from obscuring rust errors
  clearScreen: false,
  // tauri expects a fixed port, fail if that port is not available
  server: {
    port: 1420,
    strictPort: true,
    watch: {
      // 3. tell vite to ignore watching `src-tauri`
      ignored: ["**/src-tauri/**"],
    },
  },
  build: {
    // Output directory relative to the project root (f:\\Asystent\\overlay\\)
    outDir: "../dist",
    emptyOutDir: true,
  },
}));
