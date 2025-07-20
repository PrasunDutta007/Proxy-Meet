import os
import socket
import requests
from dotenv import load_dotenv
import re
from datetime import datetime
from typing import Dict, List

# --- FORCE IPv4 CONFIGURATION ---
def force_ipv4_globally():
    """Force all connections to use IPv4 only"""
    print("🌐 Configuring IPv4-only connections for Notion...")
    
    # Method 1: Patch socket.getaddrinfo to return only IPv4 addresses
    original_getaddrinfo = socket.getaddrinfo
    
    def ipv4_only_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        """Custom getaddrinfo that only returns IPv4 addresses"""
        try:
            # Force IPv4 family
            return original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
        except socket.gaierror:
            # If IPv4 fails, still try original (but this shouldn't happen for Notion)
            return original_getaddrinfo(host, port, family, type, proto, flags)
    
    # Apply the patch
    socket.getaddrinfo = ipv4_only_getaddrinfo
    print("✅ IPv4-only socket configuration applied for Notion")
    
    # Method 2: Configure requests to prefer IPv4
    import urllib3
    from urllib3.util.connection import create_connection
    
    def ipv4_create_connection(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None, socket_options=None):
        """Create IPv4-only connection"""
        host, port = address
        err = None
        
        # Force IPv4 resolution
        for res in socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            sock = None
            try:
                sock = socket.socket(af, socktype, proto)
                if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                    sock.settimeout(timeout)
                if source_address:
                    sock.bind(source_address)
                sock.connect(sa)
                return sock
            except socket.error as _:
                err = _
                if sock is not None:
                    sock.close()
        
        if err is not None:
            raise err
        else:
            raise socket.error("getaddrinfo returns an empty list")
    
    # Patch urllib3 to use IPv4-only connections
    urllib3.util.connection.create_connection = ipv4_create_connection
    print("✅ IPv4-only HTTP adapter configured for Notion")

# Apply IPv4 configuration before any network operations
force_ipv4_globally()

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

NOTION_API_URL = "https://api.notion.com/v1/pages"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def ipv4_safe_request(method, url, **kwargs):
    """Wrapper to ensure Notion API calls use IPv4 and handle errors gracefully"""
    try:
        print(f"🌐 Making {method.upper()} request to Notion via IPv4...")
        if method.lower() == 'post':
            response = requests.post(url, **kwargs)
        elif method.lower() == 'get':
            response = requests.get(url, **kwargs)
        else:
            response = requests.request(method, url, **kwargs)
        
        print(f"✅ Notion API call completed via IPv4 (Status: {response.status_code})")
        return response
    except Exception as e:
        error_msg = f"❌ Notion API call failed: {str(e)}"
        print(error_msg)
        # Check if it's a network-related error
        if "10060" in str(e) or "timeout" in str(e).lower():
            error_msg += " (Network timeout - check IPv4 configuration)"
        elif "connection" in str(e).lower():
            error_msg += " (Connection error - possible IPv6 fallback issue)"
        raise Exception(error_msg)

