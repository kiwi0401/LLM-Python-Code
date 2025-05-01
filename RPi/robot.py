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

# Add OpenAI import
from openai import OpenAI

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

# Import robot commands and initialize with serial manager
import robot_commands
robot_commands.initialize(serial_manager)

# For backwards compatibility, import all functions from robot_commands into the global namespace
from robot_commands import *

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

# Try to import audio processing module
try:
    import robot_audio
    audio_available = True
    logger.info("Audio processing module loaded successfully")
except ImportError as e:
    audio_available = False
    logger.error(f"Failed to import audio processing module: {e}")

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

def run_bot():
    """Run the robot with LLM-powered tool calling and voice control"""
    print("\n===== Starting Voice-Controlled LLM-powered Robot =====")
    
    # Check if audio processing is available
    if not audio_available:
        print("❌ Audio processing module not available. Falling back to non-voice mode.")
        return run_bot_non_voice()
    
    # Initialize audio processing components
    audio_components = robot_audio.setup_audio_processing()
    if not audio_components:
        print("❌ Failed to initialize audio processing. Falling back to non-voice mode.")
        return run_bot_non_voice()
    
    # Extract audio components
    openai_client = audio_components["openai_client"]
    tts_engine = audio_components["tts_engine"]
    recognizer = audio_components["recognizer"]
    audio_queue = audio_components["audio_queue"]
    stop_event = audio_components["stop_event"]
    
    # Load tools from the tools description file
    tool_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tool_descriptions.json')
    try:
        with open(tool_file_path, 'r') as f:
            tool_data = json.load(f)
            tools = tool_data.get('tools', [])
            if not tools:
                logger.warning("No tools found in tool_descriptions.json")
                print("⚠️ Warning: No tools found in tool_descriptions.json")
                return False
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error loading tool descriptions: {e}")
        print(f"❌ Error loading tool descriptions: {e}")
        return False
    
    # Load the dog_actions prompt
    prompt_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dog_actions.md')
    try:
        with open(prompt_file_path, 'r') as f:
            prompt_content = f.read()
    except FileNotFoundError:
        logger.error(f"Prompt file not found at {prompt_file_path}")
        print(f"❌ Error: Prompt file not found at {prompt_file_path}")
        return False
    
    try:
        print("Voice assistant is now listening for the wake phrase...")
        tts_engine.say("Robot is ready and listening")
        tts_engine.runAndWait()
        
        # Initialize conversation history with system prompt
        messages = [
            {"role": "system", "content": prompt_content}
        ]
        
        running = True
        while running:
            try:
                # 1. Wait for the wake word
                robot_audio.wait_for_wake_word(recognizer, audio_queue)
                print("Wake word detected!")
                
                # Optional: Visual or sound indication that wake word was detected
                try:
                    lightCtrl("blue", 0)  # Blue light to indicate active listening
                except:
                    pass
                
                # 2. Listen for the command
                command_text = robot_audio.listen_for_command(recognizer, audio_queue, tts_engine)
                if not command_text:
                    print("No command detected. Listening for wake word again...")
                    robot_audio.flush_audio_queue(audio_queue)
                    recognizer.Reset()
                    continue
                
                print(f"Command received: '{command_text}'")
                
                # 3. Add user command to message history
                messages.append({"role": "user", "content": command_text})
                
                # 4. Make the tool calling request to OpenAI and process all tool calls
                try:
                    # Initialize a flag to track if we need to continue tool processing
                    has_pending_tools = True
                    tool_iteration = 0
                    max_tool_iterations = 5  # Prevent infinite loops
                    
                    # Process tool calls until complete or max iterations reached
                    while has_pending_tools and tool_iteration < max_tool_iterations:
                        tool_iteration += 1
                        
                        print(f"\nProcessing tool iteration {tool_iteration}/{max_tool_iterations}...")
                        
                        # Make the tool calling request to OpenAI
                        completion = openai_client.chat.completions.create(
                            model="gpt-4o",
                            messages=messages,
                            tools=tools
                        )
                        
                        # Process and display the response
                        message = completion.choices[0].message
                        print("\nLLM Response:")
                        print(message.content)
                        
                        # Add assistant's response to the message history
                        messages.append({
                            "role": "assistant",
                            "content": message.content,
                            **({"tool_calls": message.tool_calls} if message.tool_calls else {})
                        })
                        
                        # Only speak the response on the first iteration
                        if tool_iteration == 1 or tool_iteration == 2:
                            tts_engine.say(message.content)
                            tts_engine.runAndWait()
                        
                        # Check if there are tool calls
                        if message.tool_calls:
                            print(f"\nTool Calls Received (Iteration {tool_iteration}):")
                            has_pending_tools = True
                            
                            for tool_call in message.tool_calls:
                                print(f"Tool ID: {tool_call.id}")
                                print(f"Function: {tool_call.function.name}")
                                print(f"Arguments: {tool_call.function.arguments}")
                                
                                # Execute the tool call
                                try:
                                    name = tool_call.function.name
                                    args = json.loads(tool_call.function.arguments) if tool_call.function.arguments.strip() else {}
                                    
                                    # Call the function and get the result
                                    result = call_function(name, args)
                                    
                                    # Add the result to the message history
                                    messages.append({
                                        "role": "tool",
                                        "tool_call_id": tool_call.id,
                                        "content": str(result)
                                    })
                                    
                                    print(f"Tool result: {result}")
                                    
                                    # Only provide audio feedback for the final result or first iteration
                                    if (tool_iteration == 1 or not has_pending_tools) and isinstance(result, str) and len(result) < 100:
                                        tts_engine.say(f"Task complete: {result}")
                                        tts_engine.runAndWait()
                                    
                                except Exception as e:
                                    error_msg = f"Error processing tool call: {str(e)}"
                                    logger.error(error_msg, exc_info=True)
                                    messages.append({
                                        "role": "tool",
                                        "tool_call_id": tool_call.id,
                                        "content": f"Error: {error_msg}"
                                    })
                                    tts_engine.say("Error executing command")
                                    tts_engine.runAndWait()
                        else:
                            # No more tool calls, we're done with this cycle
                            print("\nNo more tool calls for this command.")
                            has_pending_tools = False
                            break
                    
                    # Provide feedback if we hit the iteration limit
                    if tool_iteration >= max_tool_iterations and has_pending_tools:
                        print(f"\nReached maximum tool iterations ({max_tool_iterations}), stopping.")
                        tts_engine.say("Action sequence too long. Some steps may not have completed.")
                        tts_engine.runAndWait()
                        
                    # Final confirmation once all tool chains are complete
                    if tool_iteration > 1:  # Only if we ran multiple tool iterations
                        tts_engine.say("All actions completed")
                        tts_engine.runAndWait()
                        
                except Exception as e:
                    logger.error(f"Error in LLM tool calling: {e}", exc_info=True)
                    print(f"❌ Error in LLM tool calling: {e}")
                    tts_engine.say("I encountered an error processing your request")
                    tts_engine.runAndWait()
                    
                # Flush the audio queue and reset the recognizer for the next command
                robot_audio.flush_audio_queue(audio_queue)
                recognizer.Reset()
                
                # Add clear feedback that we're ready for the next command
                print("\n-----------------------------------------")
                print("✓ Command cycle complete. Listening for wake word again...")
                tts_engine.say("Ready for next command")
                tts_engine.runAndWait()
                
                # Periodically trim conversation history to prevent it from getting too long
                if len(messages) > 10:  # Keep system message plus last 9 exchanges
                    system_message = messages[0]
                    messages = [system_message] + messages[-9:]
                
            except KeyboardInterrupt:
                print("\nKeyboard interrupt received. Exiting...")
                running = False
            except Exception as e:
                logger.error(f"Error in voice control loop: {e}", exc_info=True)
                print(f"❌ Error in voice control loop: {e}")
                # Try to recover and continue
                robot_audio.flush_audio_queue(audio_queue)
                recognizer.Reset()
                
    finally:
        # Clean up resources
        stop_event.set()  # Signal the audio callback to stop
        robot_audio.cleanup_audio(audio_components["stream"], 
                                 audio_components["pyaudio"], 
                                 audio_components["tts_engine"])
        try:
            lightCtrl("off", 0)  # Turn off any lights
        except:
            pass
    
    print("\n===== Voice Control Session Ended =====")
    return True

