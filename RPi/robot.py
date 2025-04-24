#!/usr/bin/env/python3
# File name   : robot.py
# Description : Robot interfaces and core movement controls.
import json
import logging
import sys
import time
import os
import queue
import threading

from dotenv import load_dotenv
from serial_manager import SerialManager, init_serial_manager

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

# Initialize serial manager
try:
    serial_manager = init_serial_manager()
except Exception as e:
    logger.error(f"Failed to initialize serial manager: {e}")
    serial_manager = None

dataCMD = json.dumps({'var': "", 'val': 0, 'ip': ""})
upperGlobalIP = 'UPPER IP'

pitch, roll = 0, 0

# Constants for movement speed
MOVE_FORWARD_SPEED = 70  # Reduced speed for more controlled movement
MOVE_BACKWARD_SPEED = 70
TURN_SPEED = 60  # Reduced speed for more precise rotation

# Constants for time-based movement (cm/sec)
FORWARD_SPEED_CM_PER_SEC = 15
BACKWARD_SPEED_CM_PER_SEC = 20


def setUpperIP(ipInput):
    global upperGlobalIP
    upperGlobalIP = ipInput


def forward(speed=100):
    if not serial_manager:
        logger.error("Serial manager not available, can't send forward command")
        return False
    
    command = {'var': "move", 'val': 1}
    result = serial_manager.send_command_sync('json', command)
    
    if result and result.get('success'):
        logger.info(f'Command sent: robot-forward (speed={speed})')
        print('robot-forward')
        return True
    else:
        error = result.get('error', 'Unknown error')
        logger.error(f"Failed to send forward command: {error}")
        return False


def backward(speed=100):
    if not serial_manager:
        logger.error("Serial manager not available, can't send backward command")
        return False
    
    command = {'var': "move", 'val': 5}
    result = serial_manager.send_command_sync('json', command)
    
    if result and result.get('success'):
        logger.info(f'Command sent: robot-backward (speed={speed})')
        print('robot-backward')
        return True
    else:
        error = result.get('error', 'Unknown error')
        logger.error(f"Failed to send backward command: {error}")
        return False


def left(speed=100):
    if not serial_manager:
        logger.error("Serial manager not available, can't send left command")
        return False
    
    command = {'var': "move", 'val': 2}
    result = serial_manager.send_command_sync('json', command)
    
    if result and result.get('success'):
        logger.info(f'Command sent: robot-left (speed={speed})')
        print('robot-left')
        return True
    else:
        error = result.get('error', 'Unknown error')
        logger.error(f"Failed to send left command: {error}")
        return False


def right(speed=100):
    if not serial_manager:
        logger.error("Serial manager not available, can't send right command")
        return False
    
    command = {'var': "move", 'val': 4}
    result = serial_manager.send_command_sync('json', command)
    
    if result and result.get('success'):
        logger.info(f'Command sent: robot-right (speed={speed})')
        print('robot-right')
        return True
    else:
        error = result.get('error', 'Unknown error')
        logger.error(f"Failed to send right command: {error}")
        return False


def stopLR():
    if not serial_manager:
        logger.error("Serial manager not available, can't send stopLR command")
        return False
    
    command = {'var': "move", 'val': 6}
    result = serial_manager.send_command_sync('json', command)
    
    if result and result.get('success'):
        logger.info('Command sent: robot-stop LR')
        print('robot-stop')
        return True
    else:
        error = result.get('error', 'Unknown error')
        logger.error(f"Failed to send stopLR command: {error}")
        return False


def stopFB():
    if not serial_manager:
        logger.error("Serial manager not available, can't send stopFB command")
        return False
    
    command = {'var': "move", 'val': 3}
    result = serial_manager.send_command_sync('json', command)
    
    if result and result.get('success'):
        logger.info('Command sent: robot-stop FB')
        print('robot-stop')
        return True
    else:
        error = result.get('error', 'Unknown error')
        logger.error(f"Failed to send stopFB command: {error}")
        return False


def lookUp():
    if not serial_manager:
        return False
    
    command = {'var': "ges", 'val': 1}
    result = serial_manager.send_command_sync('json', command)
    
    if result and result.get('success'):
        print('robot-lookUp')
        return True
    return False


def lookDown():
    if not serial_manager:
        return False
    
    command = {'var': "ges", 'val': 2}
    result = serial_manager.send_command_sync('json', command)
    
    if result and result.get('success'):
        print('robot-lookDown')
        return True
    return False


