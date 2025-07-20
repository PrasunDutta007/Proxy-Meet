import os
import time
import subprocess
import webbrowser
import sounddevice as sd
import queue
import threading
import json
import requests
import websocket
from typing import Optional
from dotenv import load_dotenv
from meeting_pipeline import process_file
import pyautogui
import pygetwindow as gw
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchWindowException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
import shutil

load_dotenv()

ZOOM_LINK = os.getenv("ZOOM_LINK")
ASSEMBLYAI_API_KEY = os.getenv("AAI_API_KEY")
BOT_NAME = "prasun"
RESPONSE_TEXT = "Hi, this is Prasun's assistant. Prasun is currently away, but I'm here to help!"

WAIT_INTERVAL = int(os.getenv("WAIT_INTERVAL", 3))  # Check every 3 seconds
MAX_WAIT_TIME = int(os.getenv("MAX_WAIT_TIME", 3600))

# Create unique meeting directory based on timestamp
OUTPUT_DIR = "archives"
meeting_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
CURRENT_MEETING_DIR = os.path.join(OUTPUT_DIR, f"meeting_{meeting_timestamp}")
OUTPUT_FILE = os.path.join(CURRENT_MEETING_DIR, "recording.mp3")

# Create directories
os.makedirs(CURRENT_MEETING_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Global variables for thread control
recording_active = threading.Event()
listening_active = threading.Event()
driver: Optional[webdriver.Chrome] = None
recorder_process: Optional[subprocess.Popen] = None


def move_meeting_files_to_folder():
    """Move generated meeting files from current directory to the meeting folder"""
    print(f"📁 Moving meeting analysis files to {CURRENT_MEETING_DIR}...")
    
    # Files that the CrewAI agent generates
    files_to_move = [
        "Meeting_Notes.md",
        "Meeting_Notes2.md"
    ]
    
    moved_files = []
    
    for filename in files_to_move:
        source_path = filename  # Current directory
        destination_path = os.path.join(CURRENT_MEETING_DIR, filename)
        
        if os.path.exists(source_path):
            try:
                shutil.move(source_path, destination_path)
                moved_files.append(filename)
                print(f"✅ Moved {filename} to meeting folder")
            except Exception as e:
                print(f"❌ Error moving {filename}: {e}")
        else:
            print(f"⚠️ File not found: {filename}")
    
    if moved_files:
        print(f"📁 Successfully moved {len(moved_files)} analysis files to meeting folder")
        print(f"📂 Meeting folder contents: {os.listdir(CURRENT_MEETING_DIR)}")
    else:
        print("⚠️ No analysis files found to move")


class AssemblyAIRealTimeTranscriber:
    def __init__(self, api_key: str, on_transcript_callback):
        self.api_key = api_key
        self.on_transcript_callback = on_transcript_callback
        self.ws = None
        self.audio_queue = queue.Queue()
        self.is_running = False
        
    def start_transcription(self) -> bool:
        response = requests.post(
            'https://api.assemblyai.com/v2/realtime/token',
            headers={'authorization': self.api_key},
            json={'expires_in': 3600}
        )           
        
        token = response.json()['token']
        
        ws_url = f"wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000&token={token}"
        
        def on_message(ws, message):
            data = json.loads(message)
            if data['message_type'] == 'FinalTranscript':
                transcript = data['text'].lower().strip()
                if transcript:
                    print(f"🎯 Transcribed: {transcript}")
                    self.on_transcript_callback(transcript)
        
        def on_error(ws, error):
            print(f"WebSocket error: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            print("WebSocket closed")
            self.is_running = False
        
        def on_open(ws):
            print("🔊 AssemblyAI WebSocket connected")
            self.is_running = True
            
            def send_audio():
                while self.is_running and listening_active.is_set():
                    try:
                        audio_data = self.audio_queue.get(timeout=1)
                        if audio_data is not None:
                            ws.send(audio_data, websocket.ABNF.OPCODE_BINARY)
                    except queue.Empty:
                        continue            
                    
                    except Exception as e:
                        print(f"Error sending audio: {e}")
                        break
            
            audio_thread = threading.Thread(target=send_audio, daemon=True)
            audio_thread.start()
        
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        
        ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        ws_thread.start()
        
        timeout = 10
        while not self.is_running and timeout > 0:
            time.sleep(0.1)
            timeout -= 0.1
        
        return self.is_running
    
    def add_audio_data(self, audio_data):
        if self.is_running:
            self.audio_queue.put(audio_data)
    
    def stop(self):
        self.is_running = False
        if self.ws:
            self.ws.close()

def on_transcript_received(transcript: str):
    if BOT_NAME in transcript:
        print(f"🗣 Detected name '{BOT_NAME}' in: '{transcript}'")
        respond_to_mention()

def respond_to_mention():
    print("🤖 Responding to mention...")
    
    try:
        subprocess.Popen([
            "powershell", 
            f"Add-Type –AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{RESPONSE_TEXT}')"
        ])
    except Exception as e:
        print(f"❌ Voice response failed: {e}")
    
    try:
        send_zoom_message(RESPONSE_TEXT)
    except Exception as e:
        print(f"❌ Chat response failed: {e}")

def send_zoom_message(message: str):
    try:
        zoom_windows = gw.getWindowsWithTitle("Zoom")
        if zoom_windows:
            zoom_windows[0].activate()
            time.sleep(0.5)
        
        pyautogui.hotkey('alt', 'h')
        time.sleep(1)
        pyautogui.write(message)
        time.sleep(0.5)
        pyautogui.press('enter')
        print(f"✅ Sent message: {message}")
        
    except Exception as e:
        print(f"❌ Failed to send Zoom message: {e}")

def check_meeting_ended() -> bool:
    """Check ONLY for the specific 'This meeting has been ended by host' modal"""
    global driver
    if not driver:
        return True
    
    try:
        # Check if driver is still alive
        driver.current_url
        
        # Check if browser window still exists
        if len(driver.window_handles) == 0:
            print("🛑 Browser window closed")
            return True
        
        # Check in default content first
        try:
            meeting_ended_elements = driver.find_elements(
                By.XPATH, 
                "//div[contains(@class, 'zm-modal-body-title') and contains(text(), 'This meeting has been ended by host')]"
            )
            if meeting_ended_elements:
                print("🛑 SPECIFIC meeting ended modal detected in default content")
                return True
        except Exception as e:
            print(f"⚠️ Error checking default content: {e}")
        
        # Check inside the webclient frame
        try:
            driver.switch_to.default_content()
            # Add None check before WebDriverWait
            wait = WebDriverWait(driver, 2)
            wait.until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, '//*[@id="webclient"]')))
            
            # ONLY check for the specific "This meeting has been ended by host" modal
            meeting_ended_elements = driver.find_elements(
                By.XPATH, 
                "//div[contains(@class, 'zm-modal-body-title') and contains(text(), 'This meeting has been ended by host')]"
            )
            if meeting_ended_elements:
                print("🛑 SPECIFIC meeting ended modal detected in webclient frame")
                driver.switch_to.default_content()
                return True
            
            driver.switch_to.default_content()
            
        except Exception as e:
            print(f"⚠️ Error checking webclient frame: {e}")
            try:
                driver.switch_to.default_content()
            except:
                pass
        
        return False  # Meeting is still active
        
    except (NoSuchWindowException, WebDriverException) as e:
        print(f"🛑 Browser/WebDriver error: {e}")
        return True
    except Exception as e:
        print(f"⚠️ Unexpected error checking meeting status: {e}")
        return False

