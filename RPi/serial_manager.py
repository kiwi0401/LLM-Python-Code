#!/usr/bin/env/python3
# File name   : serial_manager.py
# Description : Serial communication manager for robot control.

import json
import logging
import time
import queue
import threading
import serial

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("robot.log")
    ]
)
logger = logging.getLogger("serial_manager")

# Serial communication manager
class SerialManager:
    def __init__(self, port="/dev/ttyS0", baudrate=115200, timeout=15):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout  # Increased from 10 to 15
        self.serial = None
        self.command_queue = queue.Queue()
        self.lock = threading.RLock()
        self.connected = False
        self.response_buffer = {}
        self.worker_thread = None
        self.running = False
        
        # Connect to serial port
        self.connect()
        
        # Start command processor thread
        self.start_worker()
    
    def connect(self):
        """Establish serial connection with retries"""
        max_attempts = 5
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"Attempting to connect to serial port (attempt {attempt}/{max_attempts})")
                self.serial = serial.Serial(
                    self.port, 
                    self.baudrate,
                    timeout=self.timeout,
                    write_timeout=self.timeout,
                )
                time.sleep(3)  # Allow time for the serial port to stabilize
                self.connected = True
                logger.info("Serial connection established successfully")
                return True
            except Exception as e:
                logger.error(f"Failed to connect to serial port (attempt {attempt}): {e}")
                time.sleep(0.5)
        
        logger.error(f"Failed to connect to serial port after {max_attempts} attempts")
        return False
    
    def reconnect(self):
        """Reconnect to the serial port"""
        logger.info("Attempting to reconnect to serial port")
        try:
            # Close existing connection if it exists
            if self.serial:
                try:
                    self.serial.close()
                    logger.debug("Closed existing serial connection")
                except Exception as e:
                    logger.warning(f"Error closing existing serial connection: {e}")
            
            # Create a new connection
            self.serial = serial.Serial(
                self.port, 
                self.baudrate,
                timeout=self.timeout,
                write_timeout=self.timeout,
            )
            time.sleep(1.5)  # Reduced stabilization time for command execution context
            self.connected = True
            logger.info("Serial connection reestablished successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to reconnect to serial port: {e}")
            self.connected = False
            return False
    
    def start_worker(self):
        """Start the worker thread to process commands"""
        self.running = True
        self.worker_thread = threading.Thread(target=self._process_commands)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        logger.info("Serial command processor thread started")
    
    def stop_worker(self):
        """Stop the worker thread"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(2.0)  # Wait up to 2 seconds
        logger.info("Serial command processor thread stopped")
    
    def _process_commands(self):
        """Worker thread function to process commands from queue"""
        while self.running:
            try:
                # Get command from queue with timeout
                cmd_data = self.command_queue.get(timeout=0.5)
                
                # Process command
                if cmd_data:
                    cmd_type = cmd_data.get('type')
                    command = cmd_data.get('command')
                    callback = cmd_data.get('callback')
                    retry_count = cmd_data.get('retry_count', 3)
                    
                    result = self._execute_command(cmd_type, command, retry_count)
                    
                    # Call the callback with result if provided
                    if callback:
                        callback(result)
                    
                    # Mark task as done
                    self.command_queue.task_done()
            
            except queue.Empty:
                # No commands in the queue, just continue
                pass
            except Exception as e:
                logger.error(f"Error in command processor: {e}")
    
    def _execute_command(self, cmd_type, command, retry_count=None):
        """Execute a serial command with maximum speed retries until timeout"""
        # Attempt reconnection before executing the command
        if not self.connected or not self.serial:
            logger.warning("Not connected to serial port, attempting to reconnect")
            if not self.reconnect():
                return {'success': False, 'error': 'Not connected to serial port and reconnection failed'}
        
        # Attempt a reconnection anyway to refresh the connection
        try:
            self.reconnect()
        except Exception as e:
            logger.warning(f"Preventive reconnection attempt failed: {e}")
            # Continue anyway with existing connection
        
        # Flush any lingering data before sending new command
        with self.lock:
            if self.serial.in_waiting:
                discarded = self.serial.read(self.serial.in_waiting)
                logger.debug(f"Discarded {len(discarded)} bytes from input buffer before command")
        
        # Set timeout for the entire operation (shorter for faster failure detection)
        overall_timeout = 5.0  # Reduced from 10.0 to 5.0 seconds
        start_time = time.time()
        attempt = 0
        
        # Keep trying until we succeed or time out - no delays between attempts
        while time.time() - start_time < overall_timeout:
            attempt += 1
            try:
                with self.lock:
                    # Clear input buffer for clean start
                    self.serial.reset_input_buffer()
                    
                    # Send command based on type
                    if cmd_type == 'json':
                        # Make sure JSON is properly formatted
                        if not isinstance(command, dict):
                            logger.error("JSON command must be a dictionary")
                            return {'success': False, 'error': 'Invalid JSON command format'}
                        
                        if 'var' not in command or 'val' not in command:
                            logger.error("JSON command must contain 'var' and 'val' fields")
                            return {'success': False, 'error': 'Missing required JSON fields'}
                        
                        # Send the JSON string with newline
                        cmd_str = json.dumps(command) + '\n'
                        self.serial.write(cmd_str.encode())
                        self.serial.flush()  # Ensure it's sent immediately
                        logger.debug(f"Sent JSON command (attempt {attempt}): {cmd_str.strip()}")
                    
                    elif cmd_type == 'text':
                        # Send text command with newline
                        cmd_str = command + '\n'
                        self.serial.write(cmd_str.encode())
                        self.serial.flush()  # Ensure it's sent immediately
                        logger.debug(f"Sent text command (attempt {attempt}): {cmd_str.strip()}")
                    
                    else:
                        logger.error(f"Unknown command type: {cmd_type}")
                        return {'success': False, 'error': f'Unknown command type: {cmd_type}'}
                    
                    # Check for immediate response without any delay
                    if self.serial.in_waiting:
                        # For JSON commands
                        if cmd_type == 'json':
                            response = self._check_for_ack()
                            if response:
                                logger.debug(f"Command succeeded on attempt {attempt} (immediate response)")
                                return {'success': True, 'response': response}
                        
                        # For text commands
                        elif cmd_type == 'text':
                            if command == 'GET_GYRO':
                                response = self._check_for_gyro_data()
                                if response:
                                    return {'success': True, 'data': response}
                            
                            elif command == 'GET_ACCEL':
                                response = self._check_for_accel_data()
                                if response:
                                    return {'success': True, 'data': response}
                            
                            elif command == 'RESET_GYRO':
                                response = self._check_for_response("ACK:GYRO_RESET")
                                if response:
                                    return {'success': True}
                            
                            elif command == 'PING':
                                response = self._check_for_response("PONG")
                                if response:
                                    return {'success': True}
                
                # Log only occasionally to avoid log spam
                if attempt % 20 == 0:
                    logger.debug(f"Command still waiting for response after {attempt} rapid attempts, time elapsed: {time.time() - start_time:.2f}s")
                
            except serial.SerialException as se:
                logger.error(f"Serial exception (attempt {attempt}): {se}")
                # Try to reconnect on serial exception
                if self.reconnect():
                    logger.info("Successfully reconnected after serial exception")
                    # No delay, continue immediately with next attempt
                continue
            except Exception as e:
                logger.error(f"Error executing command (attempt {attempt}): {e}")
                # No delay after error, continue immediately
        
        # If we get here, we've timed out
        elapsed = time.time() - start_time
        logger.error(f"Command failed after {attempt} rapid attempts ({elapsed:.2f}s elapsed): {command}")
        
        # Last resort: try reconnecting one more time
        if self.reconnect():
            logger.info("Final reconnection successful, checking buffer")
            
        # Last resort: check if there's anything in the buffer that might indicate success
        try:
            with self.lock:
                if self.serial.in_waiting:
                    last_chance_data = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='replace')
                    logger.debug(f"Last chance buffer check: {last_chance_data}")
                    if "ACK:" in last_chance_data or any(term in last_chance_data for term in ["Forward", "Backward", "TurnLeft", "TurnRight", "FBStop", "LRStop"]):
                        logger.info(f"Found delayed response, considering command successful: {last_chance_data}")
                        return {'success': True, 'response': last_chance_data}
        except Exception as e:
            logger.warning(f"Error in last resort buffer check: {e}")
            
        return {'success': False, 'error': f'Command timed out after {elapsed:.2f}s ({attempt} attempts)'}
    
    def _check_for_ack(self):
        """Quick check for acknowledgment response (non-blocking)"""
        if not self.serial.in_waiting:
            return None
        
        try:
            buffer = ""
            while self.serial.in_waiting:
                response = self.serial.readline().decode('utf-8', errors='replace').strip()
                buffer += response + "\n"
                
                # Skip command echo lines
                if response.startswith("COMMAND RECIEVED:"):
                    continue
                
                # Check for explicit acknowledgments
                if response == "ACK:CMD_PROCESSED":
                    logger.debug("Exact ACK match found")
                    return response
                
                # Other variants of ACK
                if response.startswith("ACK:"):
                    logger.debug(f"Found ACK variant: {response}")
                    return response
                
                # Command confirmations that imply success
                if any(cmd in response for cmd in ["Forward", "Backward", "TurnLeft", "TurnRight", "FBStop", "LRStop", 
                                                  "Steady ON", "Steady OFF", "Jump", "stayLow", "handshake", 
                                                  "ActionA", "ActionB", "ActionC"]):
                    logger.debug(f"Found command echo: {response}")
                    return "Implicit ACK from command echo"
        except Exception as e:
            logger.warning(f"Error checking for ACK: {e}")
        
        return None
    
    def _check_for_response(self, expected_response):
        """Quick check for specific response (non-blocking)"""
        if not self.serial.in_waiting:
            return None
        
        try:
            while self.serial.in_waiting:
                response = self.serial.readline().decode('utf-8', errors='replace').strip()
                
                # Skip command echo lines
                if response.startswith("COMMAND RECIEVED:"):
                    continue
                
                if response == expected_response:
                    return response
                
                # For RESET_GYRO, accept variations
                if expected_response == "ACK:GYRO_RESET" and "GYRO_RESET" in response:
                    return response
        except Exception as e:
            logger.warning(f"Error checking for response: {e}")
        
        return None
    
    def _check_for_gyro_data(self):
        """Quick check for gyroscope data (non-blocking)"""
        if not self.serial.in_waiting:
            return None
        
        try:
            buffer = ""
            while self.serial.in_waiting:
                response = self.serial.readline().decode('utf-8', errors='replace').strip()
                buffer += response + "\n"
                
                # Skip command echo lines
                if response.startswith("COMMAND RECIEVED:"):
                    continue
                
                # Check for gyro data
                if response.startswith("GYRO_DATA:"):
                    json_data = response[len("GYRO_DATA:"):]
                    try:
                        gyro_data = json.loads(json_data)
                        required_fields = ['gyro_x', 'gyro_y', 'gyro_z', 'angle_x', 'angle_y', 'angle_z']
                        if all(key in gyro_data for key in required_fields):
                            return gyro_data
                    except json.JSONDecodeError:
                        logger.debug(f"Invalid JSON in gyro data: {json_data}")
        except Exception as e:
            logger.warning(f"Error checking for gyro data: {e}")
        
        return None
    
    def _check_for_accel_data(self):
        """Quick check for accelerometer data (non-blocking)"""
        if not self.serial.in_waiting:
            return None
        
        try:
            buffer = ""
            while self.serial.in_waiting:
                response = self.serial.readline().decode('utf-8', errors='replace').strip()
                buffer += response + "\n"
                
                # Skip command echo lines
                if response.startswith("COMMAND RECIEVED:"):
                    continue
                
                # Check for accel data
                if response.startswith("ACCEL_DATA:"):
                    json_data = response[len("ACCEL_DATA:"):]
                    try:
                        accel_data = json.loads(json_data)
                        required_fields = ['acc_x', 'acc_y', 'acc_z']
                        if all(key in accel_data for key in required_fields):
                            return accel_data
                    except json.JSONDecodeError:
                        logger.debug(f"Invalid JSON in accel data: {json_data}")
        except Exception as e:
            logger.warning(f"Error checking for accel data: {e}")
        
        return None
    
    def _wait_for_gyro_data(self, timeout=2.0):
        """Legacy method maintained for compatibility"""
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            result = self._check_for_gyro_data()
            if result:
                return result
            time.sleep(0.05)
        return None
    
    def _wait_for_accel_data(self, timeout=2.0):
        """Legacy method maintained for compatibility"""
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            result = self._check_for_accel_data()
            if result:
                return result
            time.sleep(0.05)
        return None
    
    def _wait_for_ack(self, timeout=3.0):
        """Legacy method maintained for compatibility"""
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            result = self._check_for_ack()
            if result:
                return result
            time.sleep(0.05)
        return None
    
    def _wait_for_specific_response(self, expected_response, timeout=2.0):
        """Legacy method maintained for compatibility"""
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            result = self._check_for_response(expected_response)
            if result:
                return result
            time.sleep(0.05)
        return None
    
    def test_serial_connection(self):
        """Test if serial connection is working properly"""
        # Try a reconnection first
        if not self.reconnect():
            logger.error("Cannot test connection: Reconnection to serial port failed")
            return False
            
        # Use the rapid retry approach for testing
        start_time = time.time()
        timeout = 3.0  # 3 second timeout for test
        attempt = 0
        
        while time.time() - start_time < timeout:
            attempt += 1
            try:
                with self.lock:
                    self.serial.reset_input_buffer()
                    self.serial.write(b"PING\n")
                    self.serial.flush()
                    
                    # Check for response multiple times with minimal delay
                    for _ in range(5):
                        if self.serial.in_waiting:
                            response = self.serial.readline().decode('utf-8', errors='replace').strip()
                            logger.info(f"Received test response: '{response}'")
                            
                            if response == "PONG":
                                logger.info(f"Serial connection test successful on attempt {attempt}")
                                return True
                        time.sleep(0.05)
                
                # Very brief delay between attempts
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error during serial connection test (attempt {attempt}): {e}")
                time.sleep(0.1)
        
        logger.warning(f"Serial test failed after {attempt} attempts")
        return False
    
    def send_command(self, cmd_type, command, callback=None, retry_count=None):
        """Queue a command to be sent"""
        cmd_data = {
            'type': cmd_type,
            'command': command,
            'callback': callback,
            'retry_count': retry_count
        }
        self.command_queue.put(cmd_data)
        return True
    
    def send_command_sync(self, cmd_type, command, retry_count=None, timeout=15):
        """Send a command and wait for the result (synchronous)"""
        # Try to reconnect before sending the command
        if not self.connected:
            logger.warning("Not connected before sending command, attempting to reconnect")
            self.reconnect()
            
        result_container = {'result': None, 'event': threading.Event()}
        
        def callback(result):
            result_container['result'] = result
            result_container['event'].set()
        
        self.send_command(cmd_type, command, callback, retry_count)
        
        # Wait for the callback to be called
        if result_container['event'].wait(timeout):
            return result_container['result']
        else:
            logger.error(f"Timeout waiting for command result: {command}")
            return {'success': False, 'error': 'Timeout waiting for command result'}
    
    def close(self):
        """Close the serial connection and stop the worker thread"""
        self.stop_worker()
        if self.serial and self.connected:
            self.serial.close()
            logger.info("Serial connection closed")

# Initialize serial manager
def init_serial_manager():
    try:
        sm = SerialManager()
        logger.info("Serial manager initialized successfully")
        return sm
    except Exception as e:
        logger.error(f"Failed to initialize serial manager: {e}")
        return None
