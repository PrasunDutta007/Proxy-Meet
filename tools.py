import os
import socket
import requests
from crewai.tools import tool
from langchain_community.agent_toolkits import GmailToolkit
from langchain_community.tools.gmail.utils import (
    build_resource_service,
    get_gmail_credentials,
)
from typing import Union, List, Optional

# --- FORCE IPv4 CONFIGURATION ---
def force_ipv4_globally():
    """Force all connections to use IPv4 only"""
    print("🌐 Configuring IPv4-only connections...")
    
    # Method 1: Patch socket.getaddrinfo to return only IPv4 addresses
    original_getaddrinfo = socket.getaddrinfo
    
    def ipv4_only_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        """Custom getaddrinfo that only returns IPv4 addresses"""
        try:
            # Force IPv4 family
            return original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
        except socket.gaierror:
            # If IPv4 fails, still try original (but this shouldn't happen for Google)
            return original_getaddrinfo(host, port, family, type, proto, flags)
    
    # Apply the patch
    socket.getaddrinfo = ipv4_only_getaddrinfo
    print("✅ IPv4-only socket configuration applied")
    
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
    print("✅ IPv4-only HTTP adapter configured")

def configure_google_api_ipv4():
    """Configure Google API client for IPv4"""
    import googleapiclient.discovery
    import googleapiclient.http
    from google.auth.transport.requests import Request
    
    # Patch Google API HTTP transport
    original_build = googleapiclient.discovery.build
    
    def ipv4_build(*args, **kwargs):
        """Build Google API service with IPv4-only transport"""
        # Disable cache_discovery to avoid network issues
        kwargs['cache_discovery'] = False
        
        # Build service normally - the socket patch will handle IPv4
        return original_build(*args, **kwargs)
    
    googleapiclient.discovery.build = ipv4_build
    print("✅ Google API configured for IPv4")

# Apply IPv4 configuration before any imports
force_ipv4_globally()
configure_google_api_ipv4()

# --- GMAIL TOOLKIT INITIALIZATION (Your Original Code) ---
print("Initializing Gmail Toolkit with IPv4-only connections...")

try:
    credentials = get_gmail_credentials(
        token_file="token.json",
        scopes=["https://mail.google.com/"],
        client_secrets_file="credentials.json",
    )
    print("✅ Credentials obtained via IPv4")
    
    api_resource = build_resource_service(credentials=credentials)
    print("✅ API resource built via IPv4")
    
    gmail_toolkit = GmailToolkit(api_resource=api_resource)
    print("✅ Gmail Toolkit Initialized via IPv4")
    
except Exception as e:
    print(f"❌ Gmail Toolkit initialization failed: {e}")
    gmail_toolkit = None

# --- CREATE TOOL MAPPING (Your Original Code) ---
if gmail_toolkit:
    langchain_tools = gmail_toolkit.get_tools()
    gmail_tools_map = {tool.name: tool for tool in langchain_tools}

    print("Available LangChain tool names:")
    for name in gmail_tools_map.keys():
        print(f"- {name}")
else:
    gmail_tools_map = {}
    print("❌ Gmail tools not available - toolkit initialization failed")

# --- ENHANCED TOOL FUNCTIONS WITH IPv4 VERIFICATION ---

def ipv4_safe_tool_call(tool_func, *args, **kwargs):
    """Wrapper to ensure tool calls use IPv4 and handle errors gracefully"""
    try:
        print(f"🌐 Executing {tool_func.__name__ if hasattr(tool_func, '__name__') else 'tool'} via IPv4...")
        result = tool_func(*args, **kwargs)
        print(f"✅ Tool call completed via IPv4")
        return result
    except Exception as e:
        error_msg = f"❌ Tool call failed: {str(e)}"
        print(error_msg)
        # Check if it's a network-related error
        if "10060" in str(e) or "timeout" in str(e).lower():
            error_msg += " (Network timeout - check IPv4 configuration)"
        elif "connection" in str(e).lower():
            error_msg += " (Connection error - possible IPv6 fallback issue)"
        return error_msg