def leave_zoom_meeting():
    """Properly leave the Zoom meeting"""
    global driver
    print("🚪 Attempting to leave Zoom meeting...")
    
    if not driver:
        print("⚠️ No driver available to leave meeting")
        return
    
    try:
        # ONLY use the driver to interact with Zoom - no pyautogui hotkeys
        
        # Method 1: Try clicking Leave button if it exists
        try:
            driver.switch_to.default_content()
            wait = WebDriverWait(driver, 5)
            wait.until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, '//*[@id="webclient"]')))
            
            # Look for Leave button
            leave_buttons = driver.find_elements(
                By.XPATH, 
                "//button[contains(text(), 'Leave') or contains(@aria-label, 'Leave')]"
            )
            if leave_buttons:
                leave_buttons[0].click()
                print("✅ Clicked Leave button")
                time.sleep(2)
                driver.switch_to.default_content()
                return  # Successfully left, don't try other methods
            
            driver.switch_to.default_content()
            
        except Exception as e:
            print(f"⚠️ Could not click Leave button: {e}")
        
        # Method 2: Try End Meeting button if we're the host
        try:
            driver.switch_to.default_content()
            wait = WebDriverWait(driver, 3)
            wait.until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, '//*[@id="webclient"]')))
            
            end_buttons = driver.find_elements(
                By.XPATH, 
                "//button[contains(text(), 'End') or contains(@aria-label, 'End')]"
            )
            if end_buttons:
                end_buttons[0].click()
                print("✅ Clicked End button")
                time.sleep(2)
                driver.switch_to.default_content()
                return  # Successfully ended, don't close browser
            
            driver.switch_to.default_content()
            
        except Exception as e:
            print(f"⚠️ Could not click End button: {e}")
        
        # Method 3: Navigate away from the meeting URL
        try:
            driver.get("about:blank")
            print("✅ Navigated away from meeting")
        except Exception as e:
            print(f"⚠️ Could not navigate away: {e}")
            
    except Exception as e:
        print(f"❌ Error leaving meeting: {e}")

