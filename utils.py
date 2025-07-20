# utils.py (Audio-only version with local transcript storage)
import os
import json
import logging
from datetime import datetime
import assemblyai as aai
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from pydantic_ai import Agent, BinaryContent
import mimetypes

# Load environment variables from .env file
load_dotenv()

# API Keys
AAI_API_KEY = os.getenv("AAI_API_KEY")

# Configure AssemblyAI client
if AAI_API_KEY:
    aai.settings.api_key = AAI_API_KEY

# --- Pydantic Models for Transcript Processing ---
class SpeakerText(BaseModel):
    speaker: str
    text: str

class TranscriptionResult(BaseModel):
    speakers_text: List[SpeakerText]

# --- Helper Functions for Local Storage ---
def get_transcript_filename(audio_file_path: str, output_dir: Optional[str] = None) -> str:
    """Generate transcript filename based on audio file path."""
    base_name = os.path.splitext(os.path.basename(audio_file_path))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    transcript_filename = f"{base_name}_transcript_{timestamp}.json"
    
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        return os.path.join(output_dir, transcript_filename)
    else:
        # Store in the same directory as the audio file
        audio_dir = os.path.dirname(audio_file_path)
        return os.path.join(audio_dir, transcript_filename)

def save_transcript_locally(transcription_result: TranscriptionResult, 
                          audio_file_path: str, 
                          output_dir: Optional[str] = None,
                          method_used: str = "Unknown") -> Optional[str]:
    """Save transcript to local JSON file."""
    try:
        transcript_file_path = get_transcript_filename(audio_file_path, output_dir)
        
        # Prepare data for JSON serialization
        transcript_data = {
            "metadata": {
                "audio_file": os.path.basename(audio_file_path),
                "audio_file_full_path": os.path.abspath(audio_file_path),
                "transcription_method": method_used,
                "created_at": datetime.now().isoformat(),
                "total_utterances": len(transcription_result.speakers_text)
            },
            "transcript": [
                {
                    "speaker": speaker_text.speaker,
                    "text": speaker_text.text
                }
                for speaker_text in transcription_result.speakers_text
            ]
        }
        
        # Save to JSON file
        with open(transcript_file_path, 'w', encoding='utf-8') as f:
            json.dump(transcript_data, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Transcript saved locally to: {transcript_file_path}")
        return transcript_file_path
        
    except Exception as e:
        logging.error(f"Failed to save transcript locally: {e}")
        return None

def save_transcript_as_text(transcription_result: TranscriptionResult, 
                           audio_file_path: str, 
                           output_dir: Optional[str] = None,
                           method_used: str = "Unknown") -> Optional[str]:
    """Save transcript as a readable text file."""
    try:
        base_name = os.path.splitext(os.path.basename(audio_file_path))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        text_filename = f"{base_name}_transcript_{timestamp}.txt"
        
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            text_file_path = os.path.join(output_dir, text_filename)
        else:
            audio_dir = os.path.dirname(audio_file_path)
            text_file_path = os.path.join(audio_dir, text_filename)
        
        with open(text_file_path, 'w', encoding='utf-8') as f:
            f.write(f"Transcript for: {os.path.basename(audio_file_path)}\n")
            f.write(f"Transcription Method: {method_used}\n")
            f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Utterances: {len(transcription_result.speakers_text)}\n")
            f.write("="*50 + "\n\n")
            
            for speaker_text in transcription_result.speakers_text:
                f.write(f"{speaker_text.speaker}: {speaker_text.text}\n\n")
        
        logging.info(f"Text transcript saved to: {text_file_path}")
        return text_file_path
        
    except Exception as e:
        logging.error(f"Failed to save text transcript: {e}")
        return None

# --- Transcription Functions ---
def process_audio_assemblyai(audio_file_path: str, 
                           save_locally: bool = True, 
                           output_dir: Optional[str] = None,
                           save_as_text: bool = False) -> Optional[TranscriptionResult]:
    """Processes audio file using AssemblyAI and returns a structured transcript."""
    logging.info(f"Starting transcription with AssemblyAI for {audio_file_path}")
    
    # Check if file exists
    if not os.path.exists(audio_file_path):
        logging.error(f"Audio file not found: {audio_file_path}")
        return None
    
    # Check if API key is available
    if not AAI_API_KEY:
        logging.error("AssemblyAI API key not found in environment variables")
        return None
    
    try:
        config = aai.TranscriptionConfig(speaker_labels=True)
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio_file_path, config)

        if transcript.status == aai.TranscriptStatus.error:
            logging.error(f"AssemblyAI transcription failed: {transcript.error}")
            return None

        # Check if utterances exist
        if not transcript.utterances:
            logging.warning("No utterances found in transcript")
            return TranscriptionResult(speakers_text=[])

        speakers_text_list = [
            SpeakerText(speaker=f"Speaker {utt.speaker}", text=utt.text)
            for utt in transcript.utterances
            if utt.text and utt.text.strip()  # Only include non-empty text
        ]
        
        result = TranscriptionResult(speakers_text=speakers_text_list)
        logging.info(f"Successfully transcribed {len(speakers_text_list)} utterances")
        
        # Save locally if requested
        if save_locally:
            save_transcript_locally(result, audio_file_path, output_dir, "AssemblyAI")
            if save_as_text:
                save_transcript_as_text(result, audio_file_path, output_dir, "AssemblyAI")
        
        return result
        
    except Exception as e:
        logging.error(f"Error processing transcript with AssemblyAI: {e}", exc_info=True)
        return None


