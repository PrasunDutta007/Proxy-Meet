import streamlit as st
import os
import glob
import json
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Meeting Analyzer Dashboard", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        background: linear-gradient(90deg, #ff7e5f 0%, #feb47b 100%);
        padding: 0.5rem 1rem;
        border-radius: 5px;
        color: white;
        margin: 1rem 0;
    }
    .meeting-info-box {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
    .audio-section {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 12px;
        text-align: center;
        color: white;
        margin: 2rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Main header
st.markdown("""
<div class="main-header">
    <h1>🤖 PROXY-MEET 🤖</h1>
    <p>Comprehensive Meeting Analysis & Documentation</p>
</div>
""", unsafe_allow_html=True)

ARCHIVE_DIR = "archives"
# Get all meeting folders (both timestamped and latest_meeting)
all_meetings = []
if os.path.exists(ARCHIVE_DIR):
    for item in os.listdir(ARCHIVE_DIR):
        item_path = os.path.join(ARCHIVE_DIR, item)
        if os.path.isdir(item_path):
            all_meetings.append(item_path)

# Sort meetings with latest_meeting first, then by timestamp (newest first)
def sort_meetings(meeting_path):
    meeting_name = os.path.basename(meeting_path)
    if meeting_name == "latest_meeting":
        return "0000_latest"  # Ensures latest_meeting comes first
    else:
        return meeting_name

archives = sorted(all_meetings, key=sort_meetings, reverse=True)

if not archives:
    st.warning("⚠️ No archived meetings found yet.")
    st.info("Please ensure your meeting files are in the archives directory.")
else:
    # Sidebar for meeting selection
    with st.sidebar:
        st.header("📁 Meeting Selection")
        
        def format_meeting_name(path):
            name = os.path.basename(path)
            if name == "latest_meeting":
                return "🔥 Latest Meeting"
            elif name.startswith("meeting_"):
                # Format timestamp: meeting_2025-07-20_18-01-14 -> 2025-07-20 18:01:14
                try:
                    # Remove "meeting_" prefix
                    timestamp_part = name.replace("meeting_", "")
                    
                    # Split by underscore to get date and time parts
                    parts = timestamp_part.split("_")
                    if len(parts) >= 2:
                        date_part = parts[0]  # 2025-07-20
                        time_part = parts[1]  # 18-01-14
                        
                        # Convert time format from 18-01-14 to 18:01:14
                        formatted_time = time_part.replace("-", ":")
                        
                        return f"📅 {date_part} {formatted_time}"
                    else:
                        return f"📅 {timestamp_part}"
                except Exception as e:
                    return name.replace('_', ' ').title()
            else:
                return name.replace('_', ' ').title()
        
        selected = st.selectbox(
            "Choose a meeting:",
            archives,
            format_func=format_meeting_name
        )
        
        # Meeting info
        st.markdown("### 📋 Quick Info")
        meeting_name = os.path.basename(selected)
        
        if meeting_name == "latest_meeting":
            st.success("🔥 **Latest Meeting**")
            # Try to find what this links to
            try:
                if os.path.islink(selected):
                    actual_path = os.readlink(selected)
                    actual_name = os.path.basename(actual_path)
                    st.info(f"📂 **Links to:** {actual_name}")
                elif os.path.exists(selected):
                    st.info("📂 **Type:** Copy")
            except:
                pass
        elif meeting_name.startswith("meeting_"):
            # Parse timestamp from meeting folder name: meeting_2025-07-20_18-01-14
            try:
                # Remove "meeting_" prefix
                timestamp_part = meeting_name.replace("meeting_", "")
                
                # Split by underscore to get date and time parts
                parts = timestamp_part.split("_")
                if len(parts) >= 2:
                    date_part = parts[0]  # 2025-07-20 (already formatted)
                    time_part = parts[1]  # 18-01-14
                    
                    # Convert time format from 18-01-14 to 18:01:14
                    formatted_time = time_part.replace("-", ":")
                    
                    st.info(f"📅 **Date:** {date_part}")
                    st.info(f"🕐 **Time:** {formatted_time}")
                else:
                    st.info(f"**Meeting:** {meeting_name}")
            except Exception as e:
                st.info(f"**Meeting:** {meeting_name}")
        else:
            st.info(f"**Meeting:** {meeting_name}")
        
        # Check available files
        files_in_meeting = os.listdir(selected) if os.path.exists(selected) else []
        st.markdown("### 📄 Available Files")
        for file in files_in_meeting:
            if file.endswith('.mp3'):
                st.success(f"🎵 {file}")
            elif file.endswith('.json'):
                st.info(f"📊 {file}")
            elif file.endswith('.txt'):
                st.info(f"📝 {file}")
            elif file.endswith('.md'):
                st.warning(f"📑 {file}")

    # Main content area
    main_col1, main_col2 = st.columns([2, 1])
    
    with main_col1:
        # Audio Section
        audio_files = glob.glob(f"{selected}/*.mp3")
        if audio_files:
            st.markdown("""
            <div class="audio-section">
                <h2>🎧 Meeting Recording</h2>
                <p>Listen to the full meeting recording below</p>
            </div>
            """, unsafe_allow_html=True)
            
            for audio_file in audio_files:
                st.audio(audio_file)
                file_size = os.path.getsize(audio_file) / (1024 * 1024)  # MB
                st.caption(f"📁 File: {os.path.basename(audio_file)} | Size: {file_size:.1f} MB")
        
        # Transcript Section
        st.markdown('<div class="section-header"><h2>📄 Meeting Transcript</h2></div>', unsafe_allow_html=True)
        
        # Try to load JSON transcript first, then TXT
        transcript_json_files = glob.glob(f"{selected}/*.json")
        transcript_txt_files = glob.glob(f"{selected}/*.txt")
        
        transcript_content = ""
        transcript_metadata = {}
        
        if transcript_json_files:
            try:
                with open(transcript_json_files[0], 'r', encoding='utf-8') as f:
                    transcript_data = json.load(f)
                    transcript_metadata = transcript_data.get('metadata', {})
                    transcript_content = transcript_data.get('transcript', [])
                    
                    # Display metadata
                    with st.expander("📊 Transcript Metadata", expanded=False):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Method", transcript_metadata.get('transcription_method', 'Unknown'))
                        with col2:
                            st.metric("Utterances", transcript_metadata.get('total_utterances', 'Unknown'))
                        with col3:
                            created_at = transcript_metadata.get('created_at', '')
                            if created_at:
                                try:
                                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                                    st.metric("Created", dt.strftime('%Y-%m-%d %H:%M'))
                                except:
                                    st.metric("Created", created_at[:10])
                    
                    # Display transcript
                    if isinstance(transcript_content, list):
                        for i, entry in enumerate(transcript_content):
                            speaker = entry.get('speaker', f'Speaker {i+1}')
                            text = entry.get('text', '')
                            
                            # Speaker header
                            st.markdown(f"**🎤 {speaker}:**")
                            st.markdown(f"{text}")
                            st.markdown("---")
                    else:
                        st.write(transcript_content)
                    
            except Exception as e:
                st.error(f"Error loading JSON transcript: {e}")
                
        elif transcript_txt_files:
            try:
                with open(transcript_txt_files[0], 'r', encoding='utf-8') as f:
                    transcript_content = f.read()
                
                st.text_area("Full Transcript", transcript_content, height=400, key="transcript_text")
            except Exception as e:
                st.error(f"Error loading TXT transcript: {e}")
        else:
            st.warning("⚠️ No transcript files found in this meeting archive.")
    
    with main_col2:
        # Meeting Statistics
        st.markdown('<div class="section-header"><h3>📊 Meeting Stats</h3></div>', unsafe_allow_html=True)
        
        # Word count from transcript
        if transcript_content:
            if isinstance(transcript_content, list):
                word_count = sum(len(entry.get('text', '').split()) for entry in transcript_content)
                total_chars = sum(len(entry.get('text', '')) for entry in transcript_content)
            else:
                word_count = len(transcript_content.split())
                total_chars = len(transcript_content)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Words", f"{word_count:,}")
            with col2:
                st.metric("Characters", f"{total_chars:,}")
        
        # File information
        st.markdown("### 📁 File Details")
        for file in files_in_meeting:
            file_path = os.path.join(selected, file)
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                if file_size > 1024 * 1024:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                elif file_size > 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                else:
                    size_str = f"{file_size} bytes"
                
                st.markdown(f"**{file}**: {size_str}")

    # Meeting Notes Section
    st.markdown('<div class="section-header"><h2>📝 Meeting Notes & Analysis</h2></div>', unsafe_allow_html=True)
    
    # Look for markdown files in multiple locations
    note_files = []
    
    # 1. Check in the selected meeting directory
    note_files.extend(glob.glob(f"{selected}/*.md"))
    
    # 2. Check for global meeting notes in root (only if this is latest_meeting)
    if os.path.basename(selected) == "latest_meeting":
        note_files.extend(glob.glob("Meeting_Notes*.md"))
    
    # 3. Remove duplicates while preserving order
    seen = set()
    unique_note_files = []
    for file in note_files:
        if file not in seen:
            seen.add(file)
            unique_note_files.append(file)
    
    note_files = unique_note_files
    
    if note_files:
        # Create tabs for different note files
        if len(note_files) > 1:
            tab_names = []
            for file in note_files:
                filename = os.path.basename(file)
                if filename.startswith("Meeting_Notes"):
                    if "Meeting_Notes2" in filename:
                        tab_names.append("📋 Comprehensive Guide")
                    else:
                        tab_names.append("📋 Meeting Overview")
                else:
                    tab_names.append(f"📑 {filename}")
            
            tabs = st.tabs(tab_names)
            
            for i, (tab, note_file) in enumerate(zip(tabs, note_files)):
                with tab:
                    try:
                        with open(note_file, 'r', encoding='utf-8') as f:
                            notes_content = f.read()
                        
                        # Add file info
                        file_size = os.path.getsize(note_file) / 1024  # KB
                        st.caption(f"📄 Source: {os.path.basename(note_file)} | Size: {file_size:.1f} KB")
                        
                        st.markdown(notes_content)
                    except Exception as e:
                        st.error(f"Error loading notes from {note_file}: {e}")
        else:
            # Single notes file
            try:
                with open(note_files[0], 'r', encoding='utf-8') as f:
                    notes_content = f.read()
                
                # Add file info
                file_size = os.path.getsize(note_files[0]) / 1024  # KB
                st.caption(f"📄 Source: {os.path.basename(note_files[0])} | Size: {file_size:.1f} KB")
                
                st.markdown(notes_content)
            except Exception as e:
                st.error(f"Error loading notes: {e}")
    else:
        st.info("📝 No meeting notes found. Notes files should be in .md format.")
        st.markdown("""
        **Expected note file locations:**
        - `Meeting_Notes.md` (global notes)
        - `Meeting_Notes2.md` (global notes)
        - `{meeting_folder}/*.md` (meeting-specific notes)
        """)

    # Footer
    st.markdown("---")
    
    # Meeting Summary
    col1, col2, col3 = st.columns(3)
    with col1:
        total_meetings = len([m for m in archives if not os.path.basename(m) == "latest_meeting"])
        st.metric("Total Meetings", total_meetings)
    with col2:
        if archives:
            latest_meeting = [m for m in archives if os.path.basename(m) == "latest_meeting"]
            if latest_meeting:
                st.metric("Latest Available", "✅ Yes")
            else:
                st.metric("Latest Available", "❌ No")
    with col3:
        archive_size = 0
        for archive in archives:
            for root, dirs, files in os.walk(archive):
                for file in files:
                    try:
                        archive_size += os.path.getsize(os.path.join(root, file))
                    except:
                        continue
        size_mb = archive_size / (1024 * 1024)
        st.metric("Total Size", f"{size_mb:.1f} MB")
    
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 2rem;">
        <p>🤖 Powered by Meeting Analyzer AI | Built with Streamlit</p>
        <p>💡 Each meeting is automatically saved with a unique timestamp</p>
    </div>
    """, unsafe_allow_html=True)