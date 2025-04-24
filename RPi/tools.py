#!/usr/bin/env/python3
# File name   : tools.py
# Description : Camera and LLM vision tools for the robot
import os
import sys
import time
import json
import base64
import datetime
import logging
import atexit
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("tools.log")
    ]
)
logger = logging.getLogger("tools")

# Load environment variables
load_dotenv()

# Import robot control functions first - these are essential
try:
    import robot  # Import the entire module to avoid circular import issues
    logger.info("Successfully imported robot module")
    robot_module_available = True
except ImportError as e:
    logger.error(f"Failed to import robot module: {e}")
    robot_module_available = False

# Initialize OpenAI client
try:
    from openai import OpenAI
    # Initialize with API key from environment variables
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    openai_available = True
except ImportError:
    logger.warning("OpenAI library not installed. Vision features will be disabled.")
    openai_available = False
except Exception as e:
    logger.error(f"Error initializing OpenAI client: {e}")
    openai_available = False

# Add numpy and OpenCV imports
try:
    import numpy as np
    import cv2
except ImportError:
    logger.warning("NumPy or OpenCV is not installed. Camera functionality will be limited.")

# Initialize camera globally for faster access
print("Initializing camera...")
camera = None
try:
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        print("Warning: Could not open camera on startup")
    else:
        print("Camera initialized successfully")
except Exception as e:
    print(f"Error initializing camera: {e}")

# Function to clean up resources when the script exits
def cleanup():
    if camera is not None and camera.isOpened():
        camera.release()
        print("Camera released during cleanup")

# Register the cleanup function to be called when the program exits
atexit.register(cleanup)

# Load tool descriptions
def load_tool_descriptions():
    """Load tool descriptions from JSON file"""
    try:
        tool_path = os.path.join(os.path.dirname(__file__), "tool_descriptions.json")
        with open(tool_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        logger.error(f"Error loading tool descriptions: {e}")
        return []

def read_dog_eyes_prompt():
    """
    Read the prompt content from dog_eyes.md file
    
    Returns:
    - str: The content of the file or a default prompt if file cannot be read
    """
    prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dog_eyes.md")
    
    try:
        if not os.path.exists(prompt_path):
            logger.warning(f"dog_eyes.md not found at {prompt_path}")
            return "Please describe what you see in this image in detail, focusing on objects and their positions."
            
        with open(prompt_path, "r") as f:
            content = f.read()
            logger.info(f"Successfully read prompt from {prompt_path}")
            return content
    except Exception as e:
        logger.error(f"Error reading dog_eyes.md: {e}")
        return "Please describe what you see in this image in detail, focusing on objects and their positions."

def encode_image(image_path):
    """
    Encode an image as base64
    
    Parameters:
    - image_path: Path to the image file
    
    Returns:
    - str: Base64 encoded image
    """
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    except Exception as e:
        logger.error(f"Error encoding image {image_path}: {e}")
        return None

def takeScreenshot(num_screenshots=1, delay=1, save_dir=None):
    """
    Capture screenshots using the pre-initialized camera
    
    Parameters:
    - num_screenshots: Number of screenshots to take
    - delay: Time in seconds between screenshots
    - save_dir: Directory to save screenshots (defaults to 'screenshots')
    
    Returns:
    - List of saved screenshot paths
    """
    global camera
    
    # Set up default save directory
    if save_dir is None:
        save_dir = 'screenshots'
    
    # Create directory if it doesn't exist
    os.makedirs(save_dir, exist_ok=True)
    
    # Check if camera is initialized and open
    if camera is None or not camera.isOpened():
        print("Camera not available, attempting to initialize...")
        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            print("Error: Could not open camera")
            return []
    
    saved_paths = []
    
    try:
        for i in range(num_screenshots):
            # Capture frame
            print(f"Capturing image {i+1}/{num_screenshots}...")
            ret, frame = camera.read()
            
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
    
    except Exception as e:
        print(f"Error capturing screenshot: {e}")
    
    return saved_paths

def sendImageToLLM(image_path, custom_prompt=None, model="gpt-4o"):
    """
    Send an image to OpenAI's GPT-4 Vision model for analysis
    
    Parameters:
    - image_path: Path to the image file
    - custom_prompt: Optional custom prompt to use instead of dog_eyes.md
    - model: OpenAI model to use (defaults to GPT-4 Vision)
    
    Returns:
    - str: The model's response or error message
    """
    if not openai_available:
        return "Error: OpenAI library not available. Cannot process image."
    
    # Check if image exists
    if not os.path.exists(image_path):
        logger.error(f"Image file not found: {image_path}")
        return f"Error: Image file not found: {image_path}"
    
    try:
        # Encode the image
        base64_image = encode_image(image_path)
        if not base64_image:
            return "Error: Could not encode image"
        
        # Get prompt from dog_eyes.md or use custom prompt
        prompt = custom_prompt if custom_prompt else read_dog_eyes_prompt()
        
        logger.info(f"Sending image {image_path} to OpenAI API")
        
        # Send request to OpenAI
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                            },
                        },
                    ],
                }
            ],
        )
        
        # Extract and return the response
        response = completion.choices[0].message.content
        logger.info("Successfully received response from OpenAI API")
        return response
        
    except Exception as e:
        logger.error(f"Error in sendImageToLLM: {e}", exc_info=True)
        return f"Error processing image with OpenAI: {str(e)}"

