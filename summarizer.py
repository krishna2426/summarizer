import json
import os
import re
import datetime
from google import genai

# --- 1. Configuration ---
try:
    client = genai.Client()
except Exception as e:
    print("Error: Could not initialize Gemini Client. Make sure your GEMINI_API_KEY environment variable is set.")
    exit(1)

# --- 2. Dynamic File Scanner ---
def select_json_file():
    """Scans the current directory for JSON files and lets the user pick one."""
    json_files = [f for f in os.listdir('.') if f.endswith('.json')]
    
    print("\n==================================")
    print("    AVAILABLE EXPORT FILES        ")
    print("==================================")
    
    if json_files:
        print("Found the following JSON files in this directory:")
        for idx, filename in enumerate(json_files):
            print(f"[{idx}] {filename}")
        print(f"[{len(json_files)}] Enter a custom/relative file path manually")
        
        while True:
            try:
                choice = input("\nSelect a file number to load (or 'q' to quit): ").strip()
                if choice.lower() == 'q':
                    exit(0)
                choice_int = int(choice)
                if 0 <= choice_int < len(json_files):
                    return json_files[choice_int]
                elif choice_int == len(json_files):
                    break
                else:
                    print("Invalid selection. Please choose a valid number.")
            except ValueError:
                print("Please enter a valid number.")
                
    else:
        print("No .json files automatically detected in this folder.")
        
    while True:
        path = input("\nEnter the path or filename of your JSON export file: ").strip()
        if path.lower() == 'q':
            exit(0)
        if os.path.exists(path):
            return path
        else:
            print(f"Error: File '{path}' could not be found. Try again (or 'q' to quit).")

# --- 3. Recursive Text Hunter ---
def find_real_text(node):
    """Digs through JSON to find real human strings, ignoring metadata and IDs."""
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

# --- 4. Advanced Title Generator ---
def get_clean_title(chat, index):
    """Extracts a clean title by prioritizing actual message arrays first."""
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
        text = re.sub(r'^[\{\[\s"\'`#\-\*]+', '', text)
        
        text = text.strip()
        if text:
            words = text.split()
            generated_title = " ".join(words[:6])
            if len(words) > 6:
                generated_title += "..."
            return f"[Auto] {generated_title}"
            
    return f"Empty Chat #{index + 1}"

# --- 5. Multi-Format Chat Parser ---
def extract_chat_text(selected_chat):
    """Auto-detects the JSON format and extracts the conversation text."""
    conversation_text = ""
    
    if 'mapping' in selected_chat:
        mapping = selected_chat.get('mapping', {})
        for node_id, node_data in mapping.items():
            message = node_data.get('message')
            if message:
                role = message.get('author', {}).get('role', 'unknown')
                content_type = message.get('content', {}).get('content_type', '')
                if content_type == 'text':
                    parts = message.get('content', {}).get('parts', [])
                    text = "".join(parts)
                    if role in ['user', 'assistant'] and text.strip():
                        conversation_text += f"{role.upper()}: {text}\n\n"
                        
    elif 'chat_messages' in selected_chat:
        messages = selected_chat.get('chat_messages', [])
        for msg in messages:
            role = msg.get('sender', 'unknown')
            text = msg.get('text', '')
            if text.strip():
                conversation_text += f"{role.upper()}: {text}\n\n"
                
    elif 'messages' in selected_chat or isinstance(selected_chat, dict):
        messages = selected_chat.get('messages', [selected_chat])
        for msg in messages:
            role = msg.get('role', 'unknown')
            content = find_real_text(msg)
            if content.strip():
                conversation_text += f"{role.upper()}: {content}\n\n"
    elif 'history' in selected_chat:
        for msg in selected_chat.get('history', []):
            role = msg.get('author_role', 'unknown')
            text = msg.get('text_body', '')
            if text.strip():
                conversation_text += f"{role.upper()}: {text}\n\n"
    else:
        print("Warning: Unrecognized chat format. Extracted text may be incomplete.")
        
    return conversation_text

