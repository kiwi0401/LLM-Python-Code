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

# Configuration
load_dotenv("./.env")
WAKE_WORD = "hello robot"  # wake word to listen for (in lower-case for matching)
SAMPLE_RATE = 16000  # audio sample rate for Vosk model (Hz)
CHUNK = 4096  # number of audio frames per buffer read
MODEL_PATH = "./vosk-model-en-us-0.22"  # path to Vosk model directory (change if needed)

# Load Vosk model (ensure you have downloaded a Vosk model to the specified path)
model = Model(MODEL_PATH)
recognizer = KaldiRecognizer(model, SAMPLE_RATE)

# Initialize text-to-speech engine (pyttsx3)
tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 180)  # adjust speech rate if desired
tts_engine.setProperty('volume', 1.0)  # volume: 0.0 to 1.0

# Set up OpenAI API (ensure API key is set as environment variable for security)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Prepare audio input (PyAudio) and find ReSpeaker device if available
p = pyaudio.PyAudio()
device_index = None
# Optional: search for ReSpeaker device by name to select it
for i in range(p.get_device_count()):
    dev = p.get_device_info_by_index(i)
    name = dev.get('name', '').lower()
    if "respeaker" in name and dev.get('maxInputChannels', 0) > 0:
        device_index = i
        break

# Open PyAudio input stream (try mono first, if not supported, fall back to multi-channel)
format = pyaudio.paInt16  # 16-bit int sampling
channels = 1
try:
    stream = p.open(format=format, channels=channels, rate=SAMPLE_RATE,
                    input=True, frames_per_buffer=CHUNK, input_device_index=device_index)
    multi_channel = False
except Exception as e:
    # If device requires multi-channel (e.g., ReSpeaker array), open with 4 channels and downmix later
    channels = 4
    stream = p.open(format=format, channels=channels, rate=SAMPLE_RATE,
                    input=True, frames_per_buffer=CHUNK, input_device_index=device_index)
    multi_channel = True
    print("Opened multi-channel audio stream; will use first channel for recognition.")

# Queue for audio frames and an event to signal when to stop or reset listening
audio_queue = queue.Queue()
stop_event = threading.Event()


def audio_callback(in_data, frame_count, time_info, status):
    """PyAudio callback for continuously reading microphone data."""
    # If there's a status message (e.g., an error), print it
    # (PyAudio documentation: status is non-zero if input overflow etc.)
    # For simplicity, ignore status in this implementation.
    if multi_channel:
        # Downmix to single channel (pick first channel)
        audio_data = np.frombuffer(in_data, dtype=np.int16)
        mono_data = audio_data[0::channels]  # take every Nth sample corresponding to channel 0
        in_data = mono_data.tobytes()
    # If stop_event is set (e.g., to flush old data), skip adding frames
    if stop_event.is_set():
        return (None, pyaudio.paContinue)
    # Otherwise, put audio data into the queue for processing
    audio_queue.put(in_data)
    return (None, pyaudio.paContinue)


# Start the audio stream in callback mode for non-blocking continuous capture
stream.stop_stream()
stream.close()
# Re-open stream with callback (PyAudio requires closing first to change to callback mode)
stream = p.open(format=format, channels=channels, rate=SAMPLE_RATE,
                input=True, frames_per_buffer=CHUNK, input_device_index=device_index,
                stream_callback=audio_callback)
stream.start_stream()

print("Voice assistant is now listening for the wake phrase...")

