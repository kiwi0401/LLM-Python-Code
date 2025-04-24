#!/usr/bin/env/python3
# File name   : robot.py
# Description : Robot interfaces.
import atexit
import base64
import datetime
import json
import logging
import os
import time

import serial
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("robot.log")
    ]
)
logger = logging.getLogger("robot")

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

# Add numpy and OpenCV imports at the top
try:
    import numpy as np
    import cv2
except ImportError:
    logger.warning("NumPy or OpenCV is not installed. Camera functionality will be limited.")

# Initialize serial connection
ser = serial.Serial("/dev/ttyS0", 115200)
dataCMD = json.dumps({'var': "", 'val': 0, 'ip': ""})
upperGlobalIP = 'UPPER IP'

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

pitch, roll = 0, 0


def setUpperIP(ipInput):
    global upperGlobalIP
    upperGlobalIP = ipInput


def forward(speed=100):
    dataCMD = json.dumps({'var': "move", 'val': 1})
    ser.write(dataCMD.encode())
    print('robot-forward')


def backward(speed=100):
    dataCMD = json.dumps({'var': "move", 'val': 5})
    ser.write(dataCMD.encode())
    print('robot-backward')


def left(speed=100):
    dataCMD = json.dumps({'var': "move", 'val': 2})
    ser.write(dataCMD.encode())
    print('robot-left')


def right(speed=100):
    dataCMD = json.dumps({'var': "move", 'val': 4})
    ser.write(dataCMD.encode())
    print('robot-right')


def stopLR():
    dataCMD = json.dumps({'var': "move", 'val': 6})
    ser.write(dataCMD.encode())
    print('robot-stop')


def stopFB():
    dataCMD = json.dumps({'var': "move", 'val': 3})
    ser.write(dataCMD.encode())
    print('robot-stop')


def lookUp():
    dataCMD = json.dumps({'var': "ges", 'val': 1})
    ser.write(dataCMD.encode())
    print('robot-lookUp')


def lookDown():
    dataCMD = json.dumps({'var': "ges", 'val': 2})
    ser.write(dataCMD.encode())
    print('robot-lookDown')


def lookStopUD():
    dataCMD = json.dumps({'var': "ges", 'val': 3})
    ser.write(dataCMD.encode())
    print('robot-lookStopUD')


def lookLeft():
    dataCMD = json.dumps({'var': "ges", 'val': 4})
    ser.write(dataCMD.encode())
    print('robot-lookLeft')


def lookRight():
    dataCMD = json.dumps({'var': "ges", 'val': 5})
    ser.write(dataCMD.encode())
    print('robot-lookRight')


def lookStopLR():
    dataCMD = json.dumps({'var': "ges", 'val': 6})
    ser.write(dataCMD.encode())
    print('robot-lookStopLR')


def steadyMode():
    dataCMD = json.dumps({'var': "funcMode", 'val': 1})
    ser.write(dataCMD.encode())
    print('robot-steady')


def jump():
    dataCMD = json.dumps({'var': "funcMode", 'val': 4})
    ser.write(dataCMD.encode())
    print('robot-jump')


def handShake():
    dataCMD = json.dumps({'var': "funcMode", 'val': 3})
    ser.write(dataCMD.encode())
    print('robot-handshake')


def lightCtrl(colorName, cmdInput):
    colorNum = 0
    if colorName == 'off':
        colorNum = 0
    elif colorName == 'blue':
        colorNum = 1
    elif colorName == 'red':
        colorNum = 2
    elif colorName == 'green':
        colorNum = 3
    elif colorName == 'yellow':
        colorNum = 4
    elif colorName == 'cyan':
        colorNum = 5
    elif colorName == 'magenta':
        colorNum = 6
    elif colorName == 'cyber':
        colorNum = 7
    dataCMD = json.dumps({'var': "light", 'val': colorNum})
    ser.write(dataCMD.encode())