def close_obs():
    """Close OBS application gracefully via batch file"""
    print("🎥 Closing OBS gracefully via batch file...")
    
    # Simplified batch file - no need for complex dialog handling
    batch_file_content = (
        '@echo off\n'
        'echo Closing OBS gracefully...\n'
        'taskkill /im obs64.exe >nul 2>&1\n'
        'taskkill /im obs32.exe >nul 2>&1\n'
        'timeout /t 2 /nobreak >nul\n'
        'REM Force close if still running\n'
        'taskkill /f /im obs64.exe >nul 2>&1\n'
        'taskkill /f /im obs32.exe >nul 2>&1\n'
        'echo OBS closed successfully\n'
    )
    
    batch_path = "close_obs.bat"
    try:
        with open(batch_path, "w") as f:
            f.write(batch_file_content)
        
        subprocess.run(["cmd", "/c", batch_path], check=True)
        print("✅ OBS closed gracefully")
        
        try:
            os.remove(batch_path)
        except:
            pass
            
    except Exception as e:
        print(f"❌ Error closing OBS: {e}")

def is_zoom_meeting_active() -> bool:
    """Check if Zoom meeting is still active"""
    return not check_meeting_ended()

def listen_for_bot_trigger():
    if not ASSEMBLYAI_API_KEY:
        print("❌ AssemblyAI API key not found in environment variables")
        return
    
    transcriber = AssemblyAIRealTimeTranscriber(ASSEMBLYAI_API_KEY, on_transcript_received)
    
    if not transcriber.start_transcription():
        print("❌ Failed to start AssemblyAI transcription")
        return
    
    def audio_callback(indata, frames, time, status):
        if status:
            print(f"Audio status: {status}")
        
        if listening_active.is_set():
            audio_int16 = (indata * 32767).astype('int16')
            transcriber.add_audio_data(audio_int16.tobytes())
    
    print("🔊 Voice trigger activated with AssemblyAI. Listening...")
    listening_active.set()
    
    try:
        with sd.RawInputStream(
            samplerate=16000, 
            blocksize=8000, 
            dtype='float32',
            channels=1, 
            callback=audio_callback
        ):
            while listening_active.is_set() and recording_active.is_set():
                time.sleep(0.1)
    except Exception as e:
        print(f"❌ Audio listening error: {e}")
    finally:
        transcriber.stop()
        print("🔇 Voice trigger stopped")

