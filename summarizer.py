import json
import os
import re
import sys
import datetime
import argparse
from google import genai

# --- 1. Configuration Constants ---
__version__ = "1.3.0"
DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_OUTPUT_DIR = "project_states"

# Module-level client (initialized once, not per-call)
_gemini_client = None

def get_gemini_client():
    """Returns a cached Gemini client, initializing it on first use."""
    global _gemini_client
    if _gemini_client is None:
        try:
            _gemini_client = genai.Client()
        except Exception as e:
            print(f"Error: Could not initialize Gemini Client. Make sure GEMINI_API_KEY is set.\nDetail: {e}")
            sys.exit(1)
    return _gemini_client

# --- 2. Advanced Multi-Item Format Detector ---
def is_gemini_takeout(conversations):
    """Loosened detection: Scans multiple items to check if it's a Gemini export."""
    if not isinstance(conversations, list):
        return False
    for item in conversations[:5]:
        if isinstance(item, dict) and str(item.get('title', '')).startswith('Prompted'):
            return True
    return False

# --- 3. Recursive Text Scraper ---
def find_real_text(node):
    """Isolates real human dialogue strings from structural UUIDs and metadata."""
    if isinstance(node, str):
        node_stripped = node.strip()
        if re.match(r'^\d{4}-\d{2}-\d{2}T', node_stripped):
            return ""
        if "uploaded:image_" in node_stripped or "contentFetchId" in node_stripped:
            return ""
        clean_hex_check = node_stripped.replace('-', '').replace('_', '').replace(' ', '')
        if re.match(r'^[a-fA-F0-9]+$', clean_hex_check) and len(clean_hex_check) >= 8:
            return ""
        return node

    elif isinstance(node, list):
        for item in node:
            txt = find_real_text(item)
            if txt.strip():
                return txt

    elif isinstance(node, dict):
        for key in ['text', 'content', 'parts', 'message']:
            if key in node:
                txt = find_real_text(node[key])
                if txt.strip():
                    return txt
        for key, val in node.items():
            if key.lower() in ['id', 'uuid', 'chat_id', 'message_id', 'created_at', 'updated_at', 'timestamp']:
                continue
            txt = find_real_text(val)
            if txt.strip():
                return txt
    return ""

# --- 4. Title & Content Extraction ---
def get_clean_title(chat, index):
    """Extracts a clean display title from a chat object."""
    title = chat.get('title', '').strip()
    if title and title.lower() != 'untitled chat':
        return title

    messages = chat.get('chat_messages', chat.get('messages', []))
    raw_text = ""
    if messages and isinstance(messages, list):
        raw_text = find_real_text(messages[0])
    if not raw_text.strip():
        raw_text = find_real_text(chat)

    if raw_text:
        text = raw_text.strip()
        text = re.sub(r'^(user|model|human|assistant|system)\s*:\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^[\{\[\s"\'`#\-\*]+', '', text).strip()
        if text:
            words = text.split()
            generated_title = " ".join(words[:6])
            return f"[Auto] {generated_title}..." if len(words) > 6 else f"[Auto] {generated_title}"

    return f"Empty Chat #{index + 1}"


def extract_chat_text(selected_chat):
    """Auto-detects the JSON format and extracts the full conversation as plain text."""
    conversation_text = ""

    # ChatGPT node-graph format
    if 'mapping' in selected_chat:
        mapping = selected_chat.get('mapping', {})
        for node_id, node_data in mapping.items():
            message = node_data.get('message')
            if message:
                role = message.get('author', {}).get('role', 'unknown')
                if message.get('content', {}).get('content_type', '') == 'text':
                    text = "".join(message.get('content', {}).get('parts', []))
                    if role in ['user', 'assistant'] and text.strip():
                        conversation_text += f"{role.upper()}: {text}\n\n"

    # Claude flat array format
    elif 'chat_messages' in selected_chat:
        for msg in selected_chat.get('chat_messages', []):
            role = msg.get('sender', 'unknown')
            text = msg.get('text', '')
            if text.strip():
                conversation_text += f"{role.upper()}: {text}\n\n"

    # Generic messages format (Gemini sessions, etc.)
    elif 'messages' in selected_chat or isinstance(selected_chat, dict):
        messages = selected_chat.get('messages', [selected_chat])
        for msg in messages:
            role = msg.get('role', 'unknown')
            content = find_real_text(msg)
            if content.strip():
                conversation_text += f"{role.upper()}: {content}\n\n"

    # Legacy history format (author_role / text_body)
    elif 'history' in selected_chat:
        for msg in selected_chat.get('history', []):
            role = msg.get('author_role', 'unknown')
            text = msg.get('text_body', '')
            if text.strip():
                conversation_text += f"{role.upper()}: {text}\n\n"

    else:
        print("Warning: Unrecognized chat format. Extracted text may be incomplete.")

    return conversation_text

