#!/usr/bin/env/python3
# File name   : robot_commands.py
# Description : Robot command functions for interacting with the robot hardware

import json
import logging
import time
import os
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger("robot_commands")

# Reference to the serial manager, will be set by robot.py
serial_manager = None

def initialize(serial_mgr):
    """Initialize the robot commands module with the serial manager"""
    global serial_manager
    serial_manager = serial_mgr
    logger.info("Robot commands module initialized")

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