# --- 6. Interactive Menu ---
def select_conversation(filepath):
    """Provides an interactive menu and returns the chat text AND the title."""
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            all_conversations = json.load(file)
    except Exception as e:
        print(f"\nError reading '{filepath}': {e}")
        exit(1)

    if isinstance(all_conversations, dict):
        all_conversations = [all_conversations]

    # Gemini Takeout Fix
    if all_conversations and isinstance(all_conversations[0], dict) and str(all_conversations[0].get('title', '')).startswith('Prompted'):
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

    print("\n==================================")
    print("   CHAT SUMMARIZER NAVIGATION     ")
    print("==================================")
    print("[1] View 10 most recent chats")
    print("[2] Search chats by keyword")
    print("[q] Quit")
    
    menu_choice = input("\nSelect an option: ").strip()
    
    if menu_choice.lower() == 'q':
        exit(0)
        
    if menu_choice == '1':
        visible_chats = all_conversations[:10]
        
    elif menu_choice == '2':
        keyword = input("Enter a keyword to search for (e.g., 'Subway'): ").lower()
        visible_chats = []
        
        for chat in all_conversations:
            generated_title = get_clean_title(chat, 0).lower()
            msg_snippet = find_real_text(chat).lower()
                
            if keyword in generated_title or keyword in msg_snippet:
                visible_chats.append(chat)
                
        if not visible_chats:
            print(f"\nNo conversations found matching '{keyword}'.")
            return select_conversation(filepath)
            
        visible_chats = visible_chats[:15]
    else:
        print("Invalid option. Restarting menu...")
        return select_conversation(filepath)

    print(f"\n--- Matching Conversations (Showing top {len(visible_chats)}) ---")
    for index, chat in enumerate(visible_chats):
        clean_title = get_clean_title(chat, index)
        print(f"[{index}] {clean_title}")
    print("-" * 40)
    
    while True:
        try:
            choice = input("Enter the number of the chat to summarize (or 'b' to go back): ")
            if choice.lower() == 'b':
                return select_conversation(filepath)
                
            choice = int(choice)
            if 0 <= choice < len(visible_chats):
                selected_chat = visible_chats[choice]
                final_title = get_clean_title(selected_chat, choice)
                print(f"\nExtracting data from: {final_title}...")
                
                # RETURN BOTH TEXT AND TITLE NOW
                return extract_chat_text(selected_chat), final_title
            else:
                print("Invalid number. Please select a valid number.")
        except ValueError:
            print("Please enter a valid integer.")

# --- 7. AI Summarization ---
def generate_state_file(chat_text, chat_title, source_filename):
    """Sends text to Gemini and saves uniquely named Markdown file."""
    if not chat_text.strip():
        print("Error: No text extracted. Cannot generate a summary.")
        return

    print("Sending to Gemini for summarization... (This might take a few seconds)")
    
    prompt = f"""
    Analyze the following chat history and generate a strict Markdown state file.
    Do not include any conversational filler. Use this exact structure:
    
    # Project Overview
    * **Goal:** * **Tech Stack:** # Current State
    * **Working Milestones:** * **Known Blockers:** # Established Rules & Constraints
    * **Formatting Rules:** * **Architectural Decisions:** # Next Immediate Task
    
    Chat History:
    {chat_text}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        
        # 1. Clean the chat title so it's safe for Windows files (removes brackets, colons, etc.)
        safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', chat_title)
        safe_title = re.sub(r'_+', '_', safe_title).strip('_')
        
        # 2. Get the original JSON filename without the '.json' part
        base_json_name = os.path.splitext(os.path.basename(source_filename))[0]
        
        # 3. Get the current time (HourMinuteSecond)
        timestamp = datetime.datetime.now().strftime("%H%M%S")
        
        # 4. Stitch it all together! Limiting title length so it isn't massive.
        new_filename = f"{base_json_name}_{safe_title[:30]}_{timestamp}.md"
        
        with open(new_filename, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"\nSuccess! State file successfully saved as '{new_filename}'")
        
    except Exception as e:
        print(f"\nError generating content: {e}")

# --- Main Execution ---
if __name__ == "__main__":
    # Get the file name
    chosen_file = select_json_file()
    
    # Extract text AND the clean title
    chat_text, chat_title = select_conversation(chosen_file)
    
    # Generate the file with all three pieces of info
    generate_state_file(chat_text, chat_title, chosen_file)