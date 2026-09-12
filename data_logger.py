import json
import os
from datetime import datetime
import pandas as pd

class DataLogger:
    def __init__(self, log_dir="data"):
        self.log_dir = log_dir
        self.ensure_log_directory()
        self.sleep_log_file = os.path.join(self.log_dir, "sleep_log.json")
        self.habit_log_file = os.path.join(self.log_dir, "habit_log.json")
        
        # Initialize log files if they don't exist
        self.init_log_file(self.sleep_log_file)
        self.init_log_file(self.habit_log_file)
    
    def ensure_log_directory(self):
        """Create log directory if it doesn't exist"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
    
    def init_log_file(self, filepath):
        """Initialize log file with empty list if it doesn't exist"""
        if not os.path.exists(filepath):
            with open(filepath, 'w') as f:
                json.dump([], f)
    
    def log_sleep_event(self, duration, ear_value):
        """Log a sleep detection event"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": "sleep",
            "duration": duration,
            "ear_value": ear_value
        }
        self.append_to_log(self.sleep_log_file, event)
    
    def log_habit_event(self, distance):
        """Log a bad habit detection event"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": "habit",
            "distance": distance
        }
        self.append_to_log(self.habit_log_file, event)
    
    def append_to_log(self, filepath, event):
        """Append event to log file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            data.append(event)
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error logging event: {e}")
    
    def get_sleep_data(self):
        """Get sleep log data as DataFrame"""
        return self.get_log_data(self.sleep_log_file)
    
    def get_habit_data(self):
        """Get habit log data as DataFrame"""
        return self.get_log_data(self.habit_log_file)
    
    def get_log_data(self, filepath):
        """Get log data as DataFrame"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            return pd.DataFrame(data)
        except:
            return pd.DataFrame()
    
    def get_daily_stats(self, date=None):
        """Get statistics for a specific day"""
        if date is None:
            date = datetime.now().date()
        
        sleep_df = self.get_sleep_data()
        habit_df = self.get_habit_data()
        
        if not sleep_df.empty:
            sleep_df['timestamp'] = pd.to_datetime(sleep_df['timestamp'])
            sleep_df = sleep_df[sleep_df['timestamp'].dt.date == date]
        
        if not habit_df.empty:
            habit_df['timestamp'] = pd.to_datetime(habit_df['timestamp'])
            habit_df = habit_df[habit_df['timestamp'].dt.date == date]
        
        return {
            "date": date,
            "sleep_episodes": len(sleep_df),
            "total_sleep_duration": sleep_df['duration'].sum() if not sleep_df.empty else 0,
            "habit_episodes": len(habit_df),
            "avg_sleep_duration": sleep_df['duration'].mean() if not sleep_df.empty else 0
        }
    
    def get_weekly_stats(self):
        """Get statistics for the current week"""
        sleep_df = self.get_sleep_data()
        habit_df = self.get_habit_data()
        
        if not sleep_df.empty:
            sleep_df['timestamp'] = pd.to_datetime(sleep_df['timestamp'])
            week_start = datetime.now().date() - pd.Timedelta(days=datetime.now().weekday())
            sleep_df = sleep_df[sleep_df['timestamp'].dt.date >= week_start]
        
        if not habit_df.empty:
            habit_df['timestamp'] = pd.to_datetime(habit_df['timestamp'])
            week_start = datetime.now().date() - pd.Timedelta(days=datetime.now().weekday())
            habit_df = habit_df[habit_df['timestamp'].dt.date >= week_start]
        
        return {
            "sleep_episodes": len(sleep_df),
            "total_sleep_duration": sleep_df['duration'].sum() if not sleep_df.empty else 0,
            "habit_episodes": len(habit_df),
            "avg_sleep_duration": sleep_df['duration'].mean() if not sleep_df.empty else 0
        }
    
    def clear_logs(self):
        """Clear all log files"""
        self.init_log_file(self.sleep_log_file)
        self.init_log_file(self.habit_log_file)
