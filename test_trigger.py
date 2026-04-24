import time
import requests
import subprocess
import numpy as np
import torch
import pvporcupine
from pvrecorder import PvRecorder
from faster_whisper import WhisperModel
from piper.voice import PiperVoice
import random
import json
import threading
import mysql.connector
from flask import Flask, request, jsonify
import json

app = Flask(__name__)

@app.route('/api/speak', methods=['POST'])
def api_speak():
    data = request.json
    if not data or 'text' not in data:
        return jsonify({"error": "No text provided"}), 400
    
    text = data['text']
    speech_thread = threading.Thread(target=speak_text, args=(text,), daemon=True)
    speech_thread.start()
    return jsonify({"status": "success", "message": "Speaking triggered"}), 200

@app.route('/api/ask', methods=['GET'])
def api_ask():
    print("Listening for Response")
    update_dashboard("status", "Listening for Response...")
    audio_data = listen_for_response()

    user_text = transcribe_audio(audio_data)
    if user_text:
        print("You:", user_text)
        update_dashboard("status", "Processing...")
        update_dashboard("message", f"You: {user_text}")
        return jsonify({"status": "success", "message": user_text}), 200
    else:
        update_dashboard("status", "System Online")
        update_dashboard("message", "Jarvis System Online")
        return jsonify({"status": "error", "message": "No text provided"}), 400

def run_flask_app():
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    try:
        subprocess.run("sudo kill -9 $(sudo lsof -t -i:5002)", shell=True)
    except:
        pass
    app.run(host='0.0.0.0', port=5002, debug=False, use_reloader=False)

def update_dashboard(action, text):
    try:
        if action == "status":
            requests.post("http://127.0.0.1:5001/api/trigger", json={"action": "status", "message": text}, timeout=0.2)
        elif action == "message":
            requests.post("http://127.0.0.1:5001/api/trigger", json={"action": "message", "text": text}, timeout=0.2)
    except:
        pass 

update_dashboard("status", "Initializing...")
update_dashboard("message", "Jarvis Starting...")
current_audio_player = None
is_speaking = False
ACCESS_KEY = "hg3jNulOTAcUVN8HYmAqDaQ1dKPL+9502MWlu06uypE58CnyHFb/0g=="
WAKE_WORD_PATH = "resources/Jarvis_en_raspberry-pi_v4_0_0.ppn"
N8N_WEBHOOK_URL = "http://100.104.205.24:5678/webhook/thought_dump"
PIPER_MODEL = "resources/en_US-amy-medium.onnx"

MIC_POSITION = 1
previous_reply = ""
public_key = ""

print("Initializing CogniJarvis (Full Voice Mode)...")

porcupine = pvporcupine.create(
    access_key=ACCESS_KEY,
    keyword_paths=[WAKE_WORD_PATH]
) 

recorder = PvRecorder(
    frame_length=porcupine.frame_length,
    device_index=MIC_POSITION
) 

vad_model, _ = torch.hub.load(
    repo_or_dir='snakers4/silero-vad',
    model='silero_vad'
) 

voice = PiperVoice.load(PIPER_MODEL)

stt_model = WhisperModel(
    "tiny.en",
    device="cpu",
    compute_type="int8"
) 

def stop_current_speech():
    global current_audio_player
    
    if current_audio_player is not None:
        try:
            current_audio_player.terminate()
        except OSError:
            pass 
        current_audio_player = None

def speak_text(text):
    global current_audio_player, is_speaking
    is_speaking = True
    
    play_cmd = ["pw-play", "--raw", "--format=s16", "--rate=22050", "--channels=1", "-"]

    
    proc = subprocess.Popen(play_cmd, stdin=subprocess.PIPE)
    current_audio_player = proc 
    update_dashboard("status", "Speaking...")
    update_dashboard("message", text)
    try:
        for audio_chunk in voice.synthesize(text, include_alignments=True):
            
            if proc.poll() is not None:
                update_dashboard("status", "System Online")
                update_dashboard("message", "Jarvis System Online")
                return 
            proc.stdin.write(audio_chunk.audio_int16_bytes)
        update_dashboard("status", "System Online")
        update_dashboard("message", "Jarvis System Online")
        proc.stdin.flush()
    except:
        print("No text recieved")
        pass 
    finally:
        
        if proc.stdin:
            proc.stdin.close()

        proc.wait()
        
        if current_audio_player == proc:
            current_audio_player = None
        is_speaking = False