def run_bot_non_voice():
    """Run the robot with LLM-powered tool calling for autonomous operation (non-voice mode)"""
    print("\n===== Starting LLM-powered Robot (Non-voice Mode) =====")
    
    # Initialize OpenAI client
    try:
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        print(f"❌ Error initializing OpenAI client: {e}")
        return False
    
    # Load tools from the tools description file
    tool_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tool_descriptions.json')
    try:
        with open(tool_file_path, 'r') as f:
            tool_data = json.load(f)
            tools = tool_data.get('tools', [])
            if not tools:
                logger.warning("No tools found in tool_descriptions.json")
                print("⚠️ Warning: No tools found in tool_descriptions.json")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error loading tool descriptions: {e}")
        print(f"❌ Error loading tool descriptions: {e}")
        return False
    
    # Load the dog_actions prompt
    prompt_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dog_actions.md')
    try:
        with open(prompt_file_path, 'r') as f:
            prompt_content = f.read()
    except FileNotFoundError:
        logger.error(f"Prompt file not found at {prompt_file_path}")
        print(f"❌ Error: Prompt file not found at {prompt_file_path}")
        return False
    
    # Initialize message history
    messages = [
        {"role": "system", "content": prompt_content},
        {"role": "user", "content": "Can you tell me what you see?"}
    ]
    
    # Maximum number of iterations to prevent infinite loops
    max_iterations = 5
    current_iteration = 0
    
    while current_iteration < max_iterations:
        current_iteration += 1
        print(f"\nSending request to LLM (iteration {current_iteration}/{max_iterations})...")
        
        try:
            # Make the tool calling request to OpenAI
            completion = client.chat.completions.create(
                model="gpt-4o",  # Using gpt-4o as it supports tool calling
                messages=messages,
                tools=tools
            )
            
            # Process and display the response
            message = completion.choices[0].message
            print("\nLLM Response:")
            print(message.content)
            
            # Add assistant's response to the message history
            messages.append({
                "role": "assistant",
                "content": message.content,
                **({"tool_calls": message.tool_calls} if message.tool_calls else {})
            })
            
            # Check if there are tool calls
            if message.tool_calls:
                print("\nTool Calls Received:")
                for tool_call in message.tool_calls:
                    print(f"Tool ID: {tool_call.id}")
                    print(f"Function: {tool_call.function.name}")
                    print(f"Arguments: {tool_call.function.arguments}")
                    
                    # Execute the tool call
                    try:
                        name = tool_call.function.name
                        args = json.loads(tool_call.function.arguments) if tool_call.function.arguments.strip() else {}
                        
                        # Call the function and get the result
                        result = call_function(name, args)

                        print(result)
                        
                        # Add the result to the message history
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": str(result)
                        })
                        
                        print(f"Tool result: {result}")
                    except Exception as e:
                        error_msg = f"Error processing tool call: {str(e)}"
                        logger.error(error_msg, exc_info=True)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": f"Error: {error_msg}"
                        })
            else:
                # No more tool calls, we're done
                print("\nNo more tool calls, conversation complete.")
                break
                
        except Exception as e:
            logger.error(f"Error in LLM tool calling: {e}", exc_info=True)
            print(f"❌ Error in LLM tool calling: {e}")
            return False
    
    if current_iteration >= max_iterations:
        print(f"\nReached maximum iterations ({max_iterations}), stopping.")
    
    print("\n===== LLM Tool Calling Complete =====")
    return True

# Make call_function available at module level for audio-based operation
def call_function(name, args):
    print(f"Executing function: {name} with args: {args}")
    try:
        # Import tools module dynamically to avoid circular imports
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        import tools
        
        # Check if the function exists in the tools module
        if hasattr(tools, name):
            function = getattr(tools, name)
            return function(**args)
        else:
            error_msg = f"Function {name} not found in tools module"
            logger.error(error_msg)
            return {"error": error_msg}
    except Exception as e:
        error_msg = f"Error executing {name}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"error": error_msg}

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
        elif sys.argv[1] == "run_bot":
            # Run the robot with LLM tool calling
            if run_bot():
                print("Robot run successfully completed.")
            else:
                print("Robot run encountered errors.")
            sys.exit(0)
        elif sys.argv[1] == "voice_control":
            # Run the robot with voice control
            if run_bot_voice_control():
                print("Voice control session ended successfully.")
            else:
                print("Voice control encountered errors.")
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