# --- 5. Interactive Mode ---
def interactive_select_file():
    """Scans the current directory for JSON files and lets the user pick one."""
    json_files = [f for f in os.listdir('.') if f.endswith('.json')]
    print("\n==================================")
    print("    AVAILABLE EXPORT FILES        ")
    print("==================================")

    if json_files:
        for idx, filename in enumerate(json_files):
            print(f"[{idx}] {filename}")
        print(f"[{len(json_files)}] Enter custom file path manually")

        while True:
            try:
                choice = input("\nSelect a file number (or 'q' to quit): ").strip()
                if choice.lower() == 'q':
                    sys.exit(0)
                choice_int = int(choice)
                if 0 <= choice_int < len(json_files):
                    return json_files[choice_int]
                if choice_int == len(json_files):
                    break
                print("Invalid selection. Please choose a valid number.")
            except ValueError:
                print("Please enter a valid number.")

    # Custom path with retry loop
    while True:
        path = input("\nEnter JSON export file path (or 'q' to quit): ").strip()
        if path.lower() == 'q':
            sys.exit(0)
        if os.path.exists(path):
            return path
        print(f"Error: File '{path}' not found. Try again.")


def interactive_select_conversation(all_conversations):
    """Interactive menu to browse and select a conversation for summarization."""
    print("\n==================================")
    print("    CHAT SUMMARIZER NAVIGATION    ")
    print("==================================")
    print("[1] View 10 most recent chats")
    print("[2] Search chats by keyword")
    print("[q] Quit")

    menu_choice = input("\nSelect an option: ").strip()

    if menu_choice.lower() == 'q':
        sys.exit(0)

    visible_chats = []

    if menu_choice == '1':
        visible_chats = all_conversations[:10]
    elif menu_choice == '2':
        keyword = input("Enter keyword to search for: ").lower()
        for chat in all_conversations:
            if keyword in get_clean_title(chat, 0).lower() or keyword in find_real_text(chat).lower():
                visible_chats.append(chat)
        visible_chats = visible_chats[:15]
        if not visible_chats:
            print(f"\nNo conversations found matching '{keyword}'.")
            return interactive_select_conversation(all_conversations)
    else:
        print("Invalid option. Please try again.")
        return interactive_select_conversation(all_conversations)

    if not visible_chats:
        print("No conversations to display.")
        return None, None

    print(f"\n--- Showing {len(visible_chats)} conversation(s) ---")
    for index, chat in enumerate(visible_chats):
        print(f"[{index}] {get_clean_title(chat, index)}")
    print("-" * 40)

    while True:
        choice = input("\nEnter chat number to summarize (or 'b' to go back, 'q' to quit): ").strip()
        if choice.lower() == 'q':
            sys.exit(0)
        if choice.lower() == 'b':
            return interactive_select_conversation(all_conversations)
        try:
            choice_int = int(choice)
            if 0 <= choice_int < len(visible_chats):
                sel = visible_chats[choice_int]
                title = get_clean_title(sel, choice_int)
                print(f"\nExtracting data from: {title}...")
                return extract_chat_text(sel), title
            print("Invalid number. Please select a valid option.")
        except ValueError:
            print("Please enter a valid integer.")

