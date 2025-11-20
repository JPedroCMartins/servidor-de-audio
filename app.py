from flask import Flask, request
import pyaudio
import queue
import threading
import time
import numpy as np
app = Flask(__name__)

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 4096 
BYTES_PER_SAMPLE = 2 

VOLUME_FACTOR = 2.0 

TARGET_DELAY_SECONDS = 2
BYTES_PER_SECOND = RATE * BYTES_PER_SAMPLE * CHANNELS
BUFFER_SIZE_BYTES = BYTES_PER_SECOND * TARGET_DELAY_SECONDS
TARGET_CHUNKS = BUFFER_SIZE_BYTES / CHUNK

audio_queue = queue.Queue()

def playback_worker():
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True)
    print("Player: Aguardando buffer encher...")
    buffering = True
    while True:
        if buffering:
            if audio_queue.qsize() >= TARGET_CHUNKS:
                print("Player: Buffer carregado! Tocando...")
                buffering = False
            else:
                time.sleep(0.1)
                continue
        try:
            data = audio_queue.get(timeout=1)
            if data is None: break
            stream.write(data)
        except queue.Empty:
            buffering = True
    stream.stop_stream()
    stream.close()
    p.terminate()

@app.route('/stream', methods=['POST'])
def stream_audio():
    player_thread = threading.Thread(target=playback_worker, daemon=True)
    player_thread.start()

    print(f"Servidor: Recebendo e amplificando volume em {VOLUME_FACTOR}x ...")
    
    try:
        while True:
            data = request.stream.read(CHUNK)
            if not data:
                break

            audio_signal = np.frombuffer(data, dtype=np.int16)

            audio_signal = audio_signal * VOLUME_FACTOR
            

            audio_signal = np.clip(audio_signal, -32768, 32767)

            data_amplified = audio_signal.astype(np.int16).tobytes()

            audio_queue.put(data_amplified)
            
    except Exception as e:
        print(f"Erro: {e}")
    
    audio_queue.put(None)
    return "Fim", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True, use_reloader=False)