def launch_obs():
    """Launch OBS application with VirtualCam auto-start and disable shutdown check"""
    print("🎥 Launching OBS with VirtualCam and shutdown check disabled...")
    
    # Create batch file content with the --disable-shutdown-check flag
    batch_file_content = (
        '@echo off\n'
        'echo Launching OBS with VirtualCam and shutdown check disabled...\n'
        'cd /d "C:\\Program Files\\obs-studio\\bin\\64bit"\n'
        'if exist "obs64.exe" (\n'
        '    echo Starting OBS 64-bit with all flags\n'
        '    start "" "obs64.exe" --startvirtualcam --disable-shutdown-check --minimize-to-tray\n'
        ') else (\n'
        '    echo OBS 64-bit not found, trying 32-bit...\n'
        '    cd /d "C:\\Program Files (x86)\\obs-studio\\bin\\32bit"\n'
        '    if exist "obs32.exe" (\n'
        '        echo Starting OBS 32-bit with all flags\n'
        '        start "" "obs32.exe" --startvirtualcam --disable-shutdown-check --minimize-to-tray\n'
        '    ) else (\n'
        '        echo OBS not found in standard installation paths\n'
        '        echo Please check OBS installation\n'
        '    )\n'
        ')\n'
        'echo OBS launch completed\n'
    )
    
    batch_path = "launch_obs.bat"
    try:
        with open(batch_path, "w") as f:
            f.write(batch_file_content)
        
        # Execute the batch file
        subprocess.run(["cmd", "/c", batch_path], check=True)
        print("✅ OBS launched successfully with shutdown check disabled")
        
        # Clean up the batch file
        try:
            os.remove(batch_path)
        except:
            pass
            
        # Wait for OBS to start - reduced wait time since no dialogs expected
        time.sleep(3)
        print("✅ OBS startup complete - no safe mode dialogs expected")
            
    except Exception as e:
        print(f"❌ Error launching OBS via batch file: {e}")


def cleanup_and_exit():
    """Safe cleanup function that closes only what we opened"""
    global driver, recorder_process
    
    print("🧹 Starting safe cleanup...")
    
    # Stop recording and listening
    recording_active.clear()
    listening_active.clear()
    
    # Stop audio recording
    if recorder_process:
        print("🔴 Terminating recording process...")
        try:
            recorder_process.terminate()
            recorder_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("⚠️ Force killing recording process...")
            recorder_process.kill()
        print("🔴 Recording stopped.")
        recorder_process = None
    
    # Close ONLY the Zoom meeting driver (not all Chrome windows)
    if driver:
        try:
            print("🔧 Closing Zoom meeting browser window...")
            driver.quit()  # This only closes the driver's browser window
            driver = None
            print("✅ Zoom browser window closed")
        except Exception as e:
            print(f"⚠️ Error closing Zoom browser: {e}")
    
    # Close OBS via batch file at the end
    close_obs()
    
    print("✅ Safe cleanup completed")

