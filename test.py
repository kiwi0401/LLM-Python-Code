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
SAMPLE_RATE = 16000  # audio sample rate (Hz)
CHUNK = 4096  # number of audio frames per buffer read
MODEL_PATH = "./vosk-model-en-us-0.22"  # path to Vosk model directory


def init_openai_client():
    load_dotenv("./.env")
    api_key = os.getenv("OPENAI_API_KEY")
    return OpenAI(api_key=api_key)


def init_vosk_recognizer():
    model = Model(MODEL_PATH)
    recognizer = KaldiRecognizer(model, SAMPLE_RATE)
    return recognizer


def init_tts_engine():
    engine = pyttsx3.init()
    engine.setProperty('rate', 180)  # adjust speech rate if desired
    engine.setProperty('volume', 1.0)  # volume: 0.0 to 1.0
    return engine


def init_audio_stream():
    p = pyaudio.PyAudio()
    device_index = None

    # Search for a ReSpeaker device if available.
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        if "respeaker" in dev.get('name', '').lower() and dev.get('maxInputChannels', 0) > 0:
            device_index = i
            break

    format = pyaudio.paInt16  # 16-bit int sampling
    channels = 1
    multi_channel = False
    try:
        stream = p.open(format=format, channels=channels, rate=SAMPLE_RATE,
                        input=True, frames_per_buffer=CHUNK, input_device_index=device_index)
    except Exception as e:
        # If device requires multi-channel (e.g., ReSpeaker array)
        channels = 4
        stream = p.open(format=format, channels=channels, rate=SAMPLE_RATE,
                        input=True, frames_per_buffer=CHUNK, input_device_index=device_index)
        multi_channel = True
        print("Opened multi-channel audio stream; will use first channel for recognition.")
    return p, stream, device_index, channels, multi_channel


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


def listen_for_command(recognizer, audio_queue, tts_engine):
    """After wake word detection, capture the spoken command."""
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


conversation_history = []
def process_command(command_text, openai_client, prompt_path="dog_response.md", memory_limit=10):
    """Send the command to the OpenAI API and retrieve the response using conversation history.

    Parameters:
        command_text (str): The user's command text.
        openai_client: An initialized OpenAI client.
        prompt_path (str): File path to the system prompt.
        memory_limit (int): Maximum number of messages to retain (including system prompt).

    Returns:
        tuple: (assistant_reply, updated conversation_history)
    """
    try:
        # Initialize conversation history with system prompt if empty.
        if not conversation_history:
            with open(prompt_path, "r", encoding="utf-8") as f:
                system_prompt = f.read()
            conversation_history.append({"role": "system", "content": system_prompt})

        # Append the new user message.
        conversation_history.append({"role": "user", "content": command_text})

        # Call the OpenAI API using the full conversation history.
        response = openai_client.chat.completions.create(
            model="gpt-4o",  # or "gpt-4" if available
            messages=conversation_history,
        )
        assistant_reply = response.choices[0].message.content

        # Append the assistant's reply to the conversation history.
        conversation_history.append({"role": "assistant", "content": assistant_reply})

        # Limit conversation history to the last 'memory_limit' messages.
        # Always keep the initial system prompt at index 0.
        if len(conversation_history) > memory_limit:
            # Preserve system prompt and the last (memory_limit - 1) messages.
            conversation_history[:] = [conversation_history[0]] + conversation_history[-(memory_limit - 1):]

        return prompt_path, assistant_reply
    except Exception as e:
        print(f"Error processing command: {e}")
        return "I'm sorry, I couldn't process that request."


import threading
from concurrent.futures import ThreadPoolExecutor
def process_command_threaded(command_text, openai_client, prompt_paths, memory_limit=10):
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


def main():
    # Initialize components
    openai_client = init_openai_client()
    recognizer = init_vosk_recognizer()
    tts_engine = init_tts_engine()
    p, stream, device_index, channels, multi_channel = init_audio_stream()

    # Prepare audio queue and control event
    audio_queue = queue.Queue()
    stop_event = threading.Event()  # Using a queue.Event() instead of threading.Event() for clarity

    # Stop the initial blocking stream to re-open in callback mode
    stream.stop_stream()
    stream.close()

    # Create the callback using partial to include extra parameters
    callback = partial(audio_callback,
                       multi_channel=multi_channel,
                       channels=channels,
                       stop_event=stop_event,
                       audio_queue=audio_queue)

    stream = p.open(format=pyaudio.paInt16,
                    channels=channels,
                    rate=SAMPLE_RATE,
                    input=True,
                    frames_per_buffer=CHUNK,
                    input_device_index=device_index,
                    stream_callback=callback)
    stream.start_stream()

    print("Voice assistant is now listening for the wake phrase...")

    try:
        while True:
            # 1. Wait for the wake word.
            wait_for_wake_word(recognizer, audio_queue)
            print("Wake word detected. Awaiting command...")

            # 2. Listen for and transcribe the command.
            command_text = listen_for_command(recognizer, audio_queue, tts_engine)
            if not command_text:
                print("No command heard within the time limit. Returning to wake word listening.")
                continue
            print(f"Transcribed command: '{command_text}'")

            # 3. Process the command via OpenAI.
            assistant_reply = process_command_threaded(command_text, openai_client, ["dog_response.md", "dog_actions.md"])
            print(f"Assistant response: {assistant_reply}")

            for prompt_path, reply in assistant_reply:
                if prompt_path != "dog_response.md":
                    continue
                tts_engine.say(reply)
                tts_engine.runAndWait()

            print("Listening for the wake phrase again...")
            flush_audio_queue(audio_queue)
            recognizer.Reset()
    except KeyboardInterrupt:
        print("Exiting voice assistant.")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
        tts_engine.stop()


if __name__ == '__main__':
    main()