def listen_for_command():
    
    AMBIENT_TV_LEVEL = 0.02  
    TALKING_LEVEL = 0.06    
    
    command_audio = []
    silent_frames = 0
    has_spoken = False
    total_frames = 0

    while True:
        frame = recorder.read()
        total_frames += 1
        audio_np = np.array(frame, dtype=np.float32) / 32768.0
        rms = np.sqrt(np.mean(audio_np**2))

        
        tensor_input = torch.from_numpy(audio_np)
        with torch.no_grad():
            speech_prob = vad_model(tensor_input, 16000).item()

        if not has_spoken:
            if speech_prob > 0.85 and rms > (AMBIENT_TV_LEVEL + 0.02):
                has_spoken = True
                print("User detected over background noise.")   
        if has_spoken:
            command_audio.extend(frame)
            
            if speech_prob < 0.4 or rms < AMBIENT_TV_LEVEL:
                silent_frames += 1
            else:
                silent_frames = 0
        else:
            pass 

        if has_spoken and silent_frames > 50:
            break
        elif not has_spoken and total_frames > 500: 
            return np.array([], dtype=np.float32)

    return np.array(command_audio, dtype=np.float32) / 32768.0
    
def listen_for_response():
    print("Listening...")
    command_audio = []
    silent_frames = 0
    has_spoken = False  

    while True:
        frame = recorder.read()
        command_audio.extend(frame)

        tensor_input = torch.from_numpy(
            np.array(frame, dtype=np.float32) / 32768.0
        )

        with torch.no_grad():
            speech_prob = vad_model(tensor_input, 16000).item()

        if speech_prob > 0.6: 
            has_spoken = True
            silent_frames = 0
        else:
            silent_frames += 1
                
        if has_spoken and silent_frames > 45:
            break
        elif not has_spoken and silent_frames > 150:
            update_dashboard("status", "System Online")
            update_dashboard("message", "Jarvis System Online")
            print("Well I tried")
            return np.array([], dtype=np.float32)

    return np.array(command_audio, dtype=np.float32) / 32768.0

def transcribe_audio(audio_data):
    
    if len(audio_data) == 0:
        return ""
    
    start = time.perf_counter()
    segments, _ = stt_model.transcribe(audio_data, beam_size=1, best_of=1, temperature=0)
    end = time.perf_counter()
    print(f"Spoken: \nStart Time: {start} \nEnd Time: {end} \nDifference: {end-start}")
    return " ".join([segment.text for segment in segments]).strip()


def send_to_n8n(user_text, key = ""):
    if key != "":
        payload = {
            "content": user_text,
            "sessionId": key,
            "phone": False
        }
    else:
        payload = {
            "content": user_text,
            "phone":False
        }
    update_dashboard("status", "Thinking...")
    update_dashboard("message", user_text)

    try:
        
        with requests.post(N8N_WEBHOOK_URL, json=payload, stream=True) as r:
            for chunk in r.iter_content(chunk_size=None):
                if "404" not in str(chunk):
                    
                    print(chunk.decode('utf-8'), end="", flush=True)
                    return chunk.decode('utf-8')
    except Exception as e:
        print("Network error:", e)
        return "I cannot reach the workflow server."

def get_welcome_message():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="remote_user",
            password="pi",
            database="Schedule"
        )
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT student_name FROM system_config LIMIT 1")
        row = cursor.fetchone()
        db.close()
        name = row['student_name'] if row and 'student_name' in row else "Sir"
        name = name.split(" ")[0]
    except Exception as e:
        print(f"DB Error fetching name: {e}")
        name = "Sir"
    
    hour = time.localtime().tm_hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 18:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"
        
    try:
        response = requests.get("http://100.104.205.24:5678/webhook/quote-of-the-day", timeout=5)
        response.raise_for_status()
        data = response.json()
        quote = data['output']
    except Exception as e:
        print(f"Failed to fetch quote from webhook: {e}")
        quote = "Let's make today a great day."
    
    return f"{greeting} {name}, {quote}"