try:
    while True:
        # 1. Remain idle until wake word is detected
        text = ""  # buffer for recognized text
        # Continue retrieving audio from the queue and feeding to Vosk
        while True:
            data = audio_queue.get()  # get next chunk of audio (blocking if necessary)
            if recognizer.AcceptWaveform(data):
                # Final speech result for this segment (silence or phrase end reached)
                result = recognizer.Result()  # result in JSON format
                result_text = eval(result).get("text", "")  # convert JSON string to dict and get text
                text += (" " + result_text).strip()
                # Check if wake word is in the final text segment
                if WAKE_WORD in text.lower():
                    break
                # Reset text buffer and continue listening if wake word not in this final result
                text = ""
            else:
                # Partial result (speech still ongoing) – check for wake word in partial text
                partial_result = recognizer.PartialResult()
                partial_text = eval(partial_result).get("partial", "").lower()
                if WAKE_WORD in partial_text:
                    # Detected wake word in partial transcript (low-latency wake-up)&#8203;:contentReference[oaicite:0]{index=0}
                    text = WAKE_WORD
                    # Break out, but first flush recognizer to prevent mixing with command
                    recognizer.Reset()
                    break
            # Continue loop until wake word found

        # If we reach here, wake word was detected
        print("Wake word detected. Awaiting command...")
        # 2. Reply verbally with "Waiting for command"
        tts_engine.say("Waiting for command")
        tts_engine.runAndWait()

        # 3. Listen for the next spoken command (up to 10 seconds or until 1 second of silence)
        recognizer.Reset()  # reset recognizer to start fresh for the command
        command_text = ""
        silence_duration = 0  # track silence
        max_command_time = 10.0  # seconds
        start_time = time.time()
        while time.time() - start_time < max_command_time:
            try:
                data = audio_queue.get(timeout=0.5)  # wait for up to 0.5s for audio
            except queue.Empty:
                # No audio chunk available (could be silence)
                silence_duration += 0.5
                if silence_duration >= 1.0:  # 1 second of no audio
                    break  # assume end of command
                else:
                    continue
            # If we got audio data, reset silence counter
            silence_duration = 0
            if recognizer.AcceptWaveform(data):
                # Got a final chunk of speech for the command
                result = recognizer.Result()
                result_text = eval(result).get("text", "")
                command_text += (" " + result_text).strip()
                # If we consider only one command, break after first final result
                break
            else:
                # Still processing speech (partial results)
                partial_result = recognizer.PartialResult()
                partial_text = eval(partial_result).get("partial", "")
                # We can accumulate partial text or just wait for final.
                # (We'll ultimately use final result for accuracy)
                # Optionally, implement voice activity detection if needed.
        # End of command listening loop

        command_text = command_text.strip()
        if not command_text:
            # If no command was captured (maybe silence or timeout)
            print("No command heard within the time limit. Returning to wake word listening.")
            # Go back to listening for wake word
            continue

        print(f"Transcribed command: '{command_text}'")
        # 4. Transcribe the command using Vosk (already done above in command_text)
        # 5. Send the transcribed command to OpenAI API and get a response
        try:
            # Use OpenAI ChatCompletion for the latest models (e.g., gpt-3.5-turbo or GPT-4)&#8203;:contentReference[oaicite:1]{index=1}
            response = client.chat.completions.create(
                model="gpt-4o",  # or "gpt-4" if available
                messages=[{"role": "System", "content": open("dog_response.md", "r", encoding="utf-8").read()}, {"role": "user", "content": command_text}],
            )
            assistant_reply = response.choices[0].message.content
        except Exception as e:
            assistant_reply = "I'm sorry, I couldn't process that request."
            print(f"Error calling OpenAI API: {e}")

        # 6. Use pyttsx3 to vocalize the assistant's response
        print(f"Assistant response: {assistant_reply}")
        tts_engine.say(assistant_reply)
        tts_engine.runAndWait()

        # 7. After responding, continue the loop (return to waiting for wake word)
        print("Listening for the wake phrase again...")
        # Flush any lingering audio in queue to avoid false triggers or carrying over speech
        while not audio_queue.empty():
            try:
                audio_queue.get_nowait()
            except queue.Empty:
                break
        recognizer.Reset()
        text = ""
        # Loop continues to wait for next wake word...

except KeyboardInterrupt:
    # Handle clean exit on Ctrl+C
    print("Exiting voice assistant.")
finally:
    # Cleanup: stop audio stream and release resources
    stream.stop_stream()
    stream.close()
    p.terminate()
    tts_engine.stop()