async def process_audio_Gemini(audio_file_path: str, 
                              save_locally: bool = True, 
                              output_dir: Optional[str] = None,
                              save_as_text: bool = False) -> Optional[TranscriptionResult]:
    """Processes an audio file using Gemini for transcription and speaker diarization."""
    
    # Check if file exists
    if not os.path.exists(audio_file_path):
        logging.error(f"Audio file not found: {audio_file_path}")
        return None
    
    Transcritor_agent = Agent(
        'google-gla:gemini-2.5-pro',
        output_type=TranscriptionResult,
        system_prompt=""" 
            You are an advanced AI conversation analyzer specializing in call center interactions.
            Analyze the provided audio file thoroughly.

            Your tasks are:
            1.  **Transcription:** Provide a full transcript of the conversation.
            2.  **Speaker Identification:** Identify and label each speaker. Use Speaker and letter like \"Speaker A\". """,
        name='Call_Transcritor',
    )
    
    try:
        # Check file size
        file_size = os.path.getsize(audio_file_path)
        if file_size == 0:
            logging.error("Audio file is empty.")
            return None
        
        logging.info(f"Processing audio file: {audio_file_path} (size: {file_size} bytes)")
        
        with open(audio_file_path, "rb") as f:
            audio_bytes = f.read()

        if not audio_bytes:
            logging.error("Failed to read audio file or file is empty.")
            return None

        media_type, _ = mimetypes.guess_type(audio_file_path)
        if not media_type or not media_type.startswith("audio/"):
            logging.warning(f"Could not determine a valid audio media type for {audio_file_path}. Defaulting to 'audio/mpeg'.")
            media_type = 'audio/mpeg'

        logging.info(f"Sending audio to Gemini with media type: {media_type}")
        
        # Fix: Proper type annotation and result handling
        result = await Transcritor_agent.run([
            BinaryContent(data=audio_bytes, media_type=media_type)
        ])

        # Fix: Access .data instead of .output
        if result and result.data:
            logging.info("Successfully received and parsed structured transcript from Gemini.")
            logging.info(f"Transcribed {len(result.data.speakers_text)} utterances")
            
            # Save locally if requested
            if save_locally:
                save_transcript_locally(result.data, audio_file_path, output_dir, "Gemini")
                if save_as_text:
                    save_transcript_as_text(result.data, audio_file_path, output_dir, "Gemini")
            
            return result.data
        else:
            logging.error("Gemini returned empty or invalid result")
            return None

    except Exception as e:
        logging.error(f"An error occurred during pydantic-ai Gemini processing: {e}", exc_info=True)
        return None


def get_transcription_fallback(audio_file_path: str, 
                             save_locally: bool = True, 
                             output_dir: Optional[str] = None,
                             save_as_text: bool = False) -> Optional[TranscriptionResult]:
    """
    Try both transcription methods with fallback.
    First tries AssemblyAI, then Gemini if that fails.
    """
    logging.info("Starting transcription with fallback strategy")
    
    # Try AssemblyAI first (faster and more reliable for basic transcription)
    try:
        result = process_audio_assemblyai(audio_file_path, save_locally, output_dir, save_as_text)
        if result and result.speakers_text:
            logging.info("Successfully transcribed using AssemblyAI")
            return result
        else:
            logging.warning("AssemblyAI transcription returned empty or failed")
    except Exception as e:
        logging.error(f"AssemblyAI transcription failed: {e}")
    
    # Fallback to Gemini
    try:
        import asyncio
        logging.info("Falling back to Gemini transcription")
        result = asyncio.run(process_audio_Gemini(audio_file_path, save_locally, output_dir, save_as_text))
        if result and result.speakers_text:
            logging.info("Successfully transcribed using Gemini")
            return result
        else:
            logging.error("Gemini transcription also failed or returned empty")
    except Exception as e:
        logging.error(f"Gemini transcription failed: {e}")
    
    logging.error("Both transcription methods failed")
    return None


# Main function that should be called from meeting_pipeline
def process_transcription(audio_file_path: str, 
                         save_locally: bool = True, 
                         output_dir: Optional[str] = None,
                         save_as_text: bool = True) -> Optional[TranscriptionResult]:
    """
    Main transcription function with comprehensive error handling and local storage.
    
    Args:
        audio_file_path: Path to the audio file to transcribe
        save_locally: Whether to save transcript locally (default: True)
        output_dir: Directory to save transcripts (default: same as audio file)
        save_as_text: Whether to also save as readable text file (default: True)
    
    Returns:
        TranscriptionResult object or None if failed
    """
    if not audio_file_path:
        logging.error("No audio file path provided")
        return None
    
    if not os.path.exists(audio_file_path):
        logging.error(f"Audio file does not exist: {audio_file_path}")
        return None
    
    try:
        # Use the fallback strategy
        result = get_transcription_fallback(audio_file_path, save_locally, output_dir, save_as_text)
        
        if result:
            logging.info(f"Transcription completed successfully with {len(result.speakers_text)} utterances")
            return result
        else:
            logging.error("All transcription attempts failed")
            return None
            
    except Exception as e:
        logging.error(f"Unexpected error in process_transcription: {e}", exc_info=True)
        return None


# Utility function to load transcript from saved file
def load_transcript_from_file(transcript_file_path: str) -> Optional[TranscriptionResult]:
    """Load a previously saved transcript from JSON file."""
    try:
        if not os.path.exists(transcript_file_path):
            logging.error(f"Transcript file not found: {transcript_file_path}")
            return None
        
        with open(transcript_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract transcript data
        speakers_text = [
            SpeakerText(speaker=item["speaker"], text=item["text"])
            for item in data.get("transcript", [])
        ]
        
        result = TranscriptionResult(speakers_text=speakers_text)
        logging.info(f"Loaded transcript with {len(speakers_text)} utterances from {transcript_file_path}")
        return result
        
    except Exception as e:
        logging.error(f"Failed to load transcript from file: {e}")
        return None