def extract_meeting_metadata(markdown_content: str) -> Dict[str, str]:
    """Extract ALL detailed content from markdown sections - COMPREHENSIVE PARSING"""
    metadata = {
        "title": "Session Notes",
        "session_type": "General Session",
        "full_content": {},
        "overview": "",
        "action_items": [],
        "key_decisions": [],
        "participants": []
    }
    
    lines = markdown_content.strip().splitlines()
    current_section = ""
    current_content = []
    
    print(f"🔍 DEBUG: Processing {len(lines)} lines of markdown")
    
    for i, line in enumerate(lines):
        original_line = line
        line = line.strip()
        
        # Extract title (first # header)
        if line.startswith("# ") and metadata["title"] == "Session Notes":
            metadata["title"] = line[2:].strip()
            print(f"📝 Found title: '{metadata['title']}'")
            continue
        
        # Identify main sections (## headers)
        if line.startswith("## "):
            # Save previous section
            if current_section and current_content:
                content_text = "\n".join(current_content).strip()
                clean_section_name = current_section.replace("## ", "").strip()
                metadata["full_content"][clean_section_name] = format_section_content(content_text)
                
                # Process specific sections
                process_section_content(clean_section_name, content_text, metadata)
                
                print(f"✅ Processed section '{clean_section_name}' with {len(content_text)} chars")
            
            current_section = line
            current_content = []
            print(f"🎯 New section: '{line}'")
        else:
            if line and not line.startswith("```"):
                current_content.append(original_line)  # Keep original formatting
    
    # Handle last section
    if current_section and current_content:
        content_text = "\n".join(current_content).strip()
        clean_section_name = current_section.replace("## ", "").strip()
        metadata["full_content"][clean_section_name] = format_section_content(content_text)
        process_section_content(clean_section_name, content_text, metadata)
        print(f"✅ Processed final section '{clean_section_name}' with {len(content_text)} chars")
    
    # Determine session type
    content_lower = markdown_content.lower()
    if "training" in content_lower or "tutorial" in content_lower or "guide" in content_lower or "teaching" in content_lower:
        metadata["session_type"] = "Training"
    elif "interview" in content_lower:
        metadata["session_type"] = "Interview"
    elif "brainstorm" in content_lower:
        metadata["session_type"] = "Brainstorming"
    elif "standup" in content_lower:
        metadata["session_type"] = "Standup"
    elif "1-on-1" in content_lower:
        metadata["session_type"] = "1-on-1"
    
    print(f"📊 Final metadata summary:")
    print(f"   • Title: {metadata['title']}")
    print(f"   • Type: {metadata['session_type']}")
    print(f"   • Sections: {list(metadata['full_content'].keys())}")
    print(f"   • Action Items: {len(metadata['action_items'])}")
    
    return metadata

def process_section_content(section_name: str, content: str, metadata: Dict):
    """Process specific section content based on section name"""
    section_lower = section_name.lower()
    
    if "overview" in section_lower or "summary" in section_lower:
        metadata["overview"] = format_section_content(content)
        
    elif "action" in section_lower or "recommendation" in section_lower or "items" in section_lower:
        actions = extract_comprehensive_actions(content)
        metadata["action_items"].extend(actions)
        print(f"🎯 Extracted {len(actions)} action items from '{section_name}'")
        
    elif "decision" in section_lower:
        decisions = extract_list_items(content)
        metadata["key_decisions"].extend(decisions)
        
    elif "participant" in section_lower:
        participants = extract_list_items(content)
        metadata["participants"].extend(participants)

def extract_comprehensive_actions(text: str) -> List[str]:
    """COMPREHENSIVE action item extraction - handles ALL markdown formats"""
    actions = []
    lines = text.split('\n')
    
    print(f"🔍 DEBUG: Extracting actions from {len(lines)} lines")
    
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        
        # Skip empty lines
        if not line.strip():
            i += 1
            continue
            
        stripped = line.strip()
        
        # CASE 1: * **Action Item:** format
        if stripped.startswith('*') and '**Action Item:**' in stripped:
            action_title = stripped.replace('*', '').replace('**Action Item:**', '').strip()
            action_details = []
            i += 1
            
            # Collect all related details
            while i < len(lines):
                detail_line = lines[i].rstrip()
                detail_stripped = detail_line.strip()
                
                # Stop if we hit another action item or major section
                if (detail_stripped.startswith('*') and '**Action Item:**' in detail_stripped) or \
                   detail_stripped.startswith('##') or \
                   (detail_stripped.startswith('###') and not detail_stripped.startswith('    ')):
                    break
                
                # Collect indented details
                if detail_line.startswith('    ') and detail_stripped:
                    clean_detail = detail_stripped.replace('*', '').strip()
                    # Clean up bold formatting
                    clean_detail = re.sub(r'\*\*(.+?):\*\*', r'[\1]:', clean_detail)
                    if clean_detail and len(clean_detail) > 3:
                        action_details.append(clean_detail)
                
                i += 1
            
            # Format the action
            if action_title:
                formatted_action = f"{len(actions) + 1}. {action_title}"
                if action_details:
                    formatted_action += "\n" + "\n".join([f"   • {detail}" for detail in action_details])
                actions.append(formatted_action)
                print(f"✅ Action found: '{action_title}' with {len(action_details)} details")
            
            continue
            
        # CASE 2: Simple bullet points (*, -, +)
        elif stripped.startswith(('* ', '- ', '+ ')) and not '**Action Item:**' in stripped:
            action_text = stripped[2:].strip()
            # Clean up formatting
            action_text = re.sub(r'\*\*(.+?)\*\*', r'[\1]', action_text)
            
            if len(action_text) > 10:  # Only meaningful actions
                formatted_action = f"{len(actions) + 1}. {action_text}"
                actions.append(formatted_action)
                print(f"✅ Simple action found: '{action_text[:50]}...'")
        
        # CASE 3: Numbered items (1. 2. 3.)
        elif re.match(r'^\d+\.\s', stripped):
            action_text = re.sub(r'^\d+\.\s', '', stripped).strip()
            action_text = re.sub(r'\*\*(.+?)\*\*', r'[\1]', action_text)
            
            if len(action_text) > 10:
                formatted_action = f"{len(actions) + 1}. {action_text}"
                actions.append(formatted_action)
                print(f"✅ Numbered action found: '{action_text[:50]}...'")
        
        i += 1
    
    print(f"🏁 Total actions extracted: {len(actions)}")
    return actions

