# Gaja Overlay

This Tauri application displays a small overlay indicating when Gaja is listening or speaking.

## Setup

1. Install dependencies:
   ```bash
   cd overlay
   npm install
   cargo install tauri-cli
   ```

2. Run in development:
   ```bash
   npm run tauri dev
   ```

   The overlay polls the web server at `http://localhost:5001` by default. Set the `GAJA_PORT` environment variable to override the port (use `5000` for packaged builds):
   ```bash
   GAJA_PORT=5000 npm run tauri dev
   ```

3. Build for production:
   ```bash
   npm run tauri build
   ```

The overlay reacts to the `is_listening`, `is_speaking` and `text` fields provided by the `/api/status` endpoint and uses the shared `gaja-branding.css` for styling.
