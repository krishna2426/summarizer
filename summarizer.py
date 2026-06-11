import json
import os
import re
import sys
import datetime
import argparse
from google import genai

# --- 1. Configuration Constants ---
__version__ = "1.2.0"
DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_OUTPUT_DIR = "project_states"

# --- 2. Advanced Multi-Item Format Detector ---
def is_gemini_takeout(conversations):
    """Loosened detection: Scans multiple items to check if it's a Gemini export."""
    if not isinstance(conversations, list):
        return False
    
    # Check up to the first 5 items for the Gemini Takeout signature
    for item in conversations[:5]:
        if isinstance(item, dict) and str(item.get('title', '')).startswith('Prompted'):
            return True
    return False

# --- 3. Recursive Text Scraper ---
def find_real_text(node):
    """Isolates real human dialogue strings from structural UUIDs and metadata."""
    if isinstance(node, str):
        node_stripped = node.strip()
        if re.match(r'^\d{4}-\d{2}-\d{2}T', node_stripped): return ""
        if "uploaded:image_" in node_stripped or "contentFetchId" in node_stripped: return ""
            
        clean_hex_check = node_stripped.replace('-', '').replace('_', '').replace(' ', '')
        if re.match(r'^[a-fA-F0-9]+$', clean_hex_check) and len(clean_hex_check) >= 8:
            return ""
        return node
        
    elif isinstance(node, list):
        for item in node:
            txt = find_real_text(item)
            if txt.strip(): return txt
            
    elif isinstance(node, dict):
        for key in ['text', 'content', 'parts', 'message']:
            if key in node:
                txt = find_real_text(node[key])
                if txt.strip(): return txt
                
        for key, val in node.items():
            if key.lower() in ['id', 'uuid', 'chat_id', 'message_id', 'created_at', 'updated_at', 'timestamp']:
                continue
            txt = find_real_text(val)
            if txt.strip(): return txt
    return ""

# --- 4. Title & Content Extraction ---
def get_clean_title(chat, index):
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
    conversation_text = ""
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
                        
    elif 'chat_messages' in selected_chat:
        for msg in selected_chat.get('chat_messages', []):
            role, text = msg.get('sender', 'unknown'), msg.get('text', '')
            if text.strip(): conversation_text += f"{role.upper()}: {text}\n\n"
                
    elif 'messages' in selected_chat or isinstance(selected_chat, dict):
        messages = selected_chat.get('messages', [selected_chat])
        for msg in messages:
            role = msg.get('role', 'unknown')
            content = find_real_text(msg)
            if content.strip(): conversation_text += f"{role.upper()}: {content}\n\n"
    return conversation_text

# --- 5. Interactive Mode Fallbacks ---
def interactive_select_file():
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
                if choice.lower() == 'q': sys.exit(0)
                choice_int = int(choice)
                if 0 <= choice_int < len(json_files): return json_files[choice_int]
                if choice_int == len(json_files): break
            except ValueError: pass
    return input("\nEnter JSON export file path: ").strip()

def interactive_select_conversation(all_conversations):
    print("\n[1] View 10 most recent chats\n[2] Search chats by keyword")
    menu_choice = input("\nSelect an option: ").strip()
    
    visible_chats = all_conversations[:10] if menu_choice == '1' else []
    if menu_choice == '2':
        keyword = input("Enter keyword: ").lower()
        for chat in all_conversations:
            if keyword in get_clean_title(chat, 0).lower() or keyword in find_real_text(chat).lower():
                visible_chats.append(chat)
        visible_chats = visible_chats[:15]
        
    if not visible_chats:
        print("No matching conversations found.")
        return None, None

    for index, chat in enumerate(visible_chats):
        print(f"[{index}] {get_clean_title(chat, index)}")
        
    while True:
        try:
            choice = input("\nEnter chat number to summarize: ").strip()
            choice_int = int(choice)
            if 0 <= choice_int < len(visible_chats):
                sel = visible_chats[choice_int]
                return extract_chat_text(sel), get_clean_title(sel, choice_int)
        except ValueError: pass

# --- 6. Unified Inference Interface ---
def call_llm_backend(provider, prompt):
    """Dispatches the prompt to the selected LLM provider backend."""
    if provider.lower() == "gemini":
        try:
            # Simple custom CLI loading indicator
            print("Sending request to Gemini...", end="", flush=True)
            client = genai.Client()
            response = client.models.generate_content(
                model=DEFAULT_MODEL,
                contents=prompt,
            )
            print(" Done!")
            return response.text
        except Exception as e:
            print(f"\nGemini Client Error: {e}")
            sys.exit(1)
            
    elif provider.lower() in ["openai", "anthropic", "ollama"]:
        print(f"\nBackend Error: '{provider}' integration is structured but pending package installation.")
        print("Please configure your preferred community SDK wrapper here.")
        sys.exit(1)
    else:
        print(f"\nUnsupported provider: {provider}")
        sys.exit(1)

# --- 7. Execution Core ---
def main():
    parser = argparse.ArgumentParser(description="AI Project State Explorer & Summary Extraction CLI.")
    parser.add_argument("--version", "-v", action="version", version=f"%(progs)s v{__version__}")
    parser.add_argument("--file", "-f", help="Path to target chat export JSON file")
    parser.add_argument("--output-dir", "-o", default=DEFAULT_OUTPUT_DIR, help="Directory path to write generated files")
    parser.add_argument("--provider", "-p", default="gemini", choices=["gemini", "openai", "anthropic", "ollama"], help="LLM backend choice")
    
    args = parser.parse_args()
    
    # 1. Target File Resolution
    target_file = args.file if args.file else interactive_select_file()
    if not target_file or not os.path.exists(target_file):
        print(f"Error: File '{target_file}' does not exist.")
        sys.exit(1)
        
    # 2. File Parsing & Multi-Item Gemini Normalization Wrapper
    try:
        with open(target_file, 'r', encoding='utf-8') as f:
            all_conversations = json.load(f)
    except Exception as e:
        print(f"Error reading or parsing JSON file: {e}")
        sys.exit(1)
        
    if isinstance(all_conversations, dict):
        all_conversations = [all_conversations]

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

    # 3. Conversation Text Extraction
    chat_text, chat_title = interactive_select_conversation(all_conversations)
    if not chat_text:
        print("Exiting: No conversation content selected.")
        sys.exit(0)

    # 4. Prompt Synthesis & Execution
    generation_prompt = f"""
    Analyze the following chat history and generate a strict Markdown state file.
    Do not include any conversational filler. Use this exact structure:
    
    # Project Overview
    * **Goal:** * **Tech Stack:** # Current State
    * **Working Milestones:** * **Known Blockers:** # Established Rules & Constraints
    * **Formatting Rules:** * **Architectural Decisions:** # Next Immediate Task
    
    Chat History:
    {chat_text}
    """
    
    markdown_output = call_llm_backend(args.provider, generation_prompt)
    
    # 5. Protected File Write Operation
    try:
        os.makedirs(args.output_dir, exist_ok=True)
        safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', chat_title)
        safe_title = re.sub(r'_+', '_', safe_title).strip('_')
        base_name = os.path.splitext(os.path.basename(target_file))[0]
        timestamp = datetime.datetime.now().strftime("%H%M%S")
        
        final_filename = os.path.join(args.output_dir, f"{base_name}_{safe_title[:30]}_{timestamp}.md")
        
        with open(final_filename, 'w', encoding='utf-8') as f:
            f.write(markdown_output)
        print(f"Success! State file safely written to: {final_filename}")
        
    except IOError as e:
        print(f"File System Error: Failed to write state file output to directory. Detail: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()