def join_zoom_and_record() -> Optional[str]:
    global driver, recorder_process
    
    print(f"🚀 Starting new meeting session: {meeting_timestamp}")
    print(f"📁 Meeting files will be saved to: {CURRENT_MEETING_DIR}")
    
    
    print("🚀 Launching Zoom meeting via Selenium...")
    chrome_options = Options()
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--use-fake-ui-for-media-stream")
    chrome_options.add_experimental_option("detach", True)
    
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.get(ZOOM_LINK)
    except Exception as e:
        print(f"❌ Failed to initialize Chrome driver: {e}")
        return None

    # Zoom setup with proper None checks
    time.sleep(5)
    pyautogui.press('esc')
    time.sleep(5)

    try:
        cancel_btn = driver.find_element(By.XPATH, "//button[contains(text(),'Cancel')]")
        cancel_btn.click()
        print("✅ Cancel popup closed")
    except:
        print("❌ Cancel popup not found")

    time.sleep(5)
    try:
        decline_cookies = driver.find_element(By.XPATH, "//button[contains(text(),'Decline Cookies')]")
        decline_cookies.click()
        print("✅ Declined Cookies")
    except:
        print("❌ Could not find Decline Cookies button")    

    time.sleep(2)
    try:
        browser_link = driver.find_element(By.LINK_TEXT, "Join from your browser")
        browser_link.click()
        print("✅ Clicked 'Join from your browser'")
    except:
        print("❌ Could not click 'Join from your browser'")

    time.sleep(3)
    try:
        wait = WebDriverWait(driver, 10)
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, '//*[@id="webclient"]')))
        agree_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='wc_agree1']")))
        agree_btn.click()
        print("✅ Clicked I Agree")
    except Exception as e:
        print(f"❌ Could not click I Agree: {e}")

    time.sleep(2)
    try:
        driver.switch_to.default_content()
        print("✅ Switched to default content")
    except:
        print("❌ Could not switch to default content")

    time.sleep(5)
    try:
        wait = WebDriverWait(driver, 10)
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, '//*[@id="webclient"]')))
        mic_cam_btn = driver.find_element(By.XPATH, "//*[@id='ask-permission-button']")
        mic_cam_btn.click()
        print("✅ Clicked 'Use microphone and camera'")
    except Exception as e:
        print(f"❌ Could not click 'Use microphone and camera': {e}")

    time.sleep(2)
    driver.switch_to.default_content()

    time.sleep(2)
    try:
        pyautogui.press('tab', presses=3)
        pyautogui.press('enter')
        print("✅ Clicked 'Allow this time'")
    except:
        print("❌ Could not click 'Allow this time'")

    time.sleep(6)
    try:
        wait = WebDriverWait(driver, 10)
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, '//*[@id="webclient"]')))
        dropdown_btn = driver.find_element(By.XPATH, "//*[@id='root']/div/div[1]/div/div[1]/div/div/div[2]/button[2]")
        dropdown_btn.click()
        obs_option = wait.until(EC.element_to_be_clickable((
            By.CSS_SELECTOR, 
            'li[aria-label="Select a Camera OBS Virtual Camera"]'
        )))
        obs_option.click()
        print("✅ Selected OBS Virtual Camera")
        driver.switch_to.default_content()
    except Exception as e:
        print(f"❌ Could not select OBS Virtual Camera: {e}")

    time.sleep(2)
    try:
        wait = WebDriverWait(driver, 10)
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, '//*[@id="webclient"]')))
        dropdown_btn = driver.find_element(By.XPATH, "//*[@id='root']/div/div[1]/div/div[1]/div/div/div[1]/button[2]")
        dropdown_btn.click()
        spk_output = wait.until(EC.element_to_be_clickable((
            By.CSS_SELECTOR, 
            'li[aria-label="Select a Speaker CABLE Input (VB-Audio Virtual Cable)"]'
        )))
        spk_output.click()
        print("✅ Selected Speaker")
        driver.switch_to.default_content()
    except Exception as e:
        print(f"❌ Could not select Speaker: {e}")

    time.sleep(2)
    try:
        wait = WebDriverWait(driver, 10)
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, '//*[@id="webclient"]')))
        dropdown_btn = driver.find_element(By.XPATH, "//*[@id='root']/div/div[1]/div/div[1]/div/div/div[1]/button[2]")
        dropdown_btn.click()
        mic_input = wait.until(EC.element_to_be_clickable((
            By.CSS_SELECTOR, 
            'li[aria-label="Select a Microphone CABLE Output (VB-Audio Virtual Cable)"]'
        )))
        mic_input.click()
        print("✅ Selected Microphone")
        driver.switch_to.default_content()
    except Exception as e:
        print(f"❌ Could not select Microphone: {e}")

    time.sleep(3)
    try:
        wait = WebDriverWait(driver, 10)
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, '//*[@id="webclient"]')))
        name_input = wait.until(EC.element_to_be_clickable((By.ID, "input-for-name")))
        name_input.clear()
        name_input.send_keys("Prasun-Bot")
        print("✅ Name filled")
        driver.switch_to.default_content()
    except Exception as e:
        print(f"❌ Could not fill name: {e}")

    time.sleep(3)
    joined = False
    try:
        wait = WebDriverWait(driver, 10)
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, '//*[@id="webclient"]')))
        join_button = driver.find_element(By.XPATH, "//*[@id='root']/div/div[1]/div/div[2]/button")
        join_button.click()
        print("✅ Clicked Join")
        joined = True
        driver.switch_to.default_content()
    except Exception as e:
        print(f"❌ Could not click Join: {e}")

    if joined:
        print("🔴 Starting recording and voice trigger...")
        recording_active.set()
        
        record_cmd = [
            "ffmpeg", "-y", "-f", "dshow", "-i", "audio=CABLE Output (VB-Audio Virtual Cable)",
            OUTPUT_FILE
        ]
        recorder_process = subprocess.Popen(record_cmd)

        listener_thread = threading.Thread(target=listen_for_bot_trigger, daemon=True)
        listener_thread.start()

        try:
            start_time = time.time()
            last_check_time = time.time()
            
            print(f"🔍 Monitoring ONLY for 'This meeting has been ended by host' every {WAIT_INTERVAL} seconds...")
            
            while recording_active.is_set():
                current_time = time.time()
                
                if current_time - last_check_time >= WAIT_INTERVAL:
                    print("🔍 Checking for specific meeting end modal...")
                    if not is_zoom_meeting_active():
                        print("🛑 'This meeting has been ended by host' detected! Leaving meeting and stopping recording.")
                        
                        # First leave the meeting properly
                        leave_zoom_meeting()
                        time.sleep(3)  # Give time for leave to complete
                        
                        break
                    else:
                        print("✅ Meeting still active (no end modal detected)")
                    last_check_time = current_time
                
                if current_time - start_time >= MAX_WAIT_TIME:
                    print("⏰ Maximum recording time reached. Leaving meeting and stopping recording.")
                    leave_zoom_meeting()
                    break
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("⌨️ Recording stopped by user. Leaving meeting...")
            leave_zoom_meeting()
        finally:
            # Clean up
            cleanup_and_exit()

    return OUTPUT_FILE if os.path.exists(OUTPUT_FILE) else None

if __name__ == "__main__":
    try:
        print(f"📅 Starting meeting session at {meeting_timestamp}")
        print(f"📁 Meeting directory: {CURRENT_MEETING_DIR}")
        
        launch_obs()  # Only this line needed now!
        recorded_audio = join_zoom_and_record()
        
        if recorded_audio and os.path.exists(recorded_audio):
            print("🎵 Processing recorded audio...")
            process_file(recorded_audio)
            
            # NEW: Move the meeting analysis files to the meeting folder
            move_meeting_files_to_folder()
            
            print(f"✅ Meeting completed and saved to: {CURRENT_MEETING_DIR}")
            print("🌐 Refresh your Streamlit dashboard to see the latest meeting data!")
            subprocess.Popen(["streamlit", "run", "streamlit_app.py"])
            
    except Exception as e:
        print(f"❌ Fatal error: {e}")
    finally:
        recording_active.clear()
        listening_active.clear()
        if recorder_process:
            recorder_process.terminate()
        # Close OBS via batch file at the very end
        close_obs()