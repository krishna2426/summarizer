# AI Project State Explorer & Summarizer

> A command-line utility that converts messy AI chat exports into clean, structured project-state Markdown files — so you never lose development context again.

Supports exports from **Claude**, **ChatGPT**, and **Google Takeout (Gemini)**. Powered by `gemini-2.5-flash` with a pluggable backend architecture ready for OpenAI, Anthropic, and Ollama.

---

## Features

- **CLI & Interactive Modes** — Run headless via flags for automation, or use the guided terminal menu with no arguments.
- **Deep Recursive Parsing** — Strips UUIDs, timestamps, image markers, and platform metadata to isolate real human dialogue.
- **Google Takeout Normalization** — Rebuilds flat, disconnected Gemini prompt exports into chronological sessions.
- **Multi-Format Support** — Auto-detects ChatGPT node-graph, Claude flat array, generic `messages`, and legacy `history` schemas.
- **Multi-Backend Architecture** — Native Gemini support with stubs ready for OpenAI, Anthropic, and Ollama.
- **Anti-Overwrite Protection** — Timestamped output filenames written into a configurable directory.

---

## Generated Output Structure

Every state file follows this strict blueprint, optimized for developer handoffs and model context initialization:

```
# Project Overview
* Goal / Tech Stack

# Current State
* Working Milestones / Known Blockers

# Established Rules & Constraints
* Formatting Rules / Architectural Decisions

# Next Immediate Task
```

---

## Requirements

- Python **3.8+**
- A valid **Gemini API key** (free tier works)

---

## Installation

**1. Clone the repository:**
```bash
git clone https://github.com/krishna2426/summarizer.git
cd summarizer
```

**2. Install dependencies:**
```bash
pip install -r requirements.txt
```

**3. Set your API key as an environment variable:**

| Platform | Command |
|---|---|
| Linux / macOS | `export GEMINI_API_KEY="your_api_key_here"` |
| Windows (CMD) | `set GEMINI_API_KEY=your_api_key_here` |
| Windows (PowerShell) | `$env:GEMINI_API_KEY="your_api_key_here"` |

---

## Usage

### Interactive Mode

Run without arguments to scan your directory for `.json` files and launch the guided menu:

```bash
python summarizer.py
```

You'll be prompted to:
1. Select a detected JSON file (or enter a custom path)
2. Browse recent chats or search by keyword
3. Pick a conversation to summarize

The output is saved automatically to the `project_states/` directory.

---

### CLI / Headless Mode

Pass flags directly to skip all menus — useful for scripting and automation:

```bash
python summarizer.py --file my_export.json --output-dir ./states --provider gemini
```

**Available flags:**

| Flag | Short | Description | Default |
|---|---|---|---|
| `--file` | `-f` | Path to the chat export JSON | *(interactive)* |
| `--output-dir` | `-o` | Directory for generated Markdown files | `project_states` |
| `--provider` | `-p` | LLM backend: `gemini`, `openai`, `anthropic`, `ollama` | `gemini` |
| `--version` | `-v` | Print the current version and exit | — |

---

## Supported Export Formats

| Platform | Format | Key |
|---|---|---|
| **Claude** | Flat message array | `chat_messages` + `sender` / `text` |
| **ChatGPT** | Node graph | `mapping` + `author.role` / `content.parts` |
| **Google Takeout (Gemini)** | Flat prompt objects | Grouped by `time` into date sessions |
| **Generic / Legacy** | Standard array | `messages` + `role` / `content` |
| **Legacy History** | History array | `history` + `author_role` / `text_body` |

---

## Adding a New LLM Backend

The `call_llm_backend()` function in `summarizer.py` is designed to be extended. To add a new provider:

1. Uncomment the relevant package in `requirements.txt` and install it
2. Add an `elif provider.lower() == "yourprovider":` branch in `call_llm_backend()`
3. Pass `--provider yourprovider` at runtime

---

## Architecture Evolution

| Version | Changes |
|---|---|
| v1–v3 | Deep nesting resolution, image payload filtering, UUID rejection |
| v4 | Dynamic filesystem scanning |
| v5 | Google Takeout timeline grouping, timestamped file preservation |
| v1.2.0 | `argparse` CLI, `--output-dir`, multi-backend dispatcher, improved Takeout detection |
| **v1.3.0** | Cached Gemini client, restored `history` format, fixed `%(prog)s`, prompt formatting fix, `'q'`/`'b'` navigation, custom path retry loop |

---

## License

This project is licensed under the [MIT License](LICENSE).