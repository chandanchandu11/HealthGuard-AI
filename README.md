# SleepGuard Pro

**SleepGuard Pro** is an intelligent sleep detection and habit monitoring application that helps you stay awake and productive while working on your laptop at night.

## Features

- **Automatic Camera Access**: Automatically accesses webcam when application starts
- **Sleep Detection**: Detects when you close your eyes or fall asleep
- **Bad Habit Detection**: Monitors for pimple itching and beard rubbing
- **Smart Alerts**: Custom alert messages like "Wake up boss!" when sleep is detected
- **Automatic Screenshots**: Captures screenshots when you sleep and saves to E:/screenshort/
- **Real-time Monitoring**: Live camera feed with sleep statistics
- **Date & Time Tracking**: Records sleep times and dates

## Installation

1. Install Python 3.8 or higher
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Download dlib shape predictor model:
   - Download `shape_predictor_68_face_landmarks.dat` from: http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2
   - Extract and place in the project folder

## Usage

Run the application:
```bash
python main.py
```

## Screenshot Location

Screenshots are automatically saved to: `E:/screenshort/`

If drive E is not available, screenshots will be saved to: `screenshots/` (in the project directory)

## Requirements

- Windows OS
- Webcam
- Python 3.8+
- Local Drive E with "screenshort" folder (auto-created if not exists)