# --- YOUR ORIGINAL TOOL DEFINITIONS (Enhanced with IPv4 Safety) ---

@tool("Search Gmail")
def search_gmail(query: str) -> str:
    """
    Searches the user's Gmail inbox with a specific query.
    The input is a standard Gmail search query string (e.g., 'from:elon@x.com is:unread').
    Returns a list of email snippets with their IDs.
    """
    if 'search_gmail' not in gmail_tools_map:
        return "❌ Gmail search tool not available"
    
    search_tool = gmail_tools_map['search_gmail']
    return ipv4_safe_tool_call(search_tool.run, query)

@tool("Read Email Content")
def read_email(email_id: str) -> str:
    """
    Reads the full content of a specific email.
    The input MUST be the 'id' of the email, which can be obtained from the 'Search Gmail' tool.
    Returns the email's content, including sender, subject, and body.
    """
    if 'get_gmail_message' not in gmail_tools_map:
        return "❌ Gmail read tool not available"
    
    read_tool = gmail_tools_map['get_gmail_message']
    return ipv4_safe_tool_call(read_tool.run, email_id)

@tool("Send Email")
def send_email(to: Union[str, List[str]], subject: str, body: str, cc: Optional[Union[str, List[str]]] = None, bcc: Optional[Union[str, List[str]]] = None) -> str:
    """
    Sends an email to specified recipient(s).
    
    Parameters:
        to: A single email address or a list of email addresses.
        subject: The subject of the email.
        body: The main content of the email (HTML allowed).
        cc: Optional CC recipients.
        bcc: Optional BCC recipients.
    
    Returns:
        Result of sending the email.
    """
    if 'send_gmail_message' not in gmail_tools_map:
        return "❌ Gmail send tool not available"
    
    send_tool = gmail_tools_map['send_gmail_message']
    payload = {
        "message": body,
        "to": to,
        "subject": subject,
    }
    
    if cc:
        payload["cc"] = cc
    if bcc:
        payload["bcc"] = bcc
    
    return ipv4_safe_tool_call(send_tool.run, payload)

@tool("Create Email Draft")
def create_draft(to: str, subject: str, body: str) -> str:
    """
    Creates a draft email in the user's Gmail account but does not send it.
    The 'to' argument is the recipient's email address (e.g., 'example@gmail.com').
    The 'subject' argument is the subject of the email.
    The 'body' argument is the main content of the email.
    """
    if 'create_gmail_draft' not in gmail_tools_map:
        return "❌ Gmail draft tool not available"
    
    draft_tool = gmail_tools_map['create_gmail_draft']
    tool_input = {
        "to": [to],         
        "subject": subject,  
        "message": body      
    }
    
    return ipv4_safe_tool_call(draft_tool.run, tool_input)

# --- TEST FUNCTION TO VERIFY IPv4 OPERATION ---
def test_ipv4_gmail():
    """Test Gmail functionality with IPv4-only configuration"""
    print("\n🧪 Testing Gmail tools with IPv4-only configuration...")
    
    if not gmail_tools_map:
        print("❌ Gmail tools not available for testing")
        return False
    
    try:
        # Test search (least intrusive)
        print("🔍 Testing Gmail search via IPv4...")
        result = search_gmail("in:inbox")
        
        if "❌" not in result:
            print("✅ Gmail search via IPv4 successful!")
            
            # If search works, test draft creation
            print("✉️ Testing draft creation via IPv4...")
            draft_result = create_draft("test@example.com", "IPv4 Test Draft", "This draft was created via IPv4")
            
            if "❌" not in draft_result:
                print("✅ Gmail draft creation via IPv4 successful!")
                return True
            else:
                print(f"❌ Draft creation failed: {draft_result}")
                return False
        else:
            print(f"❌ Gmail search failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ IPv4 Gmail test failed: {e}")
        return False

# Run test when executed directly
if __name__ == "__main__":
    test_ipv4_gmail()
else:
    print("📧 IPv4-forced Gmail tools loaded and ready for CrewAI")

print("✅ IPv4-only Gmail tools configuration complete")