import os
import logging
from utils import process_transcription
from agents import run_crew_analysis
from notion_logger import log_meeting_notes

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def flatten_transcript(transcript_obj) -> str:
    """Convert structured transcript into flat string format for CrewAI input."""
    if not transcript_obj or not transcript_obj.speakers_text:
        return ""
    
    return "\n".join([f"{item.speaker}: {item.text}" for item in transcript_obj.speakers_text])

def process_file(audio_path):
    """
    Main processing function that handles the entire meeting pipeline:
    1. Transcription (with fallback)
    2. AI analysis
    3. Notion logging
    """
    print("🎵 Starting meeting processing pipeline...")
    
    # Validate audio file
    if not audio_path or not os.path.exists(audio_path):
        raise Exception(f"❌ Audio file not found: {audio_path}")
    
    file_size = os.path.getsize(audio_path)
    if file_size == 0:
        raise Exception(f"❌ Audio file is empty: {audio_path}")
    
    print(f"🔍 Processing audio file: {audio_path} ({file_size} bytes)")
    
    # Step 1: Transcription with built-in fallback and error handling
    print("🔍 Transcribing audio (AssemblyAI → Gemini fallback)...")
    transcript = process_transcription(audio_path)

    if transcript is None or not transcript.speakers_text:
        raise Exception("❗ Transcription failed using both AssemblyAI and Gemini, or transcript is empty.")

    print(f"✅ Transcription completed! Found {len(transcript.speakers_text)} utterances")
    
    # Step 2: Flatten transcript for AI analysis
    print("📄 Preparing transcript for AI analysis...")
    transcript_text = flatten_transcript(transcript)
    
    if not transcript_text.strip():
        raise Exception("❌ Flattened transcript is empty - no meaningful content to analyze")
    
    print(f"📄 Transcript prepared ({len(transcript_text)} characters)")

    # Step 3: AI Analysis
    print("🤖 Running AI crew analysis...")
    try:
        ai_results = run_crew_analysis(transcript_text)
        print("✅ AI analysis completed!")
    except Exception as e:
        print(f"⚠️ AI analysis failed: {e}")
        # You might want to decide if this should be fatal or continue to logging
        logging.error(f"AI analysis failed: {e}")
        ai_results = None

    # Step 4: Notion logging
    print("📝 Logging results to Notion...")
    try:
        log_meeting_notes()  # This reads Meeting_Notes.md + Meeting_Notes2.md
        print("✅ Notion logging completed!")
    except Exception as e:
        print(f"⚠️ Notion logging failed: {e}")
        logging.error(f"Notion logging failed: {e}")
        # Continue execution even if Notion logging fails

    print("🎉 Meeting processing pipeline completed successfully!")
    
    # Return results for potential further use
    return {
        'transcript': transcript,
        'transcript_text': transcript_text,
        'ai_results': ai_results,
        'audio_file': audio_path
    }

def process_file_safe(audio_path):
    """
    Safe wrapper for process_file that handles exceptions gracefully.
    Use this if you want the program to continue even if processing fails.
    """
    try:
        return process_file(audio_path)
    except Exception as e:
        print(f"❌ Meeting processing failed: {e}")
        logging.error(f"Meeting processing failed for {audio_path}: {e}", exc_info=True)
        return None