def format_section_content(text: str) -> str:
    """Format section content with proper hierarchical indentation and spacing"""
    if not text:
        return ""
    
    lines = text.split('\n')
    formatted_lines = []
    current_main_section = ""
    
    for line in lines:
        original_line = line
        line = line.strip()
        if not line:
            continue
            
        # Handle main section headers (### headers) - TOP LEVEL
        if line.startswith('### '):
            if current_main_section:
                formatted_lines.append("")  # Add space before new section
                formatted_lines.append("")  # Extra space for better separation
            
            section_title = line.replace('### ', '').strip()
            formatted_lines.append(f"🔹 {section_title.upper()}")
            formatted_lines.append("")  # Space after main heading
            current_main_section = section_title
            
        # Handle Roman numerals (I., II., III.) - MAIN SUBSECTIONS
        elif re.match(r'^[IVX]+\.\s', line):
            formatted_lines.append("")  # Space before Roman numeral section
            roman_content = line.strip()
            formatted_lines.append(f"    📍 {roman_content}")
            formatted_lines.append("")  # Space after Roman numeral
            
        # Handle letter subsections (A., B., C.) - SUB-SUBSECTIONS  
        elif re.match(r'^[A-Z]\.\s', line):
            letter_content = re.sub(r'^[A-Z]\.\s', '', line).strip()
            formatted_lines.append(f"        ▶️ {letter_content}")
            formatted_lines.append("")  # Space after letter section
            
        # Handle lowercase letter subsections (a., b., c.) - DEEPER NESTING
        elif re.match(r'^[a-z]\.\s', line):
            lower_content = re.sub(r'^[a-z]\.\s', '', line).strip()
            formatted_lines.append(f"            • {lower_content}")
            
        # Handle numbered items (1., 2., 3.) - NUMBERED LISTS
        elif re.match(r'^\d+\.\s', line):
            numbered_content = re.sub(r'^\d+\.\s', '', line).strip()
            numbered_content = re.sub(r'\*\*(.+?)\*\*', r'[\1]', numbered_content)
            formatted_lines.append(f"            {numbered_content}")
            
        # Handle subsection bullets with brackets like "• [Action Item:]"
        elif line.startswith('• [') and line.endswith(']:'):
            subsection = line.replace('• [', '').replace(']:', '').strip()
            formatted_lines.append(f"        ▶️ {subsection}")
            
        # Handle Key Discussion Points, Important Details, etc.
        elif line.endswith(':') and any(keyword in line.lower() for keyword in ['key discussion points', 'important details', 'context', 'decisions made', 'next steps', 'overview']):
            category = line.replace(':', '').strip()
            formatted_lines.append(f"            🔸 {category}:")
            
        # Handle regular bullet points (• * -)
        elif line.startswith(('• ', '* ', '- ', '+ ')):
            bullet_content = line[2:].strip()
            # Clean up bold formatting
            bullet_content = re.sub(r'\*\*(.+?)\*\*', r'[\1]', bullet_content)
            formatted_lines.append(f"                • {bullet_content}")
            
        # Handle indented content (preserve deeper indentation)
        elif original_line.startswith('    ') or original_line.startswith('\t'):
            content = line
            content = re.sub(r'\*\*(.+?)\*\*', r'[\1]', content)
            if content:
                formatted_lines.append(f"                {content}")
                
        # Handle any remaining content as regular text
        else:
            content = re.sub(r'\*\*(.+?)\*\*', r'[\1]', line)
            if content and len(content) > 3:
                formatted_lines.append(f"            {content}")
    
    result = '\n'.join(formatted_lines)
    
    # Clean up excessive blank lines (more than 2 consecutive)
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    return result