def lookStopUD():
    if not serial_manager:
        return False
    
    command = {'var': "ges", 'val': 3}
    result = serial_manager.send_command_sync('json', command)
    
    if result and result.get('success'):
        print('robot-lookStopUD')
        return True
    return False


def lookLeft():
    if not serial_manager:
        return False
    
    command = {'var': "ges", 'val': 4}
    result = serial_manager.send_command_sync('json', command)
    
    if result and result.get('success'):
        print('robot-lookLeft')
        return True
    return False


def lookRight():
    if not serial_manager:
        return False
    
    command = {'var': "ges", 'val': 5}
    result = serial_manager.send_command_sync('json', command)
    
    if result and result.get('success'):
        print('robot-lookRight')
        return True
    return False


def lookStopLR():
    if not serial_manager:
        return False
    
    command = {'var': "ges", 'val': 6}
    result = serial_manager.send_command_sync('json', command)
    
    if result and result.get('success'):
        print('robot-lookStopLR')
        return True
    return False


def resetGyroAngles():
    """Reset the robot's internal gyroscope angle tracking"""
    if not serial_manager:
        logger.error("Serial manager not available, can't reset gyro angles")
        return False
    
    result = serial_manager.send_command_sync('text', 'RESET_GYRO')
    
    if result and result.get('success'):
        logger.info('Successfully reset gyroscope angles')
        return True
    else:
        error = result.get('error', 'Unknown error')
        logger.error(f"Failed to reset gyro angles: {error}")
        return False


def steadyMode():
    if not serial_manager:
        return False
    
    command = {'var': "funcMode", 'val': 1}
    result = serial_manager.send_command_sync('json', command)
    
    if result and result.get('success'):
        print('robot-steady')
        return True
    return False


def jump():
    if not serial_manager:
        return False
    
    command = {'var': "funcMode", 'val': 4}
    result = serial_manager.send_command_sync('json', command)
    
    if result and result.get('success'):
        print('robot-jump')
        return True
    return False


def handShake():
    if not serial_manager:
        return False
    
    command = {'var': "funcMode", 'val': 3}
    result = serial_manager.send_command_sync('json', command)
    
    if result and result.get('success'):
        print('robot-handshake')
        return True
    return False


def stayLow():
    if not serial_manager:
        return False
    
    command = {'var': "funcMode", 'val': 2}
    result = serial_manager.send_command_sync('json', command)
    
    if result and result.get('success'):
        print('robot-stayLow')
        return True
    return False


def actionA():
    if not serial_manager:
        return False
    
    command = {'var': "funcMode", 'val': 5}
    result = serial_manager.send_command_sync('json', command)
    
    if result and result.get('success'):
        print('robot-actionA')
        return True
    return False


def actionB():
    if not serial_manager:
        return False
    
    command = {'var': "funcMode", 'val': 6}
    result = serial_manager.send_command_sync('json', command)
    
    if result and result.get('success'):
        print('robot-actionB')
        return True
    return False


def actionC():
    if not serial_manager:
        return False
    
    command = {'var': "funcMode", 'val': 7}
    result = serial_manager.send_command_sync('json', command)
    
    if result and result.get('success'):
        print('robot-actionC')
        return True
    return False


def lightCtrl(colorName, cmdInput):
    if not serial_manager:
        return False
        
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
        
    command = {'var': "light", 'val': colorNum}
    result = serial_manager.send_command_sync('json', command)
    
    return result and result.get('success', False)


def buzzerCtrl(buzzerCtrl, cmdInput):
    if not serial_manager:
        return False
        
    command = {'var': "buzzer", 'val': buzzerCtrl}
    result = serial_manager.send_command_sync('json', command)
    
    return result and result.get('success', False)


