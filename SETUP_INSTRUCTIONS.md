# SleepGuard Pro - Setup Instructions for Another Laptop

## What to Include in ZIP File

Create a ZIP file containing:
- `main.py` - Main application file
- `sleep_detector.py` - Sleep detection module
- `data_logger.py` - Data logging module
- `requirements.txt` - Python dependencies
- `screenshots/` folder (optional - will be created if missing)
- `data/` folder (optional - will be created if missing)

## Step-by-Step Installation

### 1. Extract the ZIP File
- Extract the ZIP file to a folder on the target laptop (e.g., `C:\SleepGuardPro` or `Desktop\SleepGuardPro`)

### 2. Install Python (if not already installed)
- Download Python from https://www.python.org/downloads/
- Install Python 3.8 or higher
- **IMPORTANT:** Check "Add Python to PATH" during installation

### 3. Install Required Dependencies
Open Command Prompt or PowerShell and navigate to the extracted folder:

```bash
cd C:\SleepGuardPro
```

Then install dependencies:

```bash
pip install -r requirements.txt
```

Or install individually:

```bash
pip install opencv-python==4.8.1.78
pip install mediapipe==0.10.8
pip install numpy==1.24.3
pip install Pillow==10.1.0
pip install pyttsx3==2.90
pip install pywin32==306
pip install pyautogui==0.9.54
pip install pystray==0.19.5
pip install matplotlib==3.7.2
pip install pandas==2.0.3
pip install reportlab==4.0.4
```

### 4. Run the Application
```bash
python main.py
```

## Troubleshooting

### Camera Not Working
- Make sure no other application is using the camera
- Check camera permissions in Windows settings
- Try a different USB port if using external camera

### Import Errors
- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Verify Python version (3.8+): `python --version`

### Sound Not Working
- Check system volume
- Verify pyttsx3 installation: `pip install pyttsx3`

### System Tray Not Working
- pystray may have issues on some Windows versions
- The app will still work without system tray functionality

## System Requirements

- **OS:** Windows 10 or 11
- **Python:** 3.8 or higher
- **RAM:** 4GB minimum (8GB recommended)
- **Camera:** Webcam (built-in or external)
- **Storage:** 500MB free space

## Features Available

✅ Sleep Detection
✅ Hand-to-Face Detection (Bad Habits)
✅ Posture Detection
✅ Yawn Detection
✅ Head Nodding Detection
✅ Eye Blink Rate Tracking
✅ Screen Time Tracking
✅ Statistics Dashboard with Charts
✅ Daily/Weekly Reports
✅ PDF Report Export
✅ Email Reports
✅ Data Backup/Restore
✅ System Tray Minimization

## Data Storage

- **Screenshots:** Saved in `screenshots/` folder
- **Logs:** Saved in `data/` folder (JSON files)
- **Backups:** ZIP files created via Backup/Restore feature

## Email Setup (Optional)

To use email reports:
1. Enable 2-factor authentication on your Gmail account
2. Generate an App Password: https://myaccount.google.com/apppasswords
3. Use the App Password (not your regular password) when sending emails

## Support

If you encounter issues:
1. Check Python version: `python --version`
2. Reinstall dependencies: `pip install -r requirements.txt --upgrade`
3. Check camera is working in other applications
4. Run as Administrator if permission issues occur