def create_notion_entry(metadata: Dict) -> str:
    """Create a detailed Notion entry with IMPROVED hierarchical formatting"""
    
    today = datetime.today().strftime("%Y-%m-%d")
    title = metadata["title"]
    
    # CHECK FOR DUPLICATES FIRST
    if check_for_existing_entry(title, today):
        print(f"🚫 DUPLICATE PREVENTED: Entry '{title}' already exists for {today}")
        return "Duplicate prevented"
    
    # Format action items with COMPREHENSIVE structure
    action_items_text = ""
    if metadata.get("action_items"):
        print(f"📝 Formatting {len(metadata['action_items'])} action items...")
        formatted_actions = []
        
        for i, action in enumerate(metadata["action_items"]):
            print(f"   Action {i+1}: {action[:50]}...")
            formatted_actions.append(action)
        
        action_items_text = "\n\n".join(formatted_actions)
        print(f"✅ Final action items text length: {len(action_items_text)} chars")
    else:
        print("⚠️  No action items found in metadata!")
    
    # Format decisions
    decisions_text = ""
    if metadata.get("key_decisions"):
        decisions_text = "\n".join([f"• {item}" for item in metadata["key_decisions"]])
    
    # Format participants
    participants_text = ", ".join(metadata.get("participants", []))
    
    # Create detailed content from ALL sections with IMPROVED FORMATTING
    detailed_content = ""
    if metadata.get("full_content"):
        section_parts = []
        for section_name, section_content in metadata["full_content"].items():
            if section_content:
                # Create a more visually appealing section separator
                section_header = f"═══════════════════════════════════════════════════════════════════════════════\n🔵 {section_name.upper()}\n═══════════════════════════════════════════════════════════════════════════════\n"
                section_parts.append(f"{section_header}\n{section_content}")
        
        detailed_content = "\n\n\n".join(section_parts)
    
    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Title": {
                "title": create_rich_text(metadata["title"])
            },
            "Date": {
                "date": {"start": today}
            },
            "Type": {
                "select": {"name": metadata["session_type"]}
            },
            "Summary": {
                "rich_text": create_rich_text(metadata.get("overview", ""))
            },
            "Action Items": {
                "rich_text": create_rich_text(action_items_text)
            },
            "Status": {
                "select": {"name": "New"}
            }
        }
    }
    
    # Add detailed content with improved formatting
    if detailed_content:
        data["properties"]["Detailed Notes"] = {
            "rich_text": create_rich_text(detailed_content)
        }
    
    # Add optional fields
    if decisions_text:
        data["properties"]["Key Decisions"] = {
            "rich_text": create_rich_text(decisions_text)
        }
    
    if participants_text:
        data["properties"]["Participants"] = {
            "rich_text": create_rich_text(participants_text)
        }

    try:
        response = ipv4_safe_request('post', NOTION_API_URL, headers=HEADERS, json=data)
        
        if response.status_code in [200, 201]:
            print(f"✅ Successfully created Notion entry: '{metadata['title']}'")
            print(f"📊 Content stats:")
            print(f"   • Total content length: {len(detailed_content)} characters")
            print(f"   • Action items: {len(metadata['action_items'])}")
            print(f"   • Action items text length: {len(action_items_text)} chars")
            print(f"   • Sections: {len(metadata.get('full_content', {}))}")
            return "Success"
        else:
            print(f"❌ Failed to create entry: {response.status_code} - {response.text}")
            return f"Error: {response.status_code}"
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return f"Error: {str(e)}"

