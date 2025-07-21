# 🤖 PROXY-MEET 🤖

An intelligent meeting automation system that acts as your proxy in online meetings, providing automated attendance, interacts when your name is called, 
generates structured meeting notes using multiple AI agents and logs it into Notion, and creates professional Minutes of Meeting (MoM) email drafts.


## 🏗️ Project Structure

```
Proxy-Meet/
├── venv/                                    # Virtual environment (excluded from git)
├── archives/                                # Meetings (excluded from git)
│   └── meeting_*/                           # Individual meetings 
│      ├── Meeting_Notes.md                  # Structured Notes using predefined format 
│      ├── Meeting_Notes2.md                 # AI-recommended format based on meeting type 
│      ├── recording.mp3                     # Meeting Recording 
│      ├── recording_transcript_*.json       # Full Transcript with speaker identification in json format 
│      └── recording_transcript_*.txt        # Full Transcript with speaker identification in human readable format 
├── credentials.json                         # Google API credentials (excluded from git)
├── .env                                     # Environment variables (excluded from git)
├── me.mp4                                   # Personal video/avatar (excluded from git)
├── token.json                               # OAuth tokens (excluded from git)
├── requirements.txt                         # Python dependencies
├── meeting_pipeline.py                      # Core meeting processing pipeline
├── tools.py                                 # Utility functions and tools
├── utils.py                                 # Helper utilities
├── zoom_bot.py                              # Zoom meeting automation bot
├── agents.py                                # AI agents for meeting interactions
├── notion_logger.py                         # Logging Notes into Notion
├── streamlit_app.py                         # Web interface using Streamlit
├── scheduler_runner.py                      # Automated scheduler execution
└── meeting_scheduler.py                     # Meeting scheduling and management

```

## 🚀 Features

- **Automated Meeting Attendance**: Joins scheduled Zoom meetings automatically
- **Intelligent Interaction**: AI-powered response via voice and in message window when your name is called
- **Meeting Logging**: Automatic audio and transcript logging in `archives/` 
- **Advanced Transcription**: Uses Google Gemini 2.5 Pro for accurate transcription with speaker diarization
- **Dual Note-taking Strategy**: 
  - Predefined structured format
  - AI-recommended format based on meeting type (progress updates, brainstorming, 1-on-1s, interviews, etc.)
- **Automated Email Distribution**: Creates MoM email drafts in Gmail
- **Multi-Agent Analysis**: Uses CrewAI with specialized agents for comprehensive meeting analysis
- **Professional Output**: Generates structured notes in Markdown format
- **Notion Logging**: Automatically logs both the meeting-notes in an organized mannner in Notion 
- **Streamlit Dashboard**: User-friendly web interface 


## 🏛️ Architecture
  
<div align="center">
  <img src="pics/architecture.png" alt="Architecture Diagram" style="max-width: 100%; height: auto;">
  <p><em>Proxy-Meet Architecture</em></p>
</div>

The application uses a multi-agent system powered by CrewAI:

1. **Meeting Analyst** - Extracts core content and themes
2. **Action Item Specialist** - Identifies actionable tasks
3. **Content Organizer** - Structures information hierarchically
4. **Quality Assurance Editor** - Ensures accuracy and formatting
5. **Meeting Strategist** - Determines optimal documentation framework
6. **Strategic Note Curator** - Applies sophisticated note-taking methodologies
7. **Email Assistant** - Formats and distributes meeting minutes



## 📋 Prerequisites

Before setting up Proxy-Meet, ensure you have:

- Python 3.8 or higher
- Google Cloud Platform account
- Zoom Pro account (for Zoom bot functionality)
- Webcam and microphone (for motion detection and audio)
- Stable internet connection

## 🛠️ Installation & Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/Proxy-Meet.git
cd Proxy-Meet
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Google Cloud Setup

#### 4.1 Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the following APIs:
   - Google Calendar API
   - Google Meet API (if available)
   - Google Drive API (for file storage)

#### 4.2 Create Service Account
1. Go to "IAM & Admin" > "Service Accounts"
2. Click "Create Service Account"
3. Fill in the details and create
4. Generate a JSON key file
5. Rename the file to `credentials.json` and place it in the project root

#### 4.3 OAuth 2.0 Setup (if needed)
1. Go to "APIs & Services" > "Credentials"
2. Create OAuth 2.0 Client IDs
3. Download the client configuration
4. The system will generate `token.json` on first authentication

### Step 5: Environment Configuration

Create a `.env` file in the project root:

