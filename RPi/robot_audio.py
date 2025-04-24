#!/usr/bin/env/python3
# File name   : robot_audio.py
# Description : Audio processing tools for voice commands

import os
import queue
import threading
import time
import numpy as np
import pyaudio
import pyttsx3
from openai import OpenAI
from vosk import Model, KaldiRecognizer
from dotenv import load_dotenv
from functools import partial

# Global Configuration
WAKE_WORD = "hello robot"  # wake word (in lower-case for matching)
SAMPLE_RATE = 16000         # audio sample rate
CHUNK = 4096
MODEL_PATH = "./vosk-model-small-en-us-0.15"  # path to Vosk model directory
PROMPT_PATHS = ["dog_response.md", "dog_actions.md"]

def init_openai_client():
    """Initialize the OpenAI client using API key from environment variables"""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    return OpenAI(api_key=api_key)

def init_vosk_recognizer():
    """Initialize the Vosk speech recognition model"""
    model = Model(MODEL_PATH)
    recognizer = KaldiRecognizer(model, SAMPLE_RATE)
    return recognizer

def init_tts_engine():
    """Initialize text-to-speech engine"""
    engine = pyttsx3.init()
    engine.setProperty('rate', 180)  # adjust speech rate
    engine.setProperty('volume', 1.0)  # volume: 0.0 to 1.0
    return engine

def init_audio_stream():
    """Initialize audio input stream, preferring ReSpeaker if available"""
    p = pyaudio.PyAudio()
    
    # Find the ReSpeaker device
    device_index = None
    channels = 1
    multi_channel = False
    
    # List all available audio devices and find the ReSpeaker
    for i in range(p.get_device_count()):
        dev_info = p.get_device_info_by_index(i)
        name = dev_info.get('name', '').lower()
        if 'respeaker' in name and dev_info.get('maxInputChannels') > 0:
            device_index = i
            channels = min(dev_info.get('maxInputChannels'), 4)  # ReSpeaker has 4 channels
            multi_channel = channels > 1
            print(f"Selected ReSpeaker device: {name} (index: {device_index}, channels: {channels})")
            break
    
    # If no ReSpeaker found, use default input device
    if device_index is None:
        device_index = p.get_default_input_device_info().get('index', 0)
        print(f"Using default input device (index: {device_index})")
    
    try:
        stream = p.open(format=pyaudio.paInt16,
                        channels=channels,
                        rate=SAMPLE_RATE,
                        input=True,
                        frames_per_buffer=CHUNK,
                        input_device_index=device_index)
        
        recognizer = KaldiRecognizer(Model(MODEL_PATH), SAMPLE_RATE)
        return p, stream, device_index, channels, multi_channel, recognizer
    except OSError as e:
        print(f"Error opening audio stream: {e}")
        print("Trying default audio device...")
        try:
            device_index = p.get_default_input_device_info().get('index', 0)
            channels = 1
            multi_channel = False
            stream = p.open(format=pyaudio.paInt16,
                            channels=channels,
                            rate=SAMPLE_RATE,
                            input=True,
                            frames_per_buffer=CHUNK,
                            input_device_index=device_index)
            recognizer = KaldiRecognizer(Model(MODEL_PATH), SAMPLE_RATE)
            return p, stream, device_index, channels, multi_channel, recognizer
        except OSError as e:
            print(f"Failed to open audio stream with default device: {e}")
            raise

def audio_callback(in_data, frame_count, time_info, status, multi_channel, channels, stop_event, audio_queue):
    """Callback function for continuous audio capture."""
    if multi_channel:
        # Downmix to single channel (use first channel)
        audio_data = np.frombuffer(in_data, dtype=np.int16)
        mono_data = audio_data[0::channels]
        in_data = mono_data.tobytes()
    if stop_event.is_set():
        return (None, pyaudio.paContinue)
    audio_queue.put(in_data)
    return (None, pyaudio.paContinue)

def wait_for_wake_word(recognizer, audio_queue):
    """Listen until the wake word is detected."""
    print("Listening for wake word...")
    text = ""
    while True:
        data = audio_queue.get()  # Blocking call
        if recognizer.AcceptWaveform(data):
            result = recognizer.Result()  # JSON string
            result_text = eval(result).get("text", "")
            text += (" " + result_text).strip()
            if WAKE_WORD in text.lower():
                break
            text = ""
        else:
            partial_result = recognizer.PartialResult()
            partial_text = eval(partial_result).get("partial", "").lower()
            if WAKE_WORD in partial_text:
                # Low latency wake-up
                text = WAKE_WORD
                recognizer.Reset()
                break
    return True