def view_surroundings():
    """
    Tool function that captures a photo and sends it to LLM for analysis
    
    Returns:
    - A description of what the robot sees from the LLM
    """
    # Take screenshot
    screenshots = takeScreenshot(1)
    
    # Check if screenshots were taken successfully
    if not screenshots:
        return "Error: Failed to capture any images of surroundings."
    
    # Send the most recent screenshot to LLM
    image_path = screenshots[-1]
    logger.info(f"Sending image {image_path} to LLM for analysis")
    
    # Get and return description
    description = sendImageToLLM(image_path)
    return description

def test_camera(num_screenshots=1, delay=1, save_dir=None):
    """
    Test camera functionality by taking screenshots
    """
    return takeScreenshot(num_screenshots, delay, save_dir)

def move_distance(distance_cm, speed=70, timeout=30):
    """
    Move the robot forward or backward a specific distance
    
    Parameters:
    - distance_cm: Distance to move in centimeters (positive for forward, negative for backward)
    - speed: Speed of movement (default 70)
    - timeout: Maximum time to try moving in seconds (default 30)
    
    Returns:
    - str: Status message
    """
    if not robot_module_available:
        error_msg = "Robot module not available. Cannot execute movement commands."
        logger.error(error_msg)
        return error_msg
    
    logger.info(f"Moving {distance_cm} cm at speed {speed}")
    
    try:
        # Constants for movement speed (cm/sec)
        FORWARD_SPEED_CM_PER_SEC = 15
        BACKWARD_SPEED_CM_PER_SEC = 20
        
        # Calculate expected movement time based on distance and speed
        if distance_cm >= 0:
            # Forward movement
            logger.info(f"Starting forward movement: {distance_cm} cm")
            expected_time = distance_cm / FORWARD_SPEED_CM_PER_SEC
            
            # Try to move forward with up to 3 retries
            success = False
            for attempt in range(1, 4):
                if robot.forward(speed):
                    success = True
                    logger.debug(f"Forward command sent successfully on attempt {attempt}")
                    break
                logger.warning(f"Forward command failed, retrying ({attempt}/3)")
                time.sleep(0.2)  # Short delay before retry
                
            if not success:
                return "Failed to send forward movement command after 3 attempts"
                
        else:
            # Backward movement
            logger.info(f"Starting backward movement: {abs(distance_cm)} cm")
            expected_time = abs(distance_cm) / BACKWARD_SPEED_CM_PER_SEC
            
            # Try to move backward with up to 3 retries
            success = False
            for attempt in range(1, 4):
                if robot.backward(speed):
                    success = True
                    logger.debug(f"Backward command sent successfully on attempt {attempt}")
                    break
                logger.warning(f"Backward command failed, retrying ({attempt}/3)")
                time.sleep(0.2)  # Short delay before retry
                
            if not success:
                return "Failed to send backward movement command after 3 attempts"
        
        # Cap the movement time by the timeout
        movement_time = min(expected_time, timeout)
        logger.info(f"Moving for {movement_time:.2f} seconds")
        
        # Wait for the calculated time
        time.sleep(movement_time)
        
        # Stop movement with retries
        stop_success = False
        for attempt in range(1, 4):
            if distance_cm >= 0:
                if robot.stopFB():
                    stop_success = True
                    logger.info("Forward movement stopped")
                    break
            else:
                if robot.stopFB():
                    stop_success = True
                    logger.info("Backward movement stopped")
                    break
                
            logger.warning(f"Stop command failed, retrying ({attempt}/3)")
            time.sleep(0.1)  # Short delay before retry
        
        if not stop_success:
            return f"Warning: Movement completed but failed to send stop command. Moved approximately {distance_cm} cm."
        
        success_msg = f"Successfully moved {distance_cm} cm"
        logger.info(success_msg)
        return success_msg
        
    except Exception as e:
        # Ensure robot stops if there's an error
        try:
            robot.stopFB()
            logger.info("Emergency stop after error")
        except:
            pass
        
        error_msg = f"Error during movement: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg

