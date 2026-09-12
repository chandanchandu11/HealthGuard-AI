import cv2
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox, Toplevel, filedialog
from PIL import Image, ImageTk
import threading
import time
from datetime import datetime
import os
from sleep_detector import SleepDetector
from data_logger import DataLogger
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import pystray
from pystray import MenuItem as item
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

class SleepGuardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SleepGuard Pro - Sleep Detection System")
        self.root.geometry("1200x800")
        self.root.configure(bg="#1e1e1e")
        
        # Camera
        self.cap = None
        self.running = False
        
        # GUI variables - must be initialized before detector
        self.status_var = tk.StringVar(value="Ready")
        self.ear_var = tk.StringVar(value="EAR: --")
        self.sleep_count_var = tk.StringVar(value="Sleep Episodes: 0")
        self.total_sleep_var = tk.StringVar(value="Total Sleep Time: 0.0s")
        self.current_time_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.screenshot_count_var = tk.StringVar(value="Screenshots: 0")
        self.habit_count_var = tk.StringVar(value="Bad Habit Episodes: 0")
        self.alert_message_var = tk.StringVar(value="Wake up boss!")
        self.screen_time_var = tk.StringVar(value="Screen Time: 0m 0s")
        
        # Statistics
        self.sleep_episodes = 0
        self.screenshot_count = 0
        self.habit_episodes = 0
        
        # State tracking for alerts
        self.was_sleeping = False
        self.was_bad_habit = False
        
        # Alert timing
        self.last_sleep_alert_time = 0
        self.last_habit_alert_time = 0
        self.alert_interval = 2.0  # Seconds between repeated alerts
        
        # Screen time tracking
        self.session_start_time = time.time()
        self.total_screen_time = 0
        
        # Initialize sleep detector (after GUI variables are set)
        try:
            self.detector = SleepDetector()
            self.detector.on_sleep_detected = self.on_sleep_detected_callback
            self.detector.on_habit_detected = self.on_habit_detected_callback
            self.detector.set_custom_alert_message(self.alert_message_var.get())
        except Exception as e:
            messagebox.showerror("Error", f"Failed to initialize sleep detector: {e}")
            return
        
        # Initialize data logger
        self.data_logger = DataLogger()
        
        # System tray icon
        self.tray_icon = None
        self.minimized_to_tray = False
        
        # Create GUI
        self.create_gui()
        
        # Start time update
        self.update_time()
        
        # Auto-start camera
        self.start_camera()
        
        # Handle window minimize event
        self.root.bind("<Unmap>", self.on_window_minimize)
    
    def setup_system_tray(self):
        """Setup system tray icon"""
        try:
            # Create a simple icon image
            icon_image = Image.new('RGB', (64, 64), color='#1e1e1e')
            
            # Create tray icon
            menu = pystray.Menu(
                item('Show Window', self.show_window),
                item('Hide Window', self.hide_window),
                item('Exit', self.quit_app)
            )
            
            self.tray_icon = pystray.Icon("SleepGuard Pro", icon_image, "SleepGuard Pro", menu)
            
            # Run tray icon in separate thread
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except Exception as e:
            print(f"Error setting up system tray: {e}")
    
    def on_window_minimize(self, event):
        """Handle window minimize event"""
        if self.root.state() == 'iconic':
            self.hide_window()
    
    def hide_window(self):
        """Hide window to system tray"""
        self.root.withdraw()
        self.minimized_to_tray = True
    
    def show_window(self):
        """Show window from system tray"""
        self.root.deiconify()
        self.root.lift()
        self.minimized_to_tray = False
    
    def quit_app(self, icon=None, item=None):
        """Quit application"""
        self.running = False
        if hasattr(self, 'cap') and self.cap:
            self.cap.release()
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.quit()
        self.root.destroy()
    
    def create_gui(self):
        """Create the GUI layout"""
        # Header
        header_frame = tk.Frame(self.root, bg="#2d2d2d", height=60)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        title_label = tk.Label(
            header_frame, 
            text="🛡️ SleepGuard Pro", 
            font=("Arial", 24, "bold"),
            bg="#2d2d2d",
            fg="#00ff88"
        )
        title_label.pack(pady=10)
        
        # Main content area
        main_frame = tk.Frame(self.root, bg="#1e1e1e")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Camera feed
        left_panel = tk.Frame(main_frame, bg="#2d2d2d", width=700)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        camera_label = tk.Label(
            left_panel,
            text="Camera Feed",
            font=("Arial", 14, "bold"),
            bg="#2d2d2d",
            fg="white"
        )
        camera_label.pack(pady=10)
        
        self.video_label = tk.Label(left_panel, bg="black")
        self.video_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Right panel - Statistics and controls
        right_panel = tk.Frame(main_frame, bg="#2d2d2d", width=400)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        
        # Status section
        status_frame = tk.LabelFrame(
            right_panel,
            text="Status",
            font=("Arial", 12, "bold"),
            bg="#2d2d2d",
            fg="white"
        )
        status_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.status_label = tk.Label(
            status_frame,
            textvariable=self.status_var,
            font=("Arial", 14, "bold"),
            bg="#2d2d2d",
            fg="#00ff88"
        )
        self.status_label.pack(pady=10)
        
        # Statistics section
        stats_frame = tk.LabelFrame(
            right_panel,
            text="Sleep Statistics",
            font=("Arial", 12, "bold"),
            bg="#2d2d2d",
            fg="white"
        )
        stats_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # EAR display
        ear_label = tk.Label(
            stats_frame,
            textvariable=self.ear_var,
            font=("Arial", 12),
            bg="#2d2d2d",
            fg="white"
        )
        ear_label.pack(anchor=tk.W, padx=10, pady=5)
        
        # Sleep count
        sleep_count_label = tk.Label(
            stats_frame,
            textvariable=self.sleep_count_var,
            font=("Arial", 12),
            bg="#2d2d2d",
            fg="white"
        )
        sleep_count_label.pack(anchor=tk.W, padx=10, pady=5)
        
        # Total sleep time
        total_sleep_label = tk.Label(
            stats_frame,
            textvariable=self.total_sleep_var,
            font=("Arial", 12),
            bg="#2d2d2d",
            fg="white"
        )
        total_sleep_label.pack(anchor=tk.W, padx=10, pady=5)
        
        # Screenshot count
        screenshot_label = tk.Label(
            stats_frame,
            textvariable=self.screenshot_count_var,
            font=("Arial", 12),
            bg="#2d2d2d",
            fg="white"
        )
        screenshot_label.pack(anchor=tk.W, padx=10, pady=5)
        
        # Bad habit count
        habit_label = tk.Label(
            stats_frame,
            textvariable=self.habit_count_var,
            font=("Arial", 12),
            bg="#2d2d2d",
            fg="white"
        )
        habit_label.pack(anchor=tk.W, padx=10, pady=5)
        
        # Screen time
        screen_time_label = tk.Label(
            stats_frame,
            textvariable=self.screen_time_var,
            font=("Arial", 12),
            bg="#2d2d2d",
            fg="#00aaff"
        )
        screen_time_label.pack(anchor=tk.W, padx=10, pady=5)
        
        # Time section
        time_frame = tk.LabelFrame(
            right_panel,
            text="Current Time",
            font=("Arial", 12, "bold"),
            bg="#2d2d2d",
            fg="white"
        )
        time_frame.pack(fill=tk.X, padx=10, pady=10)
        
        time_label = tk.Label(
            time_frame,
            textvariable=self.current_time_var,
            font=("Arial", 14),
            bg="#2d2d2d",
            fg="#00aaff"
        )
        time_label.pack(pady=10)
        
        # Controls section
        controls_frame = tk.LabelFrame(
            right_panel,
            text="Controls",
            font=("Arial", 12, "bold"),
            bg="#2d2d2d",
            fg="white"
        )
        controls_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Alert message section
        alert_frame = tk.LabelFrame(
            right_panel,
            text="Alert Message",
            font=("Arial", 12, "bold"),
            bg="#2d2d2d",
            fg="white"
        )
        alert_frame.pack(fill=tk.X, padx=10, pady=10)
        
        alert_label = tk.Label(
            alert_frame,
            text="Custom wake-up message:",
            font=("Arial", 10),
            bg="#2d2d2d",
            fg="white"
        )
        alert_label.pack(anchor=tk.W, padx=10, pady=5)
        
        alert_entry = tk.Entry(
            alert_frame,
            textvariable=self.alert_message_var,
            font=("Arial", 10),
            bg="#3d3d3d",
            fg="white",
            insertbackground="white"
        )
        alert_entry.pack(fill=tk.X, padx=10, pady=5)
        
        update_alert_btn = tk.Button(
            alert_frame,
            text="Update Alert Message",
            font=("Arial", 10),
            bg="#00aa00",
            fg="white",
            command=self.update_alert_message,
            relief=tk.RAISED,
            bd=3
        )
        update_alert_btn.pack(fill=tk.X, padx=10, pady=5)
        
        # Start/Stop button
        self.start_stop_btn = tk.Button(
            controls_frame,
            text="Stop Camera",
            font=("Arial", 12, "bold"),
            bg="#ff4444",
            fg="white",
            command=self.toggle_camera,
            relief=tk.RAISED,
            bd=3
        )
        self.start_stop_btn.pack(fill=tk.X, padx=10, pady=5)
        
        # Reset stats button
        reset_btn = tk.Button(
            controls_frame,
            text="Reset Statistics",
            font=("Arial", 12),
            bg="#ffaa00",
            fg="white",
            command=self.reset_stats,
            relief=tk.RAISED,
            bd=3
        )
        reset_btn.pack(fill=tk.X, padx=10, pady=5)
        
        # Manual screenshot button
        screenshot_btn = tk.Button(
            controls_frame,
            text="Take Screenshot",
            font=("Arial", 12),
            bg="#00aaff",
            fg="white",
            command=self.manual_screenshot,
            relief=tk.RAISED,
            bd=3
        )
        screenshot_btn.pack(fill=tk.X, padx=10, pady=5)
        
        # Statistics dashboard button
        stats_btn = tk.Button(
            controls_frame,
            text="Statistics Dashboard",
            font=("Arial", 12),
            bg="#9900ff",
            fg="white",
            command=self.show_statistics_dashboard,
            relief=tk.RAISED,
            bd=3
        )
        stats_btn.pack(fill=tk.X, padx=10, pady=5)
        
        # Generate report button
        report_btn = tk.Button(
            controls_frame,
            text="Generate Report",
            font=("Arial", 12),
            bg="#ff9900",
            fg="white",
            command=self.generate_report,
            relief=tk.RAISED,
            bd=3
        )
        report_btn.pack(fill=tk.X, padx=10, pady=5)
        
        # Backup/Restore button
        backup_btn = tk.Button(
            controls_frame,
            text="Backup/Restore Data",
            font=("Arial", 12),
            bg="#ff6600",
            fg="white",
            command=self.backup_restore_data,
            relief=tk.RAISED,
            bd=3
        )
        backup_btn.pack(fill=tk.X, padx=10, pady=5)
        
        # Info section
        info_frame = tk.LabelFrame(
            right_panel,
            text="Information",
            font=("Arial", 12, "bold"),
            bg="#2d2d2d",
            fg="white"
        )
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        info_text = tk.Label(
            info_frame,
            text="Screenshots saved to:\nE:/screenshort/",
            font=("Arial", 10),
            bg="#2d2d2d",
            fg="#aaaaaa",
            justify=tk.CENTER
        )
        info_text.pack(pady=10)
    
    def update_time(self):
        """Update current time display and screen time"""
        self.current_time_var.set(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        # Update screen time
        elapsed = time.time() - self.session_start_time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        self.screen_time_var.set(f"Screen Time: {minutes}m {seconds}s")
        
        self.root.after(1000, self.update_time)
    
    def start_camera(self):
        """Start the camera"""
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                messagebox.showerror("Error", "Could not access camera")
                return
            
            self.running = True
            self.status_var.set("Monitoring Active")
            self.status_label.config(fg="#00ff88")
            
            # Start video processing thread
            self.video_thread = threading.Thread(target=self.process_video, daemon=True)
            self.video_thread.start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start camera: {e}")
    
    def stop_camera(self):
        """Stop the camera"""
        self.running = False
        if self.cap:
            self.cap.release()
        self.status_var.set("Camera Stopped")
        self.status_label.config(fg="#ff4444")
    
    def toggle_camera(self):
        """Toggle camera on/off"""
        if self.running:
            self.stop_camera()
            self.start_stop_btn.config(text="Start Camera", bg="#00ff00")
        else:
            self.start_camera()
            self.start_stop_btn.config(text="Stop Camera", bg="#ff4444")
    
    def process_video(self):
        """Process video frames"""
        while self.running:
            try:
                ret, frame = self.cap.read()
                if not ret:
                    break
                
                # Get facial landmarks, hand landmarks, and pose landmarks
                landmarks, face_results, hand_results, pose_results = self.detector.get_facial_landmarks(frame)
                
                # Detect sleep
                is_sleeping, ear = self.detector.detect_sleep(landmarks)
                
                # Track blink rate
                blink_rate = self.detector.track_blinks(ear)
                
                # Detect bad habits (hand touching face)
                is_bad_habit, hand_distance = self.detector.detect_bad_habits(landmarks, hand_results)
                
                # Detect posture issues
                is_bad_posture, posture_score = self.detector.detect_posture(pose_results)
                
                # Detect yawning
                is_yawning, yawn_score = self.detector.detect_yawn(landmarks)
                
                # Detect head nodding
                is_head_nodding, nod_score = self.detector.detect_head_nodding(landmarks)
                
                # Draw on frame
                frame = self.draw_on_frame(frame, landmarks, hand_results, pose_results, is_sleeping, ear, is_bad_habit, is_bad_posture, is_yawning, is_head_nodding, blink_rate)
                
                # Update GUI
                self.update_gui(frame, ear, is_sleeping, is_bad_habit, is_bad_posture, is_yawning, is_head_nodding, blink_rate)
                
                # Trigger sleep alert - on state change OR periodically while sleeping
                current_time = time.time()
                if is_sleeping:
                    if not self.was_sleeping:
                        # First time entering sleep state
                        self.detector.trigger_sleep_alert()
                        self.last_sleep_alert_time = current_time
                    elif current_time - self.last_sleep_alert_time > self.alert_interval:
                        # Repeat alert periodically while sleeping
                        self.detector.trigger_sleep_alert()
                        self.last_sleep_alert_time = current_time
                
                # Trigger bad habit alert - on state change OR periodically while touching
                if is_bad_habit:
                    if not self.was_bad_habit:
                        # First time entering bad habit state
                        self.detector.trigger_bad_habit_alert()
                        self.last_habit_alert_time = current_time
                    elif current_time - self.last_habit_alert_time > self.alert_interval:
                        # Repeat alert periodically while touching face
                        self.detector.trigger_bad_habit_alert()
                        self.last_habit_alert_time = current_time
                
                # Update state tracking
                self.was_sleeping = is_sleeping
                self.was_bad_habit = is_bad_habit
                
                time.sleep(0.033)  # ~30 FPS
                
            except Exception as e:
                print(f"Error processing video: {e}")
                import traceback
                traceback.print_exc()
                break
    
    def draw_on_frame(self, frame, landmarks, hand_results, pose_results, is_sleeping, ear, is_bad_habit, is_bad_posture, is_yawning, is_head_nodding, blink_rate):
        """Draw visual indicators on frame"""
        h, w = frame.shape[:2]
        
        if landmarks:
            # Draw face mesh landmarks
            for idx, landmark in enumerate(landmarks.landmark):
                x = int(landmark.x * w)
                y = int(landmark.y * h)
                cv2.circle(frame, (x, y), 1, (0, 255, 0), -1)
            
            # Draw eye contours using MediaPipe landmarks
            # Left eye: 33, 160, 158, 133, 153, 144
            # Right eye: 362, 385, 387, 373, 380, 373
            left_eye_indices = [33, 160, 158, 133, 153, 144]
            right_eye_indices = [362, 385, 387, 373, 380, 373]
            
            left_eye_points = []
            right_eye_points = []
            
            for idx in left_eye_indices:
                x = int(landmarks.landmark[idx].x * w)
                y = int(landmarks.landmark[idx].y * h)
                left_eye_points.append([x, y])
            
            for idx in right_eye_indices:
                x = int(landmarks.landmark[idx].x * w)
                y = int(landmarks.landmark[idx].y * h)
                right_eye_points.append([x, y])
            
            left_eye_points = np.array(left_eye_points, dtype=np.int32)
            right_eye_points = np.array(right_eye_points, dtype=np.int32)
            
            left_eye_hull = cv2.convexHull(left_eye_points)
            right_eye_hull = cv2.convexHull(right_eye_points)
            
            eye_color = (0, 0, 255) if is_sleeping else (0, 255, 0)
            cv2.drawContours(frame, [left_eye_hull], -1, eye_color, 2)
            cv2.drawContours(frame, [right_eye_hull], -1, eye_color, 2)
        
        # Draw hand landmarks
        if hand_results and hand_results.multi_hand_landmarks:
            for hand_landmarks in hand_results.multi_hand_landmarks:
                for idx, landmark in enumerate(hand_landmarks.landmark):
                    x = int(landmark.x * w)
                    y = int(landmark.y * h)
                    # Draw fingertips in different color
                    if idx in [4, 8, 12, 16, 20]:  # Fingertips
                        cv2.circle(frame, (x, y), 5, (255, 0, 255), -1)
                    else:
                        cv2.circle(frame, (x, y), 2, (0, 255, 255), -1)
        
        # Draw status
        if is_bad_habit:
            status_text = "HAND TOUCHING FACE!"
            status_color = (255, 0, 255)  # Purple for bad habit
        elif is_sleeping:
            status_text = "SLEEPING!"
            status_color = (0, 0, 255)  # Red for sleep
        elif is_bad_posture:
            status_text = "BAD POSTURE!"
            status_color = (255, 165, 0)  # Orange for posture
        elif is_yawning:
            status_text = "YAWNING!"
            status_color = (255, 255, 0)  # Yellow for yawning
        elif is_head_nodding:
            status_text = "HEAD NODDING!"
            status_color = (0, 255, 255)  # Cyan for head nodding
        else:
            status_text = "AWAKE"
            status_color = (0, 255, 0)  # Green for awake
        
        cv2.putText(frame, f"Status: {status_text}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
        
        cv2.putText(frame, f"EAR: {ear:.2f}", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.putText(frame, f"Blinks/min: {blink_rate}", (10, 90), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Draw pose landmarks if available
        if pose_results and pose_results.pose_landmarks:
            for idx, landmark in enumerate(pose_results.pose_landmarks.landmark):
                x = int(landmark.x * w)
                y = int(landmark.y * h)
                cv2.circle(frame, (x, y), 3, (0, 255, 0), -1)
        
        # Draw timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, timestamp, (10, frame.shape[0] - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return frame
    
    def update_gui(self, frame, ear, is_sleeping, is_bad_habit, is_bad_posture, is_yawning, is_head_nodding, blink_rate):
        """Update GUI with current frame and statistics"""
        try:
            # Convert frame to display format
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_pil = Image.fromarray(frame_rgb)
            frame_pil = frame_pil.resize((640, 480))
            frame_tk = ImageTk.PhotoImage(frame_pil)
            
            # Update video label
            self.video_label.config(image=frame_tk)
            self.video_label.image = frame_tk
            
            # Update statistics
            self.ear_var.set(f"EAR: {ear:.3f}")
            
            stats = self.detector.get_sleep_stats()
            self.total_sleep_var.set(f"Total Sleep Time: {stats['total_sleep_duration']:.1f}s")
            
            if is_bad_habit:
                self.status_var.set("HAND TOUCHING FACE!")
                self.status_label.config(fg="#ff00ff")
            elif is_sleeping:
                self.status_var.set("SLEEP DETECTED!")
                self.status_label.config(fg="#ff0000")
            elif is_bad_posture:
                self.status_var.set("BAD POSTURE DETECTED!")
                self.status_label.config(fg="#ffa500")
            elif is_yawning:
                self.status_var.set("YAWNING DETECTED!")
                self.status_label.config(fg="#ffff00")
            elif is_head_nodding:
                self.status_var.set("HEAD NODDING DETECTED!")
                self.status_label.config(fg="#00ffff")
            else:
                self.status_var.set("Monitoring Active")
                self.status_label.config(fg="#00ff88")
                
        except Exception as e:
            print(f"Error updating GUI: {e}")
    
    def on_sleep_detected_callback(self):
        """Callback when sleep is detected"""
        self.sleep_episodes += 1
        self.sleep_count_var.set(f"Sleep Episodes: {self.sleep_episodes}")
        self.screenshot_count += 1
        self.screenshot_count_var.set(f"Screenshots: {self.screenshot_count}")
        
        # Log sleep event
        stats = self.detector.get_sleep_stats()
        duration = stats.get('total_sleep_duration', 0)
        self.data_logger.log_sleep_event(duration, 0.3)  # Approximate EAR value
    
    def on_habit_detected_callback(self):
        """Callback when bad habit is detected"""
        self.habit_episodes += 1
        self.habit_count_var.set(f"Bad Habit Episodes: {self.habit_episodes}")
        
        # Log habit event
        self.data_logger.log_habit_event(0.1)  # Approximate distance value
    
    def reset_stats(self):
        """Reset all statistics"""
        self.detector.reset_stats()
        self.sleep_episodes = 0
        self.screenshot_count = 0
        self.habit_episodes = 0
        self.sleep_count_var.set("Sleep Episodes: 0")
        self.total_sleep_var.set("Total Sleep Time: 0.0s")
        self.screenshot_count_var.set("Screenshots: 0")
        self.habit_count_var.set("Bad Habit Episodes: 0")
        self.ear_var.set("EAR: --")
    
    def manual_screenshot(self):
        """Take a manual screenshot"""
        filepath = self.detector.take_screenshot()
        if filepath:
            self.screenshot_count += 1
            self.screenshot_count_var.set(f"Screenshots: {self.screenshot_count}")
            messagebox.showinfo("Screenshot", f"Screenshot saved to:\n{filepath}")
    
    def update_alert_message(self):
        """Update the custom alert message"""
        new_message = self.alert_message_var.get()
        if new_message.strip():
            self.detector.set_custom_alert_message(new_message)
            messagebox.showinfo("Success", f"Alert message updated to:\n'{new_message}'")
        else:
            messagebox.showwarning("Warning", "Please enter a valid alert message")
    
    def on_closing(self):
        """Handle window closing"""
        if messagebox.askyesno("Quit", "Do you want to minimize to system tray instead of quitting?"):
            self.hide_window()
        else:
            self.quit_app()
    
    def show_statistics_dashboard(self):
        """Show statistics dashboard with charts"""
        dashboard_window = Toplevel(self.root)
        dashboard_window.title("Statistics Dashboard")
        dashboard_window.geometry("1000x700")
        dashboard_window.configure(bg="#1e1e1e")
        
        # Get data
        sleep_df = self.data_logger.get_sleep_data()
        habit_df = self.data_logger.get_habit_data()
        
        # Create figure with subplots
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8))
        fig.patch.set_facecolor('#1e1e1e')
        
        # Sleep episodes over time
        if not sleep_df.empty:
            sleep_df['timestamp'] = pd.to_datetime(sleep_df['timestamp'])
            sleep_df['hour'] = sleep_df['timestamp'].dt.hour
            hourly_sleep = sleep_df.groupby('hour').size()
            ax1.bar(hourly_sleep.index, hourly_sleep.values, color='#ff6b6b')
            ax1.set_title('Sleep Episodes by Hour', color='white')
            ax1.set_xlabel('Hour', color='white')
            ax1.set_ylabel('Count', color='white')
            ax1.tick_params(colors='white')
            ax1.set_facecolor('#2d2d2d')
        else:
            ax1.text(0.5, 0.5, 'No sleep data available', ha='center', va='center', color='white')
            ax1.set_title('Sleep Episodes by Hour', color='white')
            ax1.set_facecolor('#2d2d2d')
        
        # Habit episodes over time
        if not habit_df.empty:
            habit_df['timestamp'] = pd.to_datetime(habit_df['timestamp'])
            habit_df['hour'] = habit_df['timestamp'].dt.hour
            hourly_habit = habit_df.groupby('hour').size()
            ax2.bar(hourly_habit.index, hourly_habit.values, color='#4ecdc4')
            ax2.set_title('Habit Episodes by Hour', color='white')
            ax2.set_xlabel('Hour', color='white')
            ax2.set_ylabel('Count', color='white')
            ax2.tick_params(colors='white')
            ax2.set_facecolor('#2d2d2d')
        else:
            ax2.text(0.5, 0.5, 'No habit data available', ha='center', va='center', color='white')
            ax2.set_title('Habit Episodes by Hour', color='white')
            ax2.set_facecolor('#2d2d2d')
        
        # Sleep duration distribution
        if not sleep_df.empty:
            ax3.hist(sleep_df['duration'], bins=10, color='#ffe66d', edgecolor='white')
            ax3.set_title('Sleep Duration Distribution', color='white')
            ax3.set_xlabel('Duration (seconds)', color='white')
            ax3.set_ylabel('Frequency', color='white')
            ax3.tick_params(colors='white')
            ax3.set_facecolor('#2d2d2d')
        else:
            ax3.text(0.5, 0.5, 'No sleep data available', ha='center', va='center', color='white')
            ax3.set_title('Sleep Duration Distribution', color='white')
            ax3.set_facecolor('#2d2d2d')
        
        # Daily summary
        daily_stats = self.data_logger.get_daily_stats()
        categories = ['Sleep Episodes', 'Total Sleep (s)', 'Habit Episodes']
        values = [daily_stats['sleep_episodes'], daily_stats['total_sleep_duration'], daily_stats['habit_episodes']]
        ax4.bar(categories, values, color=['#ff6b6b', '#ffe66d', '#4ecdc4'])
        ax4.set_title('Today\'s Summary', color='white')
        ax4.set_ylabel('Count/Duration', color='white')
        ax4.tick_params(colors='white', rotation=45)
        ax4.set_facecolor('#2d2d2d')
        
        plt.tight_layout()
        
        # Embed in tkinter
        canvas = FigureCanvasTkAgg(fig, master=dashboard_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Close button
        close_btn = tk.Button(dashboard_window, text="Close", command=dashboard_window.destroy,
                             bg="#ff4444", fg="white", font=("Arial", 12))
        close_btn.pack(pady=10)
    
    def generate_report(self):
        """Generate and display daily/weekly report"""
        report_window = Toplevel(self.root)
        report_window.title("Activity Report")
        report_window.geometry("600x500")
        report_window.configure(bg="#1e1e1e")
        
        # Get statistics
        daily_stats = self.data_logger.get_daily_stats()
        weekly_stats = self.data_logger.get_weekly_stats()
        
        # Create text widget for report
        report_text = tk.Text(report_window, bg="#2d2d2d", fg="white", 
                             font=("Arial", 11), wrap=tk.WORD, padx=20, pady=20)
        report_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Generate report content
        report = f"""
{'='*50}
SLEEPGUARD PRO - ACTIVITY REPORT
{'='*50}

DAILY REPORT ({daily_stats['date']})
{'-'*50}
Sleep Episodes: {daily_stats['sleep_episodes']}
Total Sleep Duration: {daily_stats['total_sleep_duration']:.2f} seconds
Average Sleep Duration: {daily_stats['avg_sleep_duration']:.2f} seconds
Habit Episodes: {daily_stats['habit_episodes']}

WEEKLY REPORT
{'-'*50}
Sleep Episodes: {weekly_stats['sleep_episodes']}
Total Sleep Duration: {weekly_stats['total_sleep_duration']:.2f} seconds
Average Sleep Duration: {weekly_stats['avg_sleep_duration']:.2f} seconds
Habit Episodes: {weekly_stats['habit_episodes']}

RECOMMENDATIONS
{'-'*50}
"""
        
        if daily_stats['habit_episodes'] > 10:
            report += "• High face-touching frequency detected. Try to be more conscious of this habit.\n"
        if daily_stats['total_sleep_duration'] > 60:
            report += "• Consider taking more breaks to stay alert.\n"
        if daily_stats['sleep_episodes'] < 5:
            report += "• Good focus! Keep up the great work.\n"
        else:
            report += "• Frequent sleep episodes detected. Ensure you're getting enough rest.\n"
        
        report += f"\n{'='*50}\n"
        
        report_text.insert(tk.END, report)
        report_text.config(state=tk.DISABLED)
        
        # Close button
        close_btn = tk.Button(report_window, text="Close", command=report_window.destroy,
                             bg="#ff4444", fg="white", font=("Arial", 12))
        close_btn.pack(pady=10)
        
        # Export PDF button
        export_btn = tk.Button(report_window, text="Export to PDF", command=self.export_pdf_report,
                             bg="#00aaff", fg="white", font=("Arial", 12))
        export_btn.pack(pady=5)
        
        # Email Report button
        email_btn = tk.Button(report_window, text="Email Report", command=self.email_report,
                             bg="#00aa00", fg="white", font=("Arial", 12))
        email_btn.pack(pady=5)
    
    def export_pdf_report(self):
        """Export report to PDF"""
        try:
            # Ask for save location
            file_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                title="Save Report as PDF"
            )
            
            if not file_path:
                return
            
            # Get statistics
            daily_stats = self.data_logger.get_daily_stats()
            weekly_stats = self.data_logger.get_weekly_stats()
            
            # Create PDF
            doc = SimpleDocTemplate(file_path, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Title
            title = Paragraph("SleepGuard Pro - Activity Report", styles['Title'])
            story.append(title)
            story.append(Spacer(1, 12))
            
            # Daily Report
            daily_title = Paragraph(f"<b>Daily Report ({daily_stats['date']})</b>", styles['Heading2'])
            story.append(daily_title)
            story.append(Spacer(1, 12))
            
            daily_data = [
                ['Metric', 'Value'],
                ['Sleep Episodes', str(daily_stats['sleep_episodes'])],
                ['Total Sleep Duration', f"{daily_stats['total_sleep_duration']:.2f}s"],
                ['Average Sleep Duration', f"{daily_stats['avg_sleep_duration']:.2f}s"],
                ['Habit Episodes', str(daily_stats['habit_episodes'])]
            ]
            
            daily_table = Table(daily_data)
            daily_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(daily_table)
            story.append(Spacer(1, 12))
            
            # Weekly Report
            weekly_title = Paragraph("<b>Weekly Report</b>", styles['Heading2'])
            story.append(weekly_title)
            story.append(Spacer(1, 12))
            
            weekly_data = [
                ['Metric', 'Value'],
                ['Sleep Episodes', str(weekly_stats['sleep_episodes'])],
                ['Total Sleep Duration', f"{weekly_stats['total_sleep_duration']:.2f}s"],
                ['Average Sleep Duration', f"{weekly_stats['avg_sleep_duration']:.2f}s"],
                ['Habit Episodes', str(weekly_stats['habit_episodes'])]
            ]
            
            weekly_table = Table(weekly_data)
            weekly_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(weekly_table)
            story.append(Spacer(1, 12))
            
            # Build PDF
            doc.build(story)
            
            messagebox.showinfo("Success", f"PDF report saved to:\n{file_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export PDF: {e}")
    
    def email_report(self):
        """Send report via email"""
        try:
            # Create email configuration dialog
            email_dialog = Toplevel(self.root)
            email_dialog.title("Email Report")
            email_dialog.geometry("400x300")
            email_dialog.configure(bg="#1e1e1e")
            
            tk.Label(email_dialog, text="Your Email:", bg="#1e1e1e", fg="white").pack(pady=5)
            from_email_entry = tk.Entry(email_dialog, bg="#2d2d2d", fg="white", width=40)
            from_email_entry.pack(pady=5)
            
            tk.Label(email_dialog, text="Recipient Email:", bg="#1e1e1e", fg="white").pack(pady=5)
            to_email_entry = tk.Entry(email_dialog, bg="#2d2d2d", fg="white", width=40)
            to_email_entry.pack(pady=5)
            
            tk.Label(email_dialog, text="Gmail Password (App Password):", bg="#1e1e1e", fg="white").pack(pady=5)
            password_entry = tk.Entry(email_dialog, bg="#2d2d2d", fg="white", width=40, show="*")
            password_entry.pack(pady=5)
            
            def send_email():
                try:
                    from_email = from_email_entry.get()
                    to_email = to_email_entry.get()
                    password = password_entry.get()
                    
                    if not all([from_email, to_email, password]):
                        messagebox.showerror("Error", "Please fill all fields")
                        return
                    
                    # Get statistics
                    daily_stats = self.data_logger.get_daily_stats()
                    weekly_stats = self.data_logger.get_weekly_stats()
                    
                    # Create email content
                    subject = "SleepGuard Pro - Activity Report"
                    body = f"""
SleepGuard Pro - Activity Report

DAILY REPORT ({daily_stats['date']})
Sleep Episodes: {daily_stats['sleep_episodes']}
Total Sleep Duration: {daily_stats['total_sleep_duration']:.2f}s
Average Sleep Duration: {daily_stats['avg_sleep_duration']:.2f}s
Habit Episodes: {daily_stats['habit_episodes']}

WEEKLY REPORT
Sleep Episodes: {weekly_stats['sleep_episodes']}
Total Sleep Duration: {weekly_stats['total_sleep_duration']:.2f}s
Average Sleep Duration: {weekly_stats['avg_sleep_duration']:.2f}s
Habit Episodes: {weekly_stats['habit_episodes']}
"""
                    
                    # Create message
                    msg = MIMEMultipart()
                    msg['From'] = from_email
                    msg['To'] = to_email
                    msg['Subject'] = subject
                    msg.attach(MIMEText(body, 'plain'))
                    
                    # Send email
                    server = smtplib.SMTP('smtp.gmail.com', 587)
                    server.starttls()
                    server.login(from_email, password)
                    server.send_message(msg)
                    server.quit()
                    
                    messagebox.showinfo("Success", "Report sent successfully!")
                    email_dialog.destroy()
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to send email: {e}")
            
            send_btn = tk.Button(email_dialog, text="Send Email", command=send_email,
                               bg="#00aa00", fg="white", font=("Arial", 12))
            send_btn.pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open email dialog: {e}")
    
    def backup_restore_data(self):
        """Backup or restore data"""
        try:
            # Create backup/restore dialog
            dialog = Toplevel(self.root)
            dialog.title("Backup/Restore Data")
            dialog.geometry("400x200")
            dialog.configure(bg="#1e1e1e")
            
            def backup_data():
                try:
                    # Ask for backup location
                    backup_path = filedialog.asksaveasfilename(
                        defaultextension=".zip",
                        filetypes=[("ZIP files", "*.zip")],
                        title="Backup Data"
                    )
                    
                    if not backup_path:
                        return
                    
                    # Create backup
                    import shutil
                    data_dir = "data"
                    if os.path.exists(data_dir):
                        shutil.make_archive(backup_path.replace('.zip', ''), 'zip', data_dir)
                        messagebox.showinfo("Success", f"Data backed up to:\n{backup_path}")
                    else:
                        messagebox.showwarning("Warning", "No data to backup")
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Backup failed: {e}")
            
            def restore_data():
                try:
                    # Ask for backup file
                    backup_path = filedialog.askopenfilename(
                        filetypes=[("ZIP files", "*.zip")],
                        title="Select Backup File"
                    )
                    
                    if not backup_path:
                        return
                    
                    # Confirm restore
                    if not messagebox.askyesno("Confirm", "This will replace existing data. Continue?"):
                        return
                    
                    # Restore data
                    import shutil
                    import zipfile
                    
                    # Remove existing data directory
                    data_dir = "data"
                    if os.path.exists(data_dir):
                        shutil.rmtree(data_dir)
                    
                    # Extract backup
                    with zipfile.ZipFile(backup_path, 'r') as zip_ref:
                        zip_ref.extractall('.')
                    
                    messagebox.showinfo("Success", "Data restored successfully!")
                    dialog.destroy()
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Restore failed: {e}")
            
            backup_btn = tk.Button(dialog, text="Backup Data", command=backup_data,
                                  bg="#00aaff", fg="white", font=("Arial", 12))
            backup_btn.pack(pady=10)
            
            restore_btn = tk.Button(dialog, text="Restore Data", command=restore_data,
                                   bg="#ff6600", fg="white", font=("Arial", 12))
            restore_btn.pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open dialog: {e}")

def main():
    root = tk.Tk()
    app = SleepGuardApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
