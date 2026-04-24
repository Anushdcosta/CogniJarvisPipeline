# CogniJarvisPipeline

CogniJarvisPipeline is a Raspberry Pi voice assistant integration project built around a local web dashboard. The repository contains the core voice assistant server, dashboard update helpers, and startup scripts that link the web UI with the audio/voice pipeline and Bluetooth support.

## Overview

This project is not a generic template README. It is based on the actual website/dashboard-driven flow used by CogniJarvis:

- A web dashboard served on `http://127.0.0.1:5173`
- A Flask-based assistant backend exposing `/api/speak` and `/api/ask`
- Scripts that wait for the dashboard to be ready before launching Jarvis
- Local dashboard updates sent to `http://127.0.0.1:5001/api/trigger`

## Key components

- `Cogni_pipeline.py` - Main Jarvis voice assistant backend
  - Runs a Flask server on port `5002`
  - Offers `POST /api/speak` to speak text
  - Offers `GET /api/ask` to listen for user speech and transcribe it
  - Updates the running dashboard with status and message text

- `Bluetooth_pipeline.py` - Simple local API tester for the dashboard trigger endpoint

- `run_jarvisinput.sh` - Startup helper that waits for the web dashboard at `http://127.0.0.1:5173` then runs `Cogni_pipeline.py`

- `run_assitant.sh` - Dashboard startup helper for the Pi
  - launches the Jarvis shield animation
  - starts the web dashboard via `npm run dev`
  - waits for the dashboard port to become available

- `run_bluetooth.sh` - Bluetooth startup helper that initializes the environment and runs `Bluetooth_pipeline.py`

## Shell helper scripts

These shell scripts support the website-driven startup flow:

- `run_jarvisinput.sh`
  - waits for the dashboard at `http://127.0.0.1:5173`
  - then starts the Jarvis backend (`Cogni_pipeline.py`)
  - logs startup progress to `jarvis_startup.log`

- `run_assitant.sh`
  - starts a boot/shield animation on the Pi
  - launches the dashboard frontend
  - waits for port `5173` before dropping the shield

- `run_bluetooth.sh`
  - sleeps while Bluetooth hardware initializes
  - sets the PATH for `bluetoothctl` and `uv`
  - runs `Bluetooth_pipeline.py` to start Bluetooth-related services

## Website / Dashboard integration

The repository assumes a local dashboard application is running at:

- `http://127.0.0.1:5173`

The assistant backend sends status and message updates to the dashboard through the trigger API at:

- `http://127.0.0.1:5001/api/trigger`

This makes the web dashboard the central user interface, with `Cogni_pipeline.py` providing the voice assistant logic behind it.

## Installation

1. Install Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Ensure the dashboard app is available and serves on `http://127.0.0.1:5173`.
3. Confirm the required resources exist:
   - `resources/Jarvis_en_raspberry-pi_v4_0_0.ppn`
   - `resources/en_US-amy-medium.onnx`

4. Update any hard-coded URLs or access keys if needed:
   - `WAKE_WORD_PATH` in `Cogni_pipeline.py`
   - `N8N_WEBHOOK_URL` in `Cogni_pipeline.py`
   - Dashboard trigger endpoint at `http://127.0.0.1:5001/api/trigger`

## Running the project

### Start the web frontend on the Pi

Use:

```bash
./run_assitant.sh
```

This script:
- starts the Jarvis shield animation
- starts the dashboard with `npm run dev`
- waits until port `5173` is live
### Launch Jarvis with the dashboard

Use the helper script:

```bash
./run_jarvisinput.sh
```

This script:
- waits for the dashboard at `http://127.0.0.1:5173`
- starts the Jarvis backend via `Cogni_pipeline.py`

### Launch Bluetooth Backend

Use the helper script:

```bash
./run_bluetooth.sh
```

This script:
- waits for Bluetooth hardware to initialize
- exports the path for `bluetoothctl` and `uv`
- runs `Bluetooth_pipeline.py` for Bluetooth-related startup

## API Endpoints

- `POST /api/speak`
  - Request JSON: `{ "text": "Hello Jarvis" }`
  - Response: triggers speech synthesis

- `GET /api/ask`
  - Listens for user speech
  - Transcribes audio and returns recognized text

## Notes

- The repository is designed around the website/dashboard workflow rather than a static template.
- Local endpoints and ports are hard-coded for the current setup and may need adjustment for different environments.
- This README is intended to reflect the actual web-driven launch process used by the project.