def listen_for_command(recognizer, audio_queue, tts_engine=None):
    """After wake word detection, capture the spoken command."""
    if tts_engine:
        tts_engine.say("Waiting for command")
        tts_engine.runAndWait()
    recognizer.Reset()  # Start fresh for command capture
    command_text = ""
    silence_duration = 0
    max_command_time = 10.0  # seconds
    start_time = time.time()

    while time.time() - start_time < max_command_time:
        try:
            data = audio_queue.get(timeout=0.5)
        except queue.Empty:
            silence_duration += 0.5
            if silence_duration >= 1.0:  # 1 second of silence
                break
            continue

        silence_duration = 0  # reset silence timer

        if recognizer.AcceptWaveform(data):
            result = recognizer.Result()
            result_text = eval(result).get("text", "")
            command_text += (" " + result_text).strip()
            # Assuming one final result is enough
            break
        else:
            # Optionally process partial results if needed
            _ = eval(recognizer.PartialResult()).get("partial", "")
    return command_text.strip()

# Global conversation history
conversation_history = []

def process_command(command_text, openai_client, prompt_path="dog_response.md", memory_limit=10):
    """Process a command with OpenAI API using conversation history."""
    global conversation_history
    
    try:
        # Initialize conversation history with system prompt if empty
        if not conversation_history:
            with open(prompt_path, "r", encoding="utf-8") as f:
                system_prompt = f.read()
            conversation_history.append({"role": "system", "content": system_prompt})

        # Append the new user message
        conversation_history.append({"role": "user", "content": command_text})

        # Call the OpenAI API using the full conversation history
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=conversation_history,
        )
        assistant_reply = response.choices[0].message.content

        # Append the assistant's reply to the conversation history
        conversation_history.append({"role": "assistant", "content": assistant_reply})

        # Limit conversation history to the last 'memory_limit' messages
        if len(conversation_history) > memory_limit:
            # Preserve system prompt and the last (memory_limit - 1) messages
            conversation_history[:] = [conversation_history[0]] + conversation_history[-(memory_limit - 1):]

        return prompt_path, assistant_reply
    except Exception as e:
        print(f"Error processing command: {e}")
        return prompt_path, "I'm sorry, I couldn't process that request."

def process_command_threaded(command_text, openai_client, prompt_paths=None, memory_limit=10):
    """Process a command using multiple prompt templates in parallel."""
    if prompt_paths is None:
        prompt_paths = PROMPT_PATHS
        
    from concurrent.futures import ThreadPoolExecutor
    
    def process_single_prompt(prompt_path):
        if prompt_path == "dog_response.md":
            return process_command(command_text, openai_client, prompt_path, memory_limit)

        local_conversation_history = []
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                system_prompt = f.read()
            local_conversation_history.append({"role": "system", "content": system_prompt})
            local_conversation_history.append({"role": "user", "content": command_text})

            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=local_conversation_history,
            )
            assistant_reply = response.choices[0].message.content

            return prompt_path, assistant_reply

        except Exception as e:
            print(f"Error with prompt {prompt_path}: {e}")
            return prompt_path, "Error occurred"

    # Run each prompt processing in parallel
    with ThreadPoolExecutor(max_workers=min(3, len(prompt_paths))) as executor:
        results = list(executor.map(process_single_prompt, prompt_paths))

    return results

def flush_audio_queue(audio_queue):
    """Flush any lingering audio in the queue."""
    while not audio_queue.empty():
        try:
            audio_queue.get_nowait()
        except queue.Empty:
            break

def cleanup_audio(stream, p, tts_engine=None):
    """Clean up audio resources."""
    if stream:
        stream.stop_stream()
        stream.close()
    if p:
        p.terminate()
    if tts_engine:
        tts_engine.stop()

def setup_audio_processing():
    """Setup all audio components and return them as a dictionary."""
    try:
        # Initialize components
        openai_client = init_openai_client()
        tts_engine = init_tts_engine()
        p, stream, device_index, channels, multi_channel, recognizer = init_audio_stream()
        
        # Prepare audio queue and control event
        audio_queue = queue.Queue()
        stop_event = threading.Event()
        
        # Stop the initial blocking stream to re-open in callback mode
        stream.stop_stream()
        stream.close()
        
        # Create the callback using partial to include extra parameters
        callback = partial(audio_callback,
                          multi_channel=multi_channel,
                          channels=channels,
                          stop_event=stop_event,
                          audio_queue=audio_queue)
        
        # Reopen the stream in callback mode
        stream = p.open(format=pyaudio.paInt16,
                        channels=channels,
                        rate=SAMPLE_RATE,
                        input=True,
                        frames_per_buffer=CHUNK,
                        input_device_index=device_index,
                        stream_callback=callback)
        
        print("Audio processing initialized successfully")
        
        return {
            "openai_client": openai_client,
            "tts_engine": tts_engine,
            "pyaudio": p,
            "stream": stream,
            "recognizer": recognizer,
            "audio_queue": audio_queue,
            "stop_event": stop_event
        }
    
    except Exception as e:
        print(f"Failed to initialize audio processing: {e}")
        return None

if __name__ == '__main__':
    print("This module is not meant to be run directly.")
    print("Import it and call setup_audio_processing() to use its functionality.")