def diagnoseSerialIssues():
    """Run a comprehensive diagnostic on serial communication"""
    print("\n===== Serial Connection Diagnostics =====")
    
    if not serial_manager:
        print("❌ Serial manager not initialized!")
        logger.error("Serial manager not initialized, can't diagnose")
        return False
    
    # 1. Check if connection exists
    if not serial_manager.connected:
        print("❌ Serial not connected!")
        logger.error("Serial not connected")
        return False
    
    print("✓ Serial manager initialized")
    print(f"Port: {serial_manager.port}")
    print(f"Baudrate: {serial_manager.baudrate}")
    
    # 2. Test basic connectivity
    print("\nTesting basic serial connectivity...")
    ping_result = serial_manager.send_command_sync('text', 'PING', retry_count=5)
    if ping_result.get('success', False):
        print("✓ Communication test passed")
    else:
        print("❌ Communication test failed!")
        
    # 3. Try to get sensor data
    print("\nTesting gyroscope data retrieval...")
    print("Resetting gyroscope angles...")
    resetGyroAngles()  # Reset angles before testing
    print("✓ Gyroscope angles reset")
    print("Waiting for 1 second...")
    time.sleep(1)  # Allow some time for the reset to take effect
    gyro = getGyroData()
    if gyro:
        print("✓ Gyroscope data received:")
        print(f"  Rotation rates: X={gyro['gyro_x']:+8.4f}, Y={gyro['gyro_y']:+8.4f}, Z={gyro['gyro_z']:+8.4f}")
        print(f"  Cumulative angles: X={gyro['angle_x']:+8.4f}, Y={gyro['angle_y']:+8.4f}, Z={gyro['angle_z']:+8.4f}")
    else:
        print("❌ Failed to get gyroscope data!")
        
        # Try alternative sensors
        print("\nTrying accelerometer as alternative...")
        accel = getAccelData()
        if accel:
            print("✓ Accelerometer data received:")
            print(f"  Acceleration: X={accel['acc_x']:+8.4f}, Y={accel['acc_y']:+8.4f}, Z={accel['acc_z']:+8.4f}")
        else:
            print("❌ Failed to get accelerometer data!")
    
    print("\n===== Diagnostic Complete =====")
    return True

def testSerialConnection():
    """Simple test of serial connection with ping"""
    if not serial_manager:
        return False
    
    try:
        result = serial_manager.send_command_sync('text', 'PING', retry_count=1)
        return result.get('success', False)
    except Exception as e:
        logger.error(f"Error testing serial connection: {e}")
        return False

def getGyroData():
    """Get gyroscope data from the robot"""
    if not serial_manager:
        return None
    
    try:
        result = serial_manager.send_command_sync('text', 'GET_GYRO', retry_count=1)
        if result.get('success', False):
            return result.get('data')
        return None
    except Exception as e:
        logger.error(f"Error getting gyro data: {e}")
        return None

def getAccelData():
    """Get accelerometer data from the robot"""
    if not serial_manager:
        return None
    
    try:
        result = serial_manager.send_command_sync('text', 'GET_ACCEL', retry_count=1)
        if result.get('success', False):
            return result.get('data')
        return None
    except Exception as e:
        logger.error(f"Error getting accelerometer data: {e}")
        return None

def test_movement_sequence():
    """Run a simple movement test sequence"""
    if not serial_manager:
        print("Serial manager not initialized!")
        return
        
    print("\n===== Testing Robot Movement =====")
    
    # First test connection
    print("1. Testing communication...")
    if not testSerialConnection():
        print("❌ Failed to communicate with robot, aborting movement test")
        return
    print("✓ Communication successful")
    
    # Try a simple movement command
    print("\n2. Testing forward movement...")
    move_cmd = {'var': 'move', 'val': 1}  # 1 = Forward
    result = serial_manager.send_command_sync('json', move_cmd)
    print(f"Result: {result}")
    
    # Wait a moment
    time.sleep(1)
    
    # Stop movement
    print("\n3. Stopping movement...")
    stop_cmd = {'var': 'move', 'val': 3}  # 3 = FBStop
    result = serial_manager.send_command_sync('json', stop_cmd)
    print(f"Result: {result}")
    
    print("\n===== Movement Sequence Complete =====")

# rotate_to_angle and move_distance functions have been moved to tools.py

