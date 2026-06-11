# AI Project State Explorer & Summarizer

An intelligent command-line utility that processes large conversational exports from major AI assistants (including Claude, ChatGPT, and Google Takeout Gemini). It leverages LLM APIs to distill chaotic chat histories into highly structured, actionable project tracking blueprints (`.md`).

This tool prevents development discontinuity by helping you immediately resume active programming workflows with clear context, milestones, and blockers.

## Features

- **Robust CLI & Interactive Modes:** Run fully automated via command-line flags (`argparse`), or fall back to an intuitive interactive terminal menu.
- **Deep Recursive Parsing:** Automatically bypasses structural noise, platform database metadata, timestamps, and long UUID strings to isolate real human dialog.
- **Google Takeout Normalization:** Automatically intercepts flat, disconnected Gemini prompt export objects and groups them chronologically by date into cohesive "sessions."
- **Multi-Backend Architecture:** Native support for `gemini-2.5-flash`, with an extensible dispatcher ready for OpenAI, Anthropic, or local Ollama integrations.
- **Anti-Overwrite Protection:** Generates unique, timestamped markdown files into customizable output directories to ensure historical records are preserved.

## Project State Architecture

The generated markdown states follow a strict blueprint optimized for developer handoffs or model context initialization:

- **# Project Overview** (Goals & Tech Stack)
- **# Current State** (Working Milestones & Known Blockers)
- **# Established Rules & Constraints** (Formatting Rules & Architectural Decisions)
- **# Next Immediate Task**

## Installation

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/YOUR_USERNAME/your-repo-name.git](https://github.com/YOUR_USERNAME/your-repo-name.git)
   cd your-repo-name

```

2. **Install the dependencies:**
Ensure you are using Python 3, then install the packages from the requirements file:
```bash
pip install -r requirements.txt

```


3. **Set your Environment Variable:**
The script requires your Gemini API key to operate.
* **Linux/macOS:** `export GEMINI_API_KEY="your_api_key_here"`
* **Windows (CMD):** `set GEMINI_API_KEY=your_api_key_here`
* **Windows (PowerShell):** `$env:GEMINI_API_KEY="your_api_key_here"`



## 💻 Usage

### 1. Interactive Mode

If you run the script without any arguments, it will automatically scan your directory for `.json` files and launch an interactive menu:

```bash
python summarizer.py

```

### 2. Command-Line (Headless) Mode

You can bypass the menus entirely by passing arguments directly. This is ideal for scripting or automation.

```bash
python summarizer.py --file my_export.json --output-dir ./project_states --provider gemini

```

**Available Flags:**

* `-f`, `--file` : Path to your target chat export JSON file.
* `-o`, `--output-dir` : Directory path to save the generated Markdown files (Defaults to `project_states`).
* `-p`, `--provider` : LLM backend choice (`gemini` [default], `openai`, `anthropic`, `ollama`).
* `-v`, `--version` : Displays the current script version.

## Supported Export Formats

* **Claude (.json):** Native support for `chat_messages` arrays.
* **ChatGPT (.json):** Native support for nested `mapping` node structures.
* **Google Takeout / Gemini (.json):** Specialized timeline interceptor to rebuild sessions from isolated prompt logs.
* **Generic LLM JSON:** Recursive fallback scraper that digs for generic `messages` or `content` keys.

## License

This project is licensed under the MIT License - see the [LICENSE](https://www.google.com/search?q=LICENSE) file for details.

