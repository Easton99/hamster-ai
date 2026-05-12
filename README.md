# Hamster AI

> A lightweight, local-first AI companion for Windows.  
> Runs entirely on your PC. No cloud. No subscriptions. No data leaving your machine.

Hamster AI sits quietly in your system tray and helps you think, remember things, set reminders, and keep track of your day — without ever phoning home.

---

## Features

- **Fully offline** — powered by [Ollama](https://ollama.com); all inference runs on your hardware
- **System tray companion** — always available, never in the way
- **Mini widget** — a small always-on-top input bar for quick questions without opening the main chat
- **Mini response popups** — replies appear as small floating windows above the widget; missed ones are waiting when you open chat
- **Memory system** — remembers facts, notes, and todos across sessions using a local SQLite database
- **Reminders** — natural-language reminders (`/remind me at 6pm to check the build`)
- **Mode system** — Work, Focus, Private, and Game-Safe modes suppress notifications and tracking
- **Global hotkey** — open chat from anywhere (`Ctrl+Shift+H` by default)
- **Plugin system** — optional features load at startup; enable only what you need
- **Diagnostics** — built-in health checks with fix suggestions

---

## Screenshots

*Coming soon.*

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Windows 10 or 11 | 64-bit |
| Python 3.11+ | [python.org](https://www.python.org/downloads/) |
| [Ollama](https://ollama.com) | Must be running before launching Hamster AI |
| An Ollama model | `ollama pull llama3.2:3b` is a good starting point |

---

## Quick Start

### 1. Clone the repository

```powershell
git clone https://github.com/your-username/hamster-ai.git
cd hamster-ai
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Pull an Ollama model

```powershell
ollama pull llama3.2:3b
```

Any model works. Smaller models use less RAM and respond faster.

### 5. Start Ollama

```powershell
ollama serve
```

Keep this running in the background (or configure Ollama to start with Windows).

### 6. Run Hamster AI

```powershell
python app/main.py
```

A hamster icon will appear in your system tray. Right-click it to open the menu, or double-click to open chat.

---

## Commands

Type `/help` in the chat window for the full list. Common ones:

| Command | What it does |
|---|---|
| `/status` | Show app status |
| `/health` | Run health checks |
| `/remember <text>` | Save a memory |
| `/todo <task>` | Add a todo |
| `/note <text>` | Save a note |
| `/show-memories` | List saved memories |
| `/search-memory <word>` | Search memories |
| `/focus 30` | Start Focus Mode for 30 minutes |
| `/remind me at 6pm to ...` | Set a reminder |
| `/system` | Show a system stats snapshot |
| `/processes` | List running processes |
| `/forget-today` | Clear today's session data |

---

## Plugins

Enable or disable plugins via **right-click tray → Plugins**.

| Plugin | What it does | Extra deps needed |
|---|---|---|
| Session Awareness | Detects what you're doing (coding, gaming, browsing) | — |
| Insights | End-of-day and weekly summaries | — |
| Scheduled Reminders | Time-based reminders | — |
| Extended System Stats | GPU, per-process CPU/RAM, disk, network | `GPUtil pywin32 wmi` |
| Hardware Awareness | Monitors, USB, battery, internet status | `pywin32 wmi` |
| Process Awareness | Running processes, internet apps, startup programs | — |
| Audio Awareness | Detects whether audio is playing before interrupting | `pycaw` |
| Voice Output | Speaks replies using Windows SAPI (local TTS) | `pyttsx3` |
| Discord Translation | Transcribes system audio locally using Whisper | `PyAudioWPatch faster-whisper webrtcvad numpy` |

Optional dependencies can be installed all at once:

```powershell
# Audio plugins
pip install pyttsx3 PyAudioWPatch faster-whisper webrtcvad numpy pycaw

# Hardware/stats plugins
pip install GPUtil pywin32 wmi
```

---

## Settings

Right-click tray icon → **Settings**

- **General** — model, Ollama URL, startup behaviour, hotkey, timestamps in chat
- **Appearance** — theme (Light / Dark / High Contrast), mini widget corner and position
- **Modes** — configure Work, Focus, Private, and Game-Safe mode behaviour
- **Notifications** — notification history, reminder alerts

---

## Building a Standalone Executable

```powershell
pip install pyinstaller
pyinstaller build\hamster_ai.spec
```

Output: `dist\HamsterAI\HamsterAI.exe`

Ollama still needs to be running separately.

---

## Privacy

Hamster AI is built around a simple principle: **your data stays on your machine.**

- No telemetry, no analytics, no crash reporting to any server
- No screenshots are ever taken
- Audio capture (Discord Translation plugin) only runs when you explicitly start it; audio is never saved to disk
- Work Mode and Private Mode disable all tracking and notifications while active
- All memories, notes, todos, and reminders live in `data/hamster_ai.db` on your PC — delete the file to wipe everything

---

## Troubleshooting

**"Ollama is not running"**  
Run `ollama serve` in a terminal and keep it open, or install Ollama as a Windows service.

**No models available in the model switcher**  
Pull at least one model: `ollama pull llama3.2:3b`

**Tray icon does not appear**  
Check `data/logs/hamster_ai.log` for errors. Run Diagnostics from the tray menu.

**Global hotkey not working**  
Another application may have registered the same shortcut. Change it in Settings → General.

**Plugin shows as "failed to load"**  
Open Diagnostics from the tray menu for details. Usually a missing optional dependency — see the plugin table above.

---

## Licence

Personal project — all rights reserved. You are welcome to read the code and learn from it.  
If you'd like to contribute or use it in your own project, get in touch first.