def clean_text(text: str) -> str:
    """Clean text for Notion - MINIMAL CLEANING, NO TRUNCATION"""
    text = re.sub(r'\*+', '', text)  # Remove asterisks
    text = re.sub(r'#+\s*', '', text)  # Remove headers
    text = re.sub(r'\n+', ' ', text)  # Replace newlines with spaces
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    
    return text.strip()

def extract_list_items(text: str) -> List[str]:
    """Extract simple list items - ALL FORMATS"""
    items = []
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Bullet points
        if line.startswith(('- ', '* ', '+ ')):
            item = line[2:].strip()
            item = re.sub(r'\*\*(.+?)\*\*', r'[\1]', item)
            if len(item) > 5:
                items.append(item)
                
        # Numbered items
        elif re.match(r'^\d+\.\s', line):
            item = re.sub(r'^\d+\.\s', '', line).strip()
            item = re.sub(r'\*\*(.+?)\*\*', r'[\1]', item)
            if len(item) > 5:
                items.append(item)
    
    return items

def create_rich_text(text: str) -> List[Dict]:
    """Create Notion rich text blocks - HANDLE LONG CONTENT"""
    if not text:
        return [{"text": {"content": ""}}]
    
    # Notion has a limit of ~2000 characters per rich text block
    max_length = 1900  # Leave some buffer
    
    if len(text) <= max_length:
        return [{"text": {"content": text.strip()}}]
    
    # Split into chunks
    chunks = []
    current_pos = 0
    
    while current_pos < len(text):
        end_pos = min(current_pos + max_length, len(text))
        
        # Try to break at word boundary if we're not at the end
        if end_pos < len(text):
            last_space = text.rfind(' ', current_pos, end_pos)
            if last_space > current_pos:
                end_pos = last_space
        
        chunk = text[current_pos:end_pos].strip()
        if chunk:
            chunks.append({"text": {"content": chunk}})
        
        current_pos = end_pos
    
    return chunks

def check_for_existing_entry(title: str, date: str) -> bool:
    """Check if an entry with the same title and date already exists"""
    try:
        print(f"🔍 Checking for existing entry: '{title}' on {date}")
        
        query_url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
        
        query_data = {
            "filter": {
                "and": [
                    {
                        "property": "Title",
                        "title": {
                            "equals": title
                        }
                    },
                    {
                        "property": "Date", 
                        "date": {
                            "equals": date
                        }
                    }
                ]
            }
        }
        
        response = ipv4_safe_request('post', query_url, headers=HEADERS, json=query_data)
        
        if response.status_code == 200:
            results = response.json().get("results", [])
            if results:
                print(f"⚠️  Found {len(results)} existing entry(ies) with same title and date")
                return True
            else:
                print("✅ No duplicate found - safe to create new entry")
                return False
        else:
            print(f"❌ Error checking for duplicates: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking for existing entry: {str(e)}")
        return False

