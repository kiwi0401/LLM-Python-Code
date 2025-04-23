#!/usr/bin/env python3
"""
Standalone script to test the camera functionality
Usage: python3 standalone_camera_test.py [num_screenshots] [delay_seconds]
"""

import os
import sys
import time
import datetime
import cv2
import numpy as np

def capture_screenshots(num_screenshots=1, delay=1, save_dir=None):
    """
    Capture screenshots from the camera
    
    Parameters:
    - num_screenshots: Number of screenshots to take
    - delay: Time in seconds between screenshots
    - save_dir: Directory to save screenshots (defaults to 'screenshots')
    
    Returns:
    - List of saved screenshot paths
    """
    # Set up default save directory
    if save_dir is None:
        save_dir = 'screenshots'
    
    # Create directory if it doesn't exist
    os.makedirs(save_dir, exist_ok=True)
    
    # Initialize camera (use 0 for default camera)
    print("Opening camera...")
    cap = cv2.VideoCapture(0)
    
    # Check if camera opened successfully
    if not cap.isOpened():
        print("Error: Could not open camera")
        return []
    
    saved_paths = []
    
    try:
        for i in range(num_screenshots):
            # Capture frame
            print(f"Capturing image {i+1}/{num_screenshots}...")
            ret, frame = cap.read()
            
            if not ret:
                print(f"Error: Could not capture frame {i+1}")
                continue
                
            # Generate filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}_{i+1}.jpg"
            filepath = os.path.join(save_dir, filename)
            
            # Save image
            cv2.imwrite(filepath, frame)
            print(f"Saved: {filepath}")
            saved_paths.append(filepath)
            
            # Wait before next capture
            if i < num_screenshots - 1:
                time.sleep(delay)
    
    finally:
        # Release camera
        cap.release()
        print("Camera released")
    
    return saved_paths

if __name__ == "__main__":
    # Parse command line arguments
    num_screenshots = 1
    delay = 1
    
    if len(sys.argv) > 1:
        try:
            num_screenshots = int(sys.argv[1])
        except ValueError:
            print(f"Invalid number of screenshots: {sys.argv[1]}. Using default: 1")
    
    if len(sys.argv) > 2:
        try:
            delay = float(sys.argv[2])
        except ValueError:
            print(f"Invalid delay: {sys.argv[2]}. Using default: 1s")
    
    # Capture screenshots directly
    saved_files = capture_screenshots(num_screenshots, delay)
    
    if saved_files:
        print(f"Successfully captured {len(saved_files)} images")
    else:
        print("No images were captured")
