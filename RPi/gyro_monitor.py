#!/usr/bin/env python3
"""
Utility to monitor gyroscope data from the robot over time.
This demonstrates more robust communication and shows the cumulative angles.
"""

import json
import time
import sys
import robot  # Import the robot module

class GyroMonitor:
    def __init__(self):
        self.running = True
        # Last received gyro values
        self.last_gyro = {
            'gyro_x': 0, 'gyro_y': 0, 'gyro_z': 0,
            'angle_x': 0, 'angle_y': 0, 'angle_z': 0
        }
        # Counter for successful/failed reads
        self.success_count = 0
        self.fail_count = 0
    
    def reset_gyro(self):
        """Reset the gyroscope angles on the robot"""
        success = robot.resetGyroAngles()
        if success:
            print("Gyroscope angles reset successfully")
        else:
            print("Failed to reset gyroscope angles")
    
    def run(self):
        """Main monitoring loop"""
        print("Starting gyroscope monitoring. Press Ctrl+C to exit.")
        print("Resetting gyroscope angles...")
        self.reset_gyro()
        
        start_time = time.time()
        
        try:
            while self.running:
                gyro_data = robot.getGyroData()
                
                if gyro_data:
                    self.last_gyro = gyro_data
                    self.success_count += 1
                    
                    # Clear screen and print current values
                    print("\033c", end="")  # Clear the screen
                    print(f"Running for: {time.time() - start_time:.1f} seconds")
                    print(f"Success rate: {self.success_count}/{self.success_count + self.fail_count} " +
                          f"({self.success_count/(self.success_count + self.fail_count)*100:.1f}%)")
                    print("\nInstantaneous Rates (degrees/sec):")
                    print(f"X-axis: {gyro_data['gyro_x']:+8.4f}°/s")
                    print(f"Y-axis: {gyro_data['gyro_y']:+8.4f}°/s")
                    print(f"Z-axis: {gyro_data['gyro_z']:+8.4f}°/s")
                    
                    print("\nCumulative Angles (degrees):")
                    print(f"X-axis: {gyro_data['angle_x']:+8.4f}°")
                    print(f"Y-axis: {gyro_data['angle_y']:+8.4f}°")
                    print(f"Z-axis: {gyro_data['angle_z']:+8.4f}°")
                    
                    print("\nPress 'r' to reset angles, Ctrl+C to exit")
                else:
                    self.fail_count += 1
                
                # Check for keyboard input
                if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                    key = sys.stdin.read(1)
                    if key == 'r':
                        print("Resetting angles...")
                        self.reset_gyro()
                
                time.sleep(0.1)  # Short delay between updates
                    
        except KeyboardInterrupt:
            print("\nExiting gyroscope monitor.")
            return

if __name__ == "__main__":
    import select
    import termios
    import tty
    
    # Set terminal to raw mode for character-by-character input
    old_settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setraw(sys.stdin.fileno())
        monitor = GyroMonitor()
        monitor.run()
    finally:
        # Restore terminal settings
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
