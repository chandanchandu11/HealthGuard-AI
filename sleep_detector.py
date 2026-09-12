import cv2
import mediapipe as mp
import numpy as np
import math
import time
import threading
import os
from datetime import datetime
import pyautogui
import pyttsx3
import winsound
import queue
from collections import deque

class SleepDetector:
    def __init__(self):
        # Initialize MediaPipe Face Mesh
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Initialize MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        
        # Initialize MediaPipe Pose for posture detection
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Eye aspect ratio threshold
        self.EYE_AR_THRESH = 0.35  # Adjusted for MediaPipe landmarks
        self.EYE_AR_CONSEC_FRAMES = 10  # Reduced to trigger faster (was 20)
        
        # Frame dimensions
        self.frame_width = 0
        self.frame_height = 0
        
        # Counter for consecutive frames with closed eyes
        self.c_counter = 0
        self.total_sleep_frames = 0
        self.sleep_detected = False
        self.sleep_start_time = None
        self.total_sleep_duration = 0
        
        # Bad habit detection
        self.habit_alert_shown = False
        self.hand_near_face = False
        self.hand_touch_face_counter = 0
        self.HAND_TOUCH_CONSEC_FRAMES = 15  # Frames to trigger bad habit alert
        self.hand_touch_threshold = 0.15  # Distance threshold for hand near face
        
        # Posture detection
        self.posture_counter = 0
        self.POSTURE_CONSEC_FRAMES = 20  # Frames to trigger posture alert
        self.posture_threshold = 0.7  # Shoulder alignment threshold
        self.bad_posture_detected = False
        
        # Yawn detection
        self.yawn_counter = 0
        self.YAWN_CONSEC_FRAMES = 10  # Frames to trigger yawn alert
        self.yawn_threshold = 0.5  # Mouth aspect ratio threshold for yawning
        self.yawn_detected = False
        
        # Head nodding detection
        self.head_nod_counter = 0
        self.HEAD_NOD_CONSEC_FRAMES = 15  # Frames to trigger head nod alert
        self.head_nod_threshold = 0.3  # Head tilt threshold
        self.head_nod_detected = False
        self.head_positions = deque(maxlen=30)  # Track last 30 head positions
        
        # Eye blink rate tracking
        self.blink_count = 0
        self.blink_start_time = time.time()
        self.blinks_per_minute = 0
        self.blink_history = deque(maxlen=60)  # Track blinks over last minute
        
        # Alert system
        self.engine = None
        self.speech_queue = queue.Queue()
        self.speech_thread = None
        self.speech_running = False
        
        # Screenshot directory - use local directory by default
        self.screenshot_dir = os.path.join(os.getcwd(), "screenshots")
        self.ensure_screenshot_directory()
        
        # Callbacks
        self.on_sleep_detected = None
        self.on_habit_detected = None
        
        # Custom alert message
        self.custom_alert_message = None
        
        # Start speech thread
        self.start_speech_thread()
    
    def start_speech_thread(self):
        """Start the speech processing thread"""
        self.speech_running = True
        self.speech_thread = threading.Thread(target=self.speech_worker, daemon=True)
        self.speech_thread.start()
    
    def speech_worker(self):
        """Worker thread to process speech queue"""
        while self.speech_running:
            try:
                message = self.speech_queue.get(timeout=1)
                if message:
                    try:
                        if self.engine is None:
                            self.engine = pyttsx3.init()
                            self.engine.setProperty('rate', 150)
                        self.engine.say(message)
                        self.engine.runAndWait()
                    except Exception as e:
                        print(f"Error speaking: {e}")
                        try:
                            self.engine = None
                        except:
                            pass
                self.speech_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Speech worker error: {e}")
    
    def ensure_screenshot_directory(self):
        """Create screenshot directory if it doesn't exist"""
        try:
            if not os.path.exists(self.screenshot_dir):
                os.makedirs(self.screenshot_dir)
                print(f"Created directory: {self.screenshot_dir}")
        except Exception as e:
            print(f"Error creating directory: {e}")
            # Fallback to current directory
            self.screenshot_dir = os.path.join(os.getcwd(), "screenshots")
            try:
                if not os.path.exists(self.screenshot_dir):
                    os.makedirs(self.screenshot_dir)
                    print(f"Created fallback directory: {self.screenshot_dir}")
            except Exception as e2:
                print(f"Error creating fallback directory: {e2}")
                self.screenshot_dir = os.getcwd()
    
    def eye_aspect_ratio(self, face_landmarks, eye_indices, frame_width, frame_height):
        """Calculate the eye aspect ratio (EAR) using MediaPipe landmarks"""
        # Get eye landmarks
        eye_points = []
        for idx in eye_indices:
            landmark = face_landmarks.landmark[idx]
            eye_points.append([landmark.x * frame_width, landmark.y * frame_height])
        
        eye_points = np.array(eye_points, dtype=np.int32)
        
        # Vertical eye landmarks
        A = np.linalg.norm(eye_points[1] - eye_points[5])
        B = np.linalg.norm(eye_points[2] - eye_points[4])
        # Horizontal eye landmark
        C = np.linalg.norm(eye_points[0] - eye_points[3])
        
        # Eye aspect ratio
        ear = (A + B) / (2.0 * C)
        return ear
    
    def get_facial_landmarks(self, frame):
        """Detect facial landmarks using MediaPipe"""
        frame_height, frame_width = frame.shape[:2]
        self.frame_width = frame_width
        self.frame_height = frame_height
        
        # Convert to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process face mesh
        face_results = self.face_mesh.process(rgb_frame)
        
        # Process hands
        hand_results = self.hands.process(rgb_frame)
        
        # Process pose
        pose_results = self.pose.process(rgb_frame)
        
        landmarks = None
        if face_results.multi_face_landmarks:
            landmarks = face_results.multi_face_landmarks[0]
        
        return landmarks, face_results, hand_results, pose_results
    
    def detect_sleep(self, landmarks):
        """Detect if eyes are closed (sleep detection)"""
        if not landmarks:
            return False, 0
        
        # MediaPipe Face Mesh eye landmarks
        # Left eye: 33, 160, 158, 133, 153, 144
        # Right eye: 362, 385, 387, 373, 380, 373
        left_eye_indices = [33, 160, 158, 133, 153, 144]
        right_eye_indices = [362, 385, 387, 373, 380, 373]
        
        try:
            # landmarks is the face_landmarks object (NormalizedLandmarkList)
            face_landmarks = landmarks
            left_ear = self.eye_aspect_ratio(face_landmarks, left_eye_indices, self.frame_width, self.frame_height)
            right_ear = self.eye_aspect_ratio(face_landmarks, right_eye_indices, self.frame_width, self.frame_height)
            
            # Average eye aspect ratio
            ear = (left_ear + right_ear) / 2.0
            
            # Debug output (every 30 frames to avoid spam)
            self.total_sleep_frames += 1
            if self.total_sleep_frames % 30 == 0:
                print(f"EAR: {ear:.3f} (Threshold: {self.EYE_AR_THRESH}), Counter: {self.c_counter}/{self.EYE_AR_CONSEC_FRAMES}")
        except Exception as e:
            print(f"Error calculating EAR: {e}")
            import traceback
            traceback.print_exc()
            return False, 0
        
        # Check if eyes are closed
        if ear < self.EYE_AR_THRESH:
            self.c_counter += 1
            
            if self.c_counter >= self.EYE_AR_CONSEC_FRAMES:
                if not self.sleep_detected:
                    self.sleep_detected = True
                    self.sleep_start_time = time.time()
                    print(f"SLEEP DETECTED! EAR: {ear:.3f}")
                return True, ear
        else:
            self.c_counter = 0
            if self.sleep_detected:
                self.sleep_detected = False
                if self.sleep_start_time:
                    duration = time.time() - self.sleep_start_time
                    self.total_sleep_duration += duration
                    self.sleep_start_time = None
                print(f"WAKE UP! Duration: {duration:.1f}s")
        
        return False, ear
    
    def detect_bad_habits(self, face_landmarks, hand_results):
        """Detect bad habits like pimple touching, face touching, hair touching, nose touching"""
        if not face_landmarks or not hand_results.multi_hand_landmarks:
            return False, None
        
        # Get face center (nose tip - landmark 1 in face mesh)
        nose_tip = face_landmarks.landmark[1]
        face_center = np.array([nose_tip.x, nose_tip.y])
        
        # Check each hand
        for hand_landmarks in hand_results.multi_hand_landmarks:
            # Check fingertips (index finger tip - landmark 8, middle finger tip - landmark 12)
            # Also check thumb tip (landmark 4) and other fingertips
            fingertips = [4, 8, 12, 16, 20]  # Thumb, index, middle, ring, pinky tips
            
            for fingertip_idx in fingertips:
                fingertip = hand_landmarks.landmark[fingertip_idx]
                fingertip_pos = np.array([fingertip.x, fingertip.y])
                
                # Calculate distance between fingertip and face center
                distance = np.linalg.norm(fingertip_pos - face_center)
                
                # If hand is very close to face (within threshold)
                if distance < self.hand_touch_threshold:
                    self.hand_touch_face_counter += 1
                    
                    if self.hand_touch_face_counter >= self.HAND_TOUCH_CONSEC_FRAMES:
                        if not self.hand_near_face:
                            self.hand_near_face = True
                            return True, distance
                    return True, distance
                else:
                    self.hand_touch_face_counter = 0
                    self.hand_near_face = False
        
        return False, None
    
    def detect_posture(self, pose_results):
        """Detect poor posture (slouching) using pose landmarks"""
        if not pose_results.pose_landmarks:
            return False, None
        
        # Get shoulder landmarks (left: 11, right: 12)
        landmarks = pose_results.pose_landmarks.landmark
        left_shoulder = landmarks[11]
        right_shoulder = landmarks[12]
        
        # Calculate shoulder alignment (should be horizontal when sitting straight)
        shoulder_diff = abs(left_shoulder.y - right_shoulder.y)
        
        # Check if shoulders are misaligned (slouching)
        if shoulder_diff > self.posture_threshold:
            self.posture_counter += 1
            if self.posture_counter >= self.POSTURE_CONSEC_FRAMES:
                if not self.bad_posture_detected:
                    self.bad_posture_detected = True
                    return True, shoulder_diff
        else:
            self.posture_counter = 0
            self.bad_posture_detected = False
        
        return False, shoulder_diff
    
    def detect_yawn(self, face_landmarks):
        """Detect yawning using mouth aspect ratio"""
        if not face_landmarks:
            return False, None
        
        # Mouth landmarks (upper lip: 13, lower lip: 14, left corner: 61, right corner: 291)
        upper_lip = face_landmarks.landmark[13]
        lower_lip = face_landmarks.landmark[14]
        left_corner = face_landmarks.landmark[61]
        right_corner = face_landmarks.landmark[291]
        
        # Calculate mouth aspect ratio
        mouth_height = np.linalg.norm(np.array([upper_lip.x, upper_lip.y]) - np.array([lower_lip.x, lower_lip.y]))
        mouth_width = np.linalg.norm(np.array([left_corner.x, left_corner.y]) - np.array([right_corner.x, right_corner.y]))
        
        if mouth_width > 0:
            mouth_ar = mouth_height / mouth_width
        else:
            mouth_ar = 0
        
        # Check if mouth is open wide (yawning)
        if mouth_ar > self.yawn_threshold:
            self.yawn_counter += 1
            if self.yawn_counter >= self.YAWN_CONSEC_FRAMES:
                if not self.yawn_detected:
                    self.yawn_detected = True
                    return True, mouth_ar
        else:
            self.yawn_counter = 0
            self.yawn_detected = False
        
        return False, mouth_ar
    
    def detect_head_nodding(self, face_landmarks):
        """Detect head nodding (drowsiness)"""
        if not face_landmarks:
            return False, None
        
        # Get nose tip position
        nose_tip = face_landmarks.landmark[1]
        current_y = nose_tip.y
        
        # Track head position history
        self.head_positions.append(current_y)
        
        if len(self.head_positions) < 30:
            return False, None
        
        # Calculate vertical movement
        y_positions = list(self.head_positions)
        y_range = max(y_positions) - min(y_positions)
        
        # Check for repetitive nodding motion
        if y_range > self.head_nod_threshold:
            self.head_nod_counter += 1
            if self.head_nod_counter >= self.HEAD_NOD_CONSEC_FRAMES:
                if not self.head_nod_detected:
                    self.head_nod_detected = True
                    return True, y_range
        else:
            self.head_nod_counter = 0
            self.head_nod_detected = False
        
        return False, y_range
    
    def track_blinks(self, ear):
        """Track blink rate over time"""
        current_time = time.time()
        
        # Detect blink (rapid eye closure and opening)
        if ear < self.EYE_AR_THRESH:
            # Eye closed - potential blink
            if not hasattr(self, 'eye_closed'):
                self.eye_closed = True
                self.eye_closed_time = current_time
        else:
            # Eye opened
            if hasattr(self, 'eye_closed') and self.eye_closed:
                # Check if it was a quick blink (less than 0.3 seconds)
                if current_time - self.eye_closed_time < 0.3:
                    self.blink_count += 1
                    self.blink_history.append(current_time)
                self.eye_closed = False
        
        # Calculate blinks per minute
        time_elapsed = current_time - self.blink_start_time
        if time_elapsed >= 60:  # Every minute
            self.blinks_per_minute = self.blink_count
            self.blink_count = 0
            self.blink_start_time = current_time
        
        return self.blinks_per_minute
    
    def take_screenshot(self):
        """Take a screenshot and save it"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sleep_{timestamp}.png"
        filepath = os.path.join(self.screenshot_dir, filename)
        
        try:
            screenshot = pyautogui.screenshot()
            screenshot.save(filepath)
            print(f"Screenshot saved: {filepath}")
            return filepath
        except Exception as e:
            print(f"Error taking screenshot: {e}")
            return None
    
    def play_alert_sound(self):
        """Play alert sound"""
        try:
            winsound.Beep(1000, 1000)  # 1000Hz for 1 second
        except:
            pass
    
    def speak_alert(self, message):
        """Speak alert message using queue"""
        try:
            self.speech_queue.put(message)
        except Exception as e:
            print(f"Error queuing speech: {e}")
    
    def set_custom_alert_message(self, message):
        """Set a custom alert message"""
        self.custom_alert_message = message
    
    def trigger_sleep_alert(self):
        """Trigger sleep alert with voice message only (no sound effect)"""
        # Speak alert - use custom message if set, otherwise use random default
        if self.custom_alert_message:
            message = self.custom_alert_message
        else:
            alert_messages = [
                "Wake up boss!",
                "Hey boss, wake up!",
                "Time to wake up!",
                "Boss, are you sleeping?",
                "Wake up, it's important!"
            ]
            import random
            message = random.choice(alert_messages)
        
        threading.Thread(target=self.speak_alert, args=(message,), daemon=True).start()
        
        # Take screenshot
        self.take_screenshot()
        
        # Call callback if set
        if self.on_sleep_detected:
            self.on_sleep_detected()
    
    def trigger_bad_habit_alert(self):
        """Trigger bad habit alert when hand touches face"""
        # Play sound alert for bad habit
        threading.Thread(target=self.play_alert_sound, daemon=True).start()
        
        # Speak bad habit alert
        bad_habit_messages = [
            "Hands up your face!",
            "Don't touch your face!",
            "Stop touching your face!",
            "Hands away from face!",
            "Bad habit detected!"
        ]
        import random
        message = random.choice(bad_habit_messages)
        threading.Thread(target=self.speak_alert, args=(message,), daemon=True).start()
        
        # Call callback if set
        if self.on_habit_detected:
            self.on_habit_detected()
    
    def get_sleep_stats(self):
        """Get sleep statistics"""
        return {
            "total_sleep_frames": self.total_sleep_frames,
            "total_sleep_duration": self.total_sleep_duration,
            "currently_sleeping": self.sleep_detected,
            "sleep_start_time": self.sleep_start_time
        }
    
    def reset_stats(self):
        """Reset sleep statistics"""
        self.total_sleep_frames = 0
        self.total_sleep_duration = 0
        self.sleep_detected = False
        self.sleep_start_time = None
        self.c_counter = 0