# --- 6. Unified Inference Interface ---
def call_llm_backend(provider, prompt):
    """Dispatches the prompt to the selected LLM provider backend."""
    if provider.lower() == "gemini":
        try:
            print("Sending request to Gemini...", end="", flush=True)
            client = get_gemini_client()
            response = client.models.generate_content(
                model=DEFAULT_MODEL,
                contents=prompt,
            )
            print(" Done!")
            return response.text
        except Exception as e:
            print(f"\nGemini API Error: {e}")
            sys.exit(1)

    elif provider.lower() in ["openai", "anthropic", "ollama"]:
        print(f"\nBackend '{provider}' is structured but pending implementation.")
        print("Install the relevant SDK and add your integration inside call_llm_backend().")
        print("  openai:    pip install openai")
        print("  anthropic: pip install anthropic")
        print("  ollama:    pip install ollama")
        sys.exit(1)

    else:
        print(f"\nUnsupported provider: '{provider}'")
        sys.exit(1)

# --- 7. Execution Core ---
def main():
    parser = argparse.ArgumentParser(
        description="AI Project State Explorer & Summary Extraction CLI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python summarizer.py
  python summarizer.py -f conversations.json
  python summarizer.py -f export.json -o ./states -p gemini
        """
    )
    # FIX: was %(progs)s — correct is %(prog)s
    parser.add_argument("--version", "-v", action="version", version=f"%(prog)s v{__version__}")
    parser.add_argument("--file", "-f", help="Path to target chat export JSON file")
    parser.add_argument("--output-dir", "-o", default=DEFAULT_OUTPUT_DIR, help="Directory to write generated state files (default: project_states)")
    parser.add_argument("--provider", "-p", default="gemini", choices=["gemini", "openai", "anthropic", "ollama"], help="LLM backend to use (default: gemini)")

    args = parser.parse_args()

    # 1. Target File Resolution
    target_file = args.file if args.file else interactive_select_file()
    if not target_file or not os.path.exists(target_file):
        print(f"Error: File '{target_file}' does not exist.")
        sys.exit(1)

    # 2. File Parsing
    try:
        with open(target_file, 'r', encoding='utf-8') as f:
            all_conversations = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Could not parse JSON file '{target_file}'. It may be malformed.\nDetail: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

    if isinstance(all_conversations, dict):
        all_conversations = [all_conversations]

    # 3. Gemini Takeout Normalization
    if is_gemini_takeout(all_conversations):
        grouped = {}
        for item in all_conversations:
            date_key = item.get('time', 'Unknown_Date')[:10]
            if date_key not in grouped:
                grouped[date_key] = {'title': f"Gemini Session ({date_key})", 'messages': []}
            item['role'] = 'user'
            if item.get('title', '').startswith('Prompted '):
                item['content'] = item['title'].replace('Prompted ', '', 1)
            grouped[date_key]['messages'].insert(0, item)
        all_conversations = list(grouped.values())

    # 4. Conversation Selection
    chat_text, chat_title = interactive_select_conversation(all_conversations)
    if not chat_text or not chat_text.strip():
        print("Exiting: No conversation content could be extracted.")
        sys.exit(0)

    # 5. Prompt Synthesis
    # FIX: properly formatted multi-line prompt (was crammed onto single lines before)
    generation_prompt = f"""Analyze the following chat history and generate a strict Markdown state file.
Do not include any conversational filler. Use this exact structure:

# Project Overview
* **Goal:**
* **Tech Stack:**

# Current State
* **Working Milestones:**
* **Known Blockers:**

# Established Rules & Constraints
* **Formatting Rules:**
* **Architectural Decisions:**

# Next Immediate Task

Chat History:
{chat_text}
"""

    markdown_output = call_llm_backend(args.provider, generation_prompt)

    # 6. Protected File Write
    try:
        os.makedirs(args.output_dir, exist_ok=True)
        safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', chat_title)
        safe_title = re.sub(r'_+', '_', safe_title).strip('_')
        base_name = os.path.splitext(os.path.basename(target_file))[0]
        timestamp = datetime.datetime.now().strftime("%H%M%S")
        final_filename = os.path.join(args.output_dir, f"{base_name}_{safe_title[:30]}_{timestamp}.md")

        with open(final_filename, 'w', encoding='utf-8') as f:
            f.write(markdown_output)

        print(f"\nSuccess! State file written to: {final_filename}")

    except IOError as e:
        print(f"File System Error: Failed to write output file.\nDetail: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()