if __name__ == '__main__':
    if len(sys.argv) > 1:
        # Process command line arguments
        if sys.argv[1] == "diagnose":
            # Run diagnostic tests
            diagnoseSerialIssues()
            sys.exit(0)
        elif sys.argv[1] == "test_serial":
            # Just test serial connection
            testSerialConnection()
            sys.exit(0)
        elif sys.argv[1] == "reset_gyro":
            # Reset gyroscope angles
            if resetGyroAngles():
                print("Gyroscope angles reset successfully")
            else:
                print("Failed to reset gyroscope angles")
            sys.exit(0)
        elif sys.argv[1] == "test_movement":
            # Run movement test
            try:
                # Import tools dynamically to avoid circular imports
                sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                from tools import move_distance, rotate_to_angle
                
                print("\n===== Testing Robot Movement =====")
                
                # Test sequence: forward 1 meter, rotate 45 degrees, rotate back -45 degrees
                print("\n1. Moving forward 100 cm (1 meter)...")
                result = move_distance(100)
                print(f"Result: {result}")
                
                # Wait between movements
                print("Waiting 2 seconds...")
                time.sleep(2)
                
                print("\n2. Rotating 45 degrees clockwise...")
                result = rotate_to_angle(45)
                print(f"Result: {result}")
                
                # Wait between movements
                print("Waiting 2 seconds...")
                time.sleep(2)
                
                print("\n3. Rotating 45 degrees counter-clockwise...")
                result = rotate_to_angle(-45)
                print(f"Result: {result}")
                
                print("\n===== Movement Test Complete =====")
                
                sys.exit(0)
            except ImportError as e:
                print(f"Error importing tools module: {e}")
                logger.error(f"Error importing tools module: {e}")
                sys.exit(1)
            except Exception as e:
                print(f"Error during movement test: {e}")
                logger.error(f"Error during movement test: {e}", exc_info=True)
                sys.exit(1)
        elif sys.argv[1] == "test_sequence":
            try:
                test_movement_sequence()
                sys.exit(0)
            except ImportError:
                print("Error: Could not import movement tools from tools.py")
                sys.exit(1)
            except Exception as e:
                print(f"Error during movement sequence: {e}")
                sys.exit(1)
    
    # Default behavior - improved diagnostics and monitoring
    print("\nRunning basic serial diagnostics first...")
    diagnoseSerialIssues()
    
    print("\nStarting continuous gyro monitoring (Ctrl+C to exit)...")
    while True:
        try:
            # Get and print gyroscope data
            gyro = getGyroData()
            if gyro:
                print("\nGyroscope Data:")
                print(f"  Rotation rates (°/s): X={gyro['gyro_x']:+8.4f}, Y={gyro['gyro_y']:+8.4f}, Z={gyro['gyro_z']:+8.4f}")
                print(f"  Cumulative angles (°): X={gyro['angle_x']:+8.4f}, Y={gyro['angle_y']:+8.4f}, Z={gyro['angle_z']:+8.4f}")
            else:
                print("No gyroscope data received, trying again...")
            time.sleep(2)  # Short delay between data requests
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")
            logger.error(f"Error in monitoring loop: {e}", exc_info=True)
            time.sleep(2)  # Add delay to avoid rapid error loops
    
    # Check for command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "test_movement":
        # Import tools for testing movement
        try:
            from tools import rotate_to_angle, move_distance
            
            print("\n===== Testing Robot Movement =====")
            
            # Test sequence: forward 1 meter, rotate 45 degrees, rotate back -45 degrees
            print("\n1. Moving forward 100 cm (1 meter)...")
            result = move_distance(100)
            print(f"Result: {result}")
            
            # Wait between movements
            print("Waiting 2 seconds...")
            time.sleep(2)
            
            print("\n2. Rotating 45 degrees clockwise...")
            result = rotate_to_angle(45)
            print(f"Result: {result}")
            
            # Wait between movements
            print("Waiting 2 seconds...")
            time.sleep(2)
            
            print("\n3. Rotating 45 degrees counter-clockwise...")
            result = rotate_to_angle(-45)
            print(f"Result: {result}")
            
            print("\n===== Movement Test Complete =====")
            
            sys.exit(0)
        except ImportError:
            print("Error: Could not import movement tools from tools.py")
            sys.exit(1)
        except Exception as e:
            print(f"Error during movement test: {e}")
            sys.exit(1)
    
    # Default camera test if no specific test is requested
    # Import tools only when needed
    from tools import test_camera, view_surroundings

    # Parse optional arguments for number of screenshots and delay
    num_screenshots = 1
    delay = 1

    if len(sys.argv) > 2:
        try:
            num_screenshots = int(sys.argv[2])
        except ValueError:
            pass

    if len(sys.argv) > 3:
        try:
            delay = float(sys.argv[3])
        except ValueError:
            pass

    test_camera(num_screenshots, delay)

    # Test view_surroundings function
    try:
        print("\nTesting view_surroundings function:")
        description = view_surroundings()
        print(description)
    except Exception as e:
        print(f"Error testing view_surroundings: {e}")
