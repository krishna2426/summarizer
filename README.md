# AI Project State Explorer & Summarizer

An intelligent command-line utility that processes large conversational exports from major AI assistants (including Claude, ChatGPT, and Google Takeout Gemini) and leverages the Gemini API to distill them into structured project tracking blueprints (`.md`).

This tool prevents development discontinuity by helping you immediately resume active programming workflows with clear context, milestones, and blockers.

## Features

- **Deep Recursive Parsing:** Automatically bypasses structural noise, platform database metadata, timestamps, and long UUID strings to isolate real human dialog.
- **Google Takeout Normalization:** Automatically intercepts flat, disconnected Gemini prompt export objects, groups them chronologically by date into cohesive "sessions," and enables the AI to reverse-engineer project states purely from your inputs.
- **Dynamic File Discovery:** Scans your working directory automatically for available `.json` files, offering an interactive list-based CLI selection menu.
- **Anti-Overwrite Protection:** Generates unique, timestamped markdown files using the source name and sanitized conversation title to ensure historical records are preserved.
- **Context-Optimized Token Management:** Strips image references and system junk locally *before* transmission to keep API input context efficient without truncating technical depth.

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

2. **Install the required Google GenAI SDK:**
```bash
pip install google-genai

```



## Configuration

The script relies on the official Google GenAI SDK. You must expose your Gemini API key as an environment variable before execution.

**On Linux/macOS:**

```bash
export GEMINI_API_KEY="your_api_key_here"

```

**On Windows (Command Prompt):**

```cmd
set GEMINI_API_KEY=your_api_key_here

```

**On Windows (PowerShell):**

```powershell
$env:GEMINI_API_KEY="your_api_key_here"

```

## Usage

1. Place your exported conversation JSON files (e.g., Claude `conversations.json` or your Google Takeout archive) into the project folder.
2. Run the main processing script:
```bash
python summarizer.py

```


3. Use the interactive menu to:
* Select an automatically detected JSON file (or provide a custom path).
* Choose whether to view recent logs or search across your chat archive using technical keywords (e.g., "Subway", "parser", "API").
* Select the conversation index to analyze.


4. The script will securely handle the parsing and write a highly detailed state file named like:
`[source_file]_[sanitized_title]_[HHMMSS].md`

## Architecture Evolution

This utility evolved over several versions to handle the distinct real-world quirks of platform logs:

* **v1 - v3:** Resolved deep nesting challenges, filtered image payload markers, and added filtering to reject UUID hashes.
* **v4:** Added dynamic filesystem scanning utilities.
* **v5 (Current):** Engineered the timeline grouping pipeline for model-less Google Takeout archives and added dynamic timestamp file preservation.

## License

This project is licensed under the MIT License - see the [LICENSE](https://www.google.com/search?q=LICENSE) file for details.

```

```