def create_notion_entry(metadata: Dict) -> str:
    """Create a detailed Notion entry with COMPREHENSIVE action items"""
    
    today = datetime.today().strftime("%Y-%m-%d")
    title = metadata["title"]
    
    # CHECK FOR DUPLICATES FIRST
    if check_for_existing_entry(title, today):
        print(f"🚫 DUPLICATE PREVENTED: Entry '{title}' already exists for {today}")
        return "Duplicate prevented"
    
    # Format action items with COMPREHENSIVE structure
    action_items_text = ""
    if metadata.get("action_items"):
        print(f"📝 Formatting {len(metadata['action_items'])} action items...")
        formatted_actions = []
        
        for i, action in enumerate(metadata["action_items"]):
            print(f"   Action {i+1}: {action[:50]}...")
            formatted_actions.append(action)
        
        action_items_text = "\n\n".join(formatted_actions)
        print(f"✅ Final action items text length: {len(action_items_text)} chars")
    else:
        print("⚠️  No action items found in metadata!")
    
    # Format decisions
    decisions_text = ""
    if metadata.get("key_decisions"):
        decisions_text = "\n".join([f"• {item}" for item in metadata["key_decisions"]])
    
    # Format participants
    participants_text = ", ".join(metadata.get("participants", []))
    
    # Create detailed content from ALL sections
    detailed_content = ""
    if metadata.get("full_content"):
        section_parts = []
        for section_name, section_content in metadata["full_content"].items():
            if section_content:
                section_parts.append(f"━━━ {section_name.upper()} ━━━\n\n{section_content}")
        
        detailed_content = "\n\n" + "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n".join(section_parts)
    
    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Title": {
                "title": create_rich_text(metadata["title"])
            },
            "Date": {
                "date": {"start": today}
            },
            "Type": {
                "select": {"name": metadata["session_type"]}
            },
            "Summary": {
                "rich_text": create_rich_text(metadata.get("overview", ""))
            },
            "Action Items": {
                "rich_text": create_rich_text(action_items_text)
            },
            "Status": {
                "select": {"name": "New"}
            }
        }
    }
    
    # Add detailed content
    if detailed_content:
        data["properties"]["Detailed Notes"] = {
            "rich_text": create_rich_text(detailed_content)
        }
    
    # Add optional fields
    if decisions_text:
        data["properties"]["Key Decisions"] = {
            "rich_text": create_rich_text(decisions_text)
        }
    
    if participants_text:
        data["properties"]["Participants"] = {
            "rich_text": create_rich_text(participants_text)
        }

    try:
        response = ipv4_safe_request('post', NOTION_API_URL, headers=HEADERS, json=data)
        
        if response.status_code in [200, 201]:
            print(f"✅ Successfully created Notion entry: '{metadata['title']}'")
            print(f"📊 Content stats:")
            print(f"   • Total content length: {len(detailed_content)} characters")
            print(f"   • Action items: {len(metadata['action_items'])}")
            print(f"   • Action items text length: {len(action_items_text)} chars")
            print(f"   • Sections: {len(metadata.get('full_content', {}))}")
            return "Success"
        else:
            print(f"❌ Failed to create entry: {response.status_code} - {response.text}")
            return f"Error: {response.status_code}"
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return f"Error: {str(e)}"

def log_meeting_notes():
    """Log Meeting_Notes2.md to Notion - COMPREHENSIVE PARSING"""
    print("📝 Creating Notion entry from Meeting_Notes2.md...")
    print("🚀 COMPREHENSIVE ACTION ITEM EXTRACTION - All formats supported!")
    print("🛡️  DUPLICATE PREVENTION - Won't create duplicates!")
    
    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        print("❌ Missing NOTION_API_KEY or NOTION_DATABASE_ID")
        return
    
    filename = "Meeting_Notes2.md"
    
    if not os.path.exists(filename):
        print(f"❌ {filename} not found")
        return
    
    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
        
        if not content.strip():
            print("❌ File is empty")
            return
        
        print(f"📄 Source file size: {len(content)} characters")
        
        # Extract metadata with comprehensive parsing
        metadata = extract_meeting_metadata(content)
        
        print(f"📊 FINAL EXTRACTION RESULTS:")
        print(f"   • Title: {metadata['title']}")
        print(f"   • Type: {metadata['session_type']}")
        print(f"   • Sections captured: {len(metadata.get('full_content', {}))}")
        print(f"   • Action Items FOUND: {len(metadata['action_items'])}")
        print(f"   • Overview length: {len(metadata.get('overview', ''))} chars")
        
        if metadata['action_items']:
            print("🎯 ACTION ITEMS PREVIEW:")
            for i, action in enumerate(metadata['action_items'][:3]):
                print(f"   {i+1}. {action[:100]}...")
        else:
            print("❌ NO ACTION ITEMS EXTRACTED - Check markdown format!")
        
        # Create Notion entry
        result = create_notion_entry(metadata)
        print(f"🏁 Result: {result}")
        
    except Exception as e:
        print(f"❌ Error processing file: {str(e)}")

if __name__ == "__main__":
    log_meeting_notes()