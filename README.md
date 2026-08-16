<p align="center">
  <img src="./.github/readme-assets/blueprint.gif" alt="Animated blueprint / system visual for VoiceForge-AI" width="100%" />
</p>

<h1 align="center">VoiceForge-AI</h1>

<p align="center"><strong>VoiceForge-AI is a Python-based bilingual (Hindi/English) desktop voice assistant designed to provide full PC automation: speech→NLP→automation with a PyQt6 UI. The dossier contains a README, a main entrypoint (main.py), core modules for speech, NLP, automation, and the voice engine. Several referenced utilities/UI modules and tests are not present in the supplied files.</strong></p>

<p align="center"><code>REPO//SIGNAL</code> · <code>BLUEPRINT / SYSTEM</code> · <code>LOOPING README EXPERIENCE</code></p>

## Live signal

| Lens | Readout |
| --- | --- |
| Portfolio lane | **BLUEPRINT / SYSTEM** |
| Code surface | **9** tracked files observed |
| Primary materials | **Python, Markdown** |
| Verification | **0** test-related files observed |

> A structural view of the project machinery. The animated frame above is a lightweight visual signature; the sections below remain the source of truth for implementation details.

## Motion map

`INGEST` → `COMPOSE` → `SHIP`

Trace the repository from inputs and dependencies through its core modules to the delivered surface. Keep configuration explicit, make failure states observable, and add verification around the highest-value paths.

<details open>
<summary><strong>Open the full project dossier</strong></summary>

> VoiceForge-AI is a Python-based bilingual (Hindi/English) desktop voice assistant designed to provide full PC automation: speech→NLP→automation with a PyQt6 UI. The dossier contains a README, a main entrypoint (main.py), core modules for speech, NLP, automation, and the voice engine. Several referenced utilities/UI modules and tests are not present in the supplied files.

## Overview

Listens to microphone input, converts audio to text (SpeechRecognizer), extracts intents/entities (NLPProcessor), and executes actions on Windows via UI automation and Win32 APIs (AutomationEngine). It aims to support multi-step workflows, offline mode (Whisper), GPT-based intent resolution, and a PyQt6 GUI for feedback.

## Key capabilities

- Bilingual speech recognition (Hindi/English) with offline Whisper option
- GPT/OpenAI integration for intent understanding (configurable via API key)
- Rule-based regex intent patterns as fallback
- Windows automation via Win32 APIs and PyAutoGUI
- PyQt6 GUI integration and a threaded asyncio processing loop
- Configuration-driven safe mode / confirmation flags
- Template matching/OCR and YOLO referenced for UI element detection (computer vision)

## Technology

- Python 3.9+
- PyQt6 (GUI)
- speech_recognition, pyaudio (audio capture)
- whisper (offline ASR), OpenAI API (online NLP)
- spaCy (NLP)
- transformers
- opencv-python, pytesseract, pyautogui (CV & automation)
- win32api/win32gui/win32process (Windows integration)
- psutil, subprocess, numpy, scipy
- pytest/pytest-asyncio (testing listed)
- redis, pandas, requests (data/IO listed)

## Repository structure

The following top-level files and directories were observed in the repository:

- `README.md`
- `automation_engine.py`
- `infinity-hackathon-overview.md`
- `main.py`
- `nlp_processor.py`
- `requirements.txt`
- `script.py`
- `speech_recognition.py`
- `voice_engine.py`

## Getting started

Create and activate a virtual environment, then install the declared dependencies.

```bash
python -m venv .venv
# Activate the environment using your platform's standard command.
pip install -r requirements.txt
```

Inspect the repository entry point and configuration files before running the application, as the audited files do not establish a single universal launch command.

## Configuration

Component-based: Audio Input → Speech Engine (speech_recognition.py) → NLP Engine (nlp_processor.py) → Automation Engine (automation_engine.py) with a PyQt6 UI (referenced in main.py). main.py spawns a QThread (VoiceEngineThread) that runs an asyncio loop calling VoiceEngine.process_next_command (voice_engine.py), and coordinates UI updates via Qt signals. Configuration and logger utilities are referenced (ConfigManager, setup_logger) but their implementations are not included in the supplied dossier.

## Development and quality notes

- No dedicated test files were identified in the audited tree.
- No continuous-integration configuration was identified during the audit.

### Current improvement opportunities

- Add missing utility and UI modules referenced by main.py: src/utils/config_manager.py, src/utils/logger.py, src/ui/main_window.py — minimally stubbed so app can initialize.
- Move secrets out of repo: load OpenAI API key from environment variables (os.environ or python-dotenv) and document in README. Add config/settings.example.json (README references creating one) if not present.
- Add a .gitignore and remove any sensitive files; add instructions for secure key setup in README.
- Introduce a command whitelist and require explicit confirmation for actions classified as destructive (uninstall/delete/format). Enforce ConfigManager.safe_mode and confirmation_required in AutomationEngine execution paths.
- Add basic unit tests for pure logic in NLPProcessor intent regexes and for AutomationEngine helper methods; create tests/test_nlp_processor.py and tests/test_automation_engine.py with mocks for pyautogui/win32.
- Add CI (GitHub Actions) that runs linting (flake8/black) and pytest on push to catch regressions early.
- Add defensive checks around subprocess usage (use subprocess.run with shell=False / explicit argument lists) and limit commands executed by the automation database to known safe commands.

## Contributing

Before submitting changes, keep the implementation aligned with the existing project structure, add or update relevant tests where the project supports them, and describe any configuration changes in the pull request.

</details>

---

<p align="center"><sub>README motion system · visual layer by RepoSignal · implementation details remain project-specific</sub></p>