def rotate_to_angle(target_angle, speed=100, tolerance=2.0, timeout=20):
    """
    Rotate the robot to reach a specified angle using gyroscope feedback
    
    Parameters:
    - target_angle: Target angle in degrees (positive = clockwise, negative = counter-clockwise)
    - speed: Speed of rotation (default 60)
    - tolerance: How close to target angle is considered success (default 2.0 degrees)
    - timeout: Maximum time to try rotating in seconds (default 20)
    
    Returns:
    - dict: Status information including success/failure and measurements
    """
    if not robot_module_available:
        error_msg = "Robot module not available. Cannot execute rotation commands."
        logger.error(error_msg)
        return {"success": False, "error": error_msg}
    
    logger.info(f"Rotating to angle {target_angle}° at speed {speed}")
    
    # Reset gyroscope angles to start from zero with retries
    max_reset_attempts = 3
    reset_success = False
    
    for attempt in range(1, max_reset_attempts + 1):
        logger.info(f"Resetting gyroscope angles (attempt {attempt}/{max_reset_attempts})")
        if robot.resetGyroAngles():
            reset_success = True
            break
        time.sleep(0.5)  # Wait before retry
    
    if not reset_success:
        error_msg = f"Failed to reset gyroscope angles after {max_reset_attempts} attempts"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}
    
    time.sleep(0.2)  # Short delay to ensure reset is processed
    
    # Get initial gyroscope reading with retries
    gyro_data = None
    for attempt in range(1, 4):
        gyro_data = robot.getGyroData()
        if gyro_data:
            break
        logger.warning(f"Failed to get initial gyro reading, retrying ({attempt}/3)")
        time.sleep(0.2)
    
    if not gyro_data:
        error_msg = "Could not initialize gyroscope after 3 attempts"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}
    
    start_angle = gyro_data['angle_z']
    logger.info(f"Initial angle: {start_angle}°")
    
    start_time = time.time()
    last_print_time = start_time
    print_interval = 0.5  # Print debug info every 0.5 seconds
    
    try:
        while time.time() - start_time < timeout:
            # Determine direction and send command
            rotation_success = False
            for attempt in range(1, 4):
                if target_angle > 0:
                    # Turn right (clockwise)
                    if robot.right(speed):
                        rotation_success = True
                        if attempt > 1:
                            logger.info(f"Rotation command sent successfully on attempt {attempt}")
                        break
                else:
                    # Turn left (counter-clockwise)
                    if robot.left(speed):
                        rotation_success = True
                        if attempt > 1:
                            logger.info(f"Rotation command sent successfully on attempt {attempt}")
                        break
                logger.warning(f"Rotation command failed, retrying ({attempt}/3)")
                time.sleep(0.1)  # Short delay before retry
            
            if not rotation_success:
                error_msg = "Failed to send rotation command after 3 attempts"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
            
            # Wait a short time for rotation to have an effect
            time.sleep(0.1)
            
            # Get current gyroscope data with retries
            gyro_data = None
            for attempt in range(1, 4):
                gyro_data = robot.getGyroData()
                if gyro_data:
                    break
                time.sleep(0.05)
                
            if not gyro_data:
                logger.warning("Failed to get gyro data during rotation")
                continue
                
            current_angle = gyro_data['angle_z']
            angle_change = current_angle - start_angle
            
            # Print debug info periodically
            if time.time() - last_print_time > print_interval:
                debug_msg = f"Current: {current_angle:.2f}°, Change: {angle_change:.2f}°, Target: {target_angle}°"
                logger.info(debug_msg)
                print(debug_msg)
                last_print_time = time.time()
            
            # Check if we've reached the target angle
            if abs(angle_change - target_angle) <= tolerance:
                # Stop rotation with retries
                stop_success = False
                for attempt in range(1, 4):
                    if robot.stopLR():
                        stop_success = True
                        break
                    time.sleep(0.05)
                
                if not stop_success:
                    logger.warning("Failed to send stop command after reaching target angle")
                
                logger.info(f"Target angle reached! Final angle: {current_angle}°")
                return {
                    "success": True, 
                    "target": target_angle,
                    "actual": angle_change,
                    "final_reading": current_angle,
                    "time": time.time() - start_time
                }
            
            # Small delay to prevent CPU overload
            time.sleep(0.01)
            
        # If we get here, we've timed out
        # Stop rotation with retries
        stop_success = False
        for attempt in range(1, 4):
            if robot.stopLR():
                stop_success = True
                break
            time.sleep(0.05)
        
        if not stop_success:
            logger.warning("Failed to send stop command after timeout")
        
        # Get final angle with retries
        last_gyro = None
        for attempt in range(1, 4):
            last_gyro = robot.getGyroData()
            if last_gyro:
                break
            time.sleep(0.05)
        
        if last_gyro:
            current_angle = last_gyro['angle_z']
            angle_change = current_angle - start_angle
        else:
            current_angle = None
            angle_change = None
        
        timeout_msg = f"Rotation timed out after {timeout}s. Final angle: {current_angle}°"
        logger.warning(timeout_msg)
        return {
            "success": False,
            "error": "Timeout",
            "target": target_angle,
            "actual": angle_change,
            "final_reading": current_angle,
            "time": timeout
        }
            
    except Exception as e:
        # Ensure robot stops if there's an error
        try:
            for attempt in range(1, 4):
                if robot.stopLR():
                    logger.info("Emergency stop after error")
                    break
                time.sleep(0.05)
        except:
            pass
            
        error_msg = f"Error during rotation: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }

# Update available tools dictionary to include rotation and movement tools
available_tools = {
    "view_surroundings": view_surroundings,
    "rotate_to_angle": rotate_to_angle,
    "move_distance": move_distance
}

# Tool descriptions for documentation and help commands
tool_descriptions = [
    {
        "name": "view_surroundings",
        "description": "Take a photo and analyze what the robot can see",
        "parameters": []
    },
    {
        "name": "rotate_to_angle",
        "description": "Rotate the robot by a specified angle in degrees",
        "parameters": [
            {
                "name": "angle",
                "type": "number",
                "description": "Angle to rotate in degrees (positive for right, negative for left)"
            }
        ]
    },
    {
        "name": "move_distance",
        "description": "Move the robot forward or backward by a specified distance",
        "parameters": [
            {
                "name": "distance",
                "type": "number",
                "description": "Distance to move in centimeters (positive for forward, negative for backward)"
            }
        ]
    }
]

if __name__ == '__main__':
    # When run directly, test the camera and LLM
    print("Testing camera and LLM vision...")
    
    # Test the view_surroundings function
    print("\nTesting view_surroundings function:")
    description = view_surroundings()
    print(description)
    
    # Only run movement tests if robot module is available
    if robot_module_available:
        try:
            print("\nTesting movement functions:")
            print("1. Testing rotate_to_angle (10 degrees clockwise)")
            result = rotate_to_angle(10)
            print(f"Result: {result}")
            
            time.sleep(1)
            
            print("2. Testing move_distance (10 cm forward)")
            result = move_distance(10)
            print(f"Result: {result}")
        except Exception as e:
            print(f"Error during movement tests: {e}")