def main():
    
    api_thread = threading.Thread(target=run_flask_app, daemon=True)
    api_thread.start()
    
    global previous_reply, public_key
    recorder.start()
    
    welcome_msg = get_welcome_message()
    speech_thread = threading.Thread(target=speak_text, args=(welcome_msg,), daemon=True)
    speech_thread.start()
    
    print("CogniJarvis Online. Say your wake word...")
    update_dashboard("status", "System Online")
    update_dashboard("message", "Jarvis System Online")
    try:
        while True:
                if is_speaking:
                    time.sleep(0.1)
                    continue

                if previous_reply is None:
                    previous_reply = ""
                if "[REQUEST]" not in previous_reply:
                    pcm = recorder.read()
                    if porcupine.process(pcm) >= 0:
                        print("\nWake word detected.") 
                        update_dashboard("status", "Listening...")
                        update_dashboard("message", "Ready for your command")
                        stop_current_speech()
                        
                        audio_data = listen_for_command()
                        
                        user_text = transcribe_audio(audio_data)

                        if user_text:
                            print("You:", user_text)
                            update_dashboard("status", "Processing...")
                            update_dashboard("message", f"You: {user_text}")
                            if "[REQUEST]" in previous_reply:
                                user_text = user_text + "[RESPONSE]"
                                previous_reply = previous_reply.replace("[REQUEST]", "")

                            key = public_key
                            print("sending to n8n")
                            reply = send_to_n8n(user_text, key)
                            print(reply)
                            try:
                                json_reply = json.loads(reply)
                                previous_reply = json_reply["output"]
                                print(previous_reply)
                                public_key = json_reply["sessionId"]
                                speech_thread = threading.Thread(target=speak_text, args=(previous_reply,), daemon=True)
                                speech_thread.start()
                            except:
                                previous_reply = reply
                                print("Prolly where the issue is")
                                public_key = ""
                                speech_thread = threading.Thread(target=speak_text, args=(previous_reply,), daemon=True)
                                speech_thread.start()
                        else:
                            update_dashboard("status", "System Online")
                            update_dashboard("message", "Jarvis System Online")
                else:
                    print("Listening for Response")
                    update_dashboard("status", "Listening for Response...")
                    audio_data = listen_for_response()

                    user_text = transcribe_audio(audio_data)
                        
                    if user_text:
                            print("You:", user_text)
                            update_dashboard("status", "Processing...")
                            update_dashboard("message", f"You: {user_text}")
                            if "[REQUEST]" in previous_reply:
                                user_text = user_text + "[RESPONSE]"
                                previous_reply = previous_reply.replace("[REQUEST]", "")

                            key = public_key
                            reply = send_to_n8n(user_text, key)
                            print("Prolly where the issue is")
                            try:
                                json_reply = json.loads(reply)
                                print("output1")
                                previous_reply = json_reply["output"]
                                print(previous_reply)
                                public_key = json_reply["sessionId"]
                                speech_thread = threading.Thread(target=speak_text, args=(previous_reply,), daemon=True)
                                speech_thread.start()
                            except:
                                print("output2")
                                previous_reply = reply
                                public_key = ""
                                speech_thread = threading.Thread(target=speak_text, args=(previous_reply,), daemon=True)
                                speech_thread.start()
                    else:
                        previous_reply = ""
                        update_dashboard("status", "System Online")
                        update_dashboard("message", "Jarvis System Online")

    except KeyboardInterrupt:
        update_dashboard("status", "Jarvis Offline")
        update_dashboard("message", "Please Restart the system")
        print("\nShutting down...")


    finally:
        recorder.stop()
        recorder.delete()
        porcupine.delete()
if __name__ == "__main__":
    main()
    