```env
# Google APIs
GOOGLE_CALENDAR_ID=your_calendar_id@gmail.com
GOOGLE_CREDENTIALS_PATH=credentials.json
GOOGLE_TOKEN_PATH=token.json

# Zoom Configuration
ZOOM_API_KEY=your_zoom_api_key
ZOOM_API_SECRET=your_zoom_api_secret
ZOOM_ACCOUNT_ID=your_zoom_account_id

# Meeting Settings
DEFAULT_MEETING_DURATION=60
AUTO_JOIN_ENABLED=true
MOTION_DETECTION_ENABLED=true

# Logging
LOG_LEVEL=INFO
LOG_FILE_PATH=logs/proxy_meet.log

# AI Configuration
OPENAI_API_KEY=your_openai_api_key  # If using OpenAI for agents
ANTHROPIC_API_KEY=your_anthropic_api_key  # If using Anthropic
```

### Step 6: Personal Avatar Setup

1. Record a short video of yourself (`me.mp4`) for avatar purposes
2. Place it in the project root
3. Ensure good lighting and clear audio for best results

## 🎮 Usage

### Method 1: Streamlit Web Interface

Launch the web dashboard:

```bash
streamlit run streamlit_app.py
```

Navigate to `http://localhost:8501` in your browser to:
- View upcoming meetings
- Configure meeting settings
- Monitor active sessions
- Review meeting logs and reports

### Method 2: Command Line Interface

#### Start the Meeting Scheduler
```bash
python scheduler_runner.py
```

#### Run Individual Components
```bash
# Test meeting pipeline
python meeting_pipeline.py

# Start Zoom bot for specific meeting
python zoom_bot.py --meeting-id=MEETING_ID

# View motion logs
python motion_logger.py --view-logs
```

### Method 3: Automated Scheduling

Set up the scheduler to run automatically:

```bash
# Add to crontab for automated execution
# Run every 5 minutes to check for meetings
*/5 * * * * /path/to/your/venv/bin/python /path/to/Proxy-Meet/scheduler_runner.py
```

## ⚙️ Configuration

### Meeting Preferences

Edit the configuration in `streamlit_app.py` or through the web interface:

- **Auto-join timing**: How early to join meetings
- **Interaction level**: How active the bot should be
- **Recording settings**: Whether to record meetings
- **Notification preferences**: How to be alerted about meetings

### Agent Behavior

Customize AI agent responses in `agents.py`:

```python
# Example configuration
AGENT_CONFIG = {
    "personality": "professional",
    "response_frequency": "moderate",
    "topics_of_interest": ["project updates", "deadlines", "action items"],
    "auto_responses": True
}
```

## 📊 Features Deep Dive

### 1. Meeting Pipeline (`meeting_pipeline.py`)
- Pre-meeting preparation and validation
- Real-time meeting monitoring
- Post-meeting cleanup and reporting

### 2. AI Agents (`agents.py`)
- Natural language processing for meeting context
- Automated responses to common questions
- Intelligent participation decisions

### 3. Motion Logger (`motion_logger.py`)
- Webcam-based activity detection
- Attention monitoring during meetings
- Privacy-focused local processing

### 4. Zoom Integration (`zoom_bot.py`)
- Automated Zoom meeting joining
- Camera and microphone management
- Screen sharing capabilities

## 🐛 Troubleshooting

### Common Issues

#### Authentication Errors
```bash
# Re-authenticate with Google
rm token.json
python meeting_scheduler.py  # Will prompt for re-auth
```

#### Zoom Connection Issues
1. Verify Zoom API credentials in `.env`
2. Check Zoom account permissions
3. Ensure Zoom client is updated

#### Permission Errors
```bash
# Fix file permissions
chmod +x scheduler_runner.py
chmod 644 credentials.json
```

#### Module Import Errors
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

### Logs and Debugging

Enable debug logging:

```python
# In any Python file
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check log files:
```bash
# View recent logs
tail -f logs/proxy_meet.log

# Search for errors
grep ERROR logs/proxy_meet.log
```

## 🔒 Security & Privacy

- **Credentials**: Never commit `credentials.json`, `token.json`, or `.env` files
- **Video Data**: Personal video (`me.mp4`) stays local and is not uploaded
- **Meeting Data**: All meeting logs are stored locally by default
- **API Keys**: Store securely in environment variables
- **Network**: Use HTTPS for all external API calls

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This tool is for educational and productivity purposes. Always ensure compliance with your organization's policies and meeting platform terms of service. Use responsibly and with participants' knowledge when appropriate.

## 🆘 Support

If you encounter issues:

1. Check the [Issues](https://github.com/YOUR_USERNAME/Proxy-Meet/issues) page
2. Review the troubleshooting section above
3. Create a new issue with detailed description and logs

## 🙏 Acknowledgments

- Google Calendar API for scheduling integration
- Zoom SDK for meeting automation
- Streamlit for the beautiful web interface
- OpenCV for motion detection capabilities

---

**Made with ❤️ for productive meeting management**