def buzzerCtrl(buzzerCtrl, cmdInput):
    dataCMD = json.dumps({'var': "buzzer", 'val': buzzerCtrl})
    ser.write(dataCMD.encode())


def getGyroDataSingle():
    """
    Single attempt to request gyroscope data from the robot
    Returns a dictionary with gyro data or None on error
    """
    # Clear any existing data in the buffer
    ser.reset_input_buffer()

    # Send request command for gyroscope data
    ser.write("GET_GYRO\n".encode())

    # Wait for response with timeout
    start_time = time.time()
    timeout = 0.05  # Short timeout for quicker retries

    while (time.time() - start_time) < timeout:
        if ser.in_waiting:
            try:
                response = ser.readline().decode('utf-8').strip()

                # Check for the identifier prefix to ensure we're reading the right message
                if response.startswith("GYRO_DATA:"):
                    # Extract the JSON part
                    json_data = response[len("GYRO_DATA:"):]

                    try:
                        # Parse JSON response
                        gyro_data = json.loads(json_data)

                        # Validate that the response has the expected fields
                        required_fields = ['gyro_x', 'gyro_y', 'gyro_z', 'angle_x', 'angle_y', 'angle_z']
                        if all(key in gyro_data for key in required_fields):
                            return gyro_data
                        else:
                            print("Error: Incomplete gyroscope data received")
                            return None
                    except json.JSONDecodeError:
                        print(f"Error: Failed to parse gyroscope data JSON: {json_data}")
                        return None
            except UnicodeDecodeError:
                # Bad data, continue looking
                pass

        # Small delay to prevent CPU overload
        time.sleep(0.005)

    # If we get here, we timed out
    return None


def getGyroData():
    """
    Request gyroscope data with retries
    Makes up to 5 attempts to get valid data
    Returns a dictionary with gyro_x, gyro_y, gyro_z, angle_x, angle_y, angle_z values or None if all attempts fail
    """
    max_attempts = 5

    for attempt in range(1, max_attempts + 1):
        gyro_data = getGyroDataSingle()
        if gyro_data:
            return gyro_data

        # If not the last attempt, print message and wait a tiny bit before retry
        if attempt < max_attempts:
            print(f"Retry {attempt}/{max_attempts} for gyro data")
            time.sleep(0.01)  # Small delay between retries

    print(f"Error: Failed to get gyro data after {max_attempts} attempts")
    return None


def resetGyroAngles():
    """Reset the cumulative gyroscope angles on the robot"""
    ser.reset_input_buffer()
    ser.write("RESET_GYRO\n".encode())

    # Wait for acknowledgement
    start_time = time.time()
    timeout = 1.0

    while (time.time() - start_time) < timeout:
        if ser.in_waiting:
            response = ser.readline().decode('utf-8').strip()
            if response == "ACK:GYRO_RESET":
                return True
        time.sleep(0.01)

    print("Error: No acknowledgement received for gyro reset")
    return False


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
            print(f"Capturing image {i + 1}/{num_screenshots}...")
            ret, frame = camera.read()

            if not ret:
                print(f"Error: Could not capture frame {i + 1}")
                continue

            # Generate filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}_{i + 1}.jpg"
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


def test_camera(num_screenshots=1, delay=1, save_dir=None):
    """
    Legacy method that now uses the new takeScreenshot method.
    """
    return takeScreenshot(num_screenshots, delay, save_dir)


if __name__ == '__main__':
    resetGyroAngles()

    # Example of how to get gyroscope data
    while True:
        # Get and print gyroscope data
        gyro = getGyroData()
        if gyro:
            print("Gyro X: {:.4f}, Y: {:.4f}, Z: {:.4f}".format(
                gyro['gyro_x'], gyro['gyro_y'], gyro['gyro_z']))
            print("Angle X: {:.4f}, Y: {:.4f}, Z: {:.4f}".format(
                gyro['angle_x'], gyro['angle_y'], gyro['angle_z']))

        # Wait between readings
        time.sleep(0.5)
