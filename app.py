import json
from flask import Flask, request, jsonify, render_template, Response
import requests
import base64
import os
from pydub import AudioSegment
import io
import grpc
import riva.client
import numpy as np
from scipy.io.wavfile import write

auth = riva.client.Auth(uri='localhost:50051')
riva_asr = riva.client.ASRService(auth)
tts_service = riva.client.SpeechSynthesisService(auth)

language_code = "en-US"  # Replace with your desired language code
sample_rate_hz = 44100  # Replace with your desired sample rate
voice_name = "English-US.Female-1"  # Replace with the desired voice name
data_type = np.int16 # For RIVA version < 1.10.0, set this to np.float32

app = Flask(__name__)

def asr(audio_path):
    # Read audio file
    with io.open(audio_path, 'rb') as fh:
        content = fh.read()

    # Set up ASR configuration
    config = riva.client.RecognitionConfig()
    config.language_code = "en-US"
    config.max_alternatives = 1
    config.enable_automatic_punctuation = True
    config.audio_channel_count = 1

    # Perform ASR using Riva ASR
    response = riva_asr.offline_recognize(content, config)
    asr_best_transcript = response.results[0].alternatives[0].transcript
    
    return asr_best_transcript

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/describe', methods=['POST'])
def describe():
    encoded_string = request.json['image']
    if 'audioTranscription' in request.json:
        audio_transcription = request.json['audioTranscription']
    else:
        audio_transcription = "Describe the image"
    print(audio_transcription)
    image_data = [{"data": encoded_string, "id": 12}]
    data = {
        "prompt": f"USER:[img-12]{audio_transcription}\nASSISTANT:", 
        
        "n_predict": 128, 
        "image_data": image_data, 
        "stream": True
    }
    headers = {"Content-Type": "application/json"}
    url = "http://localhost:8080/completion"
    
    response = requests.post(url, headers=headers, json=data, stream=True)
    
    def generate():
        for chunk in response.iter_content(chunk_size=1024):
            if chunk: 
                try:
                    chunk_json = json.loads(chunk.decode().split("data: ")[1])
                    content = chunk_json.get("content", "")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue  

    return Response(generate(), content_type='text/plain')


@app.route('/stopRecording',methods=["GET", "POST"])
def stopRecording():
    if request.files:
        audio_data = request.files.get('audio')
        if audio_data:
            transcript = process_audio(audio_data)
            return jsonify({'transcript': transcript})
    return jsonify({'error': 'Invalid request'})

def process_audio(audio_data):
    # Process the audio data and save it as a WAV file
    save_path = os.path.join("./", "audio_recording.wav")  # Change the path as needed

    # Convert the audio data to WAV format using pydub
    audio = AudioSegment.from_file(audio_data)
    audio = audio.set_frame_rate(16000)
    audio = audio.set_sample_width(2)
    audio = audio.set_channels(1)
    audio.export(save_path, format="wav")
    print(f'Audio saved to: {save_path}')
    asr_transcript = asr(save_path)

    #print('ASR Transcript:', asr_transcript)
    return asr_transcript

@app.route('/tts', methods=['POST'])
def tts_endpoint():
    text = request.json['answer']
    audio_samples = tts(text)
    result_bytes = tts_to_bytesio(audio_samples)
    return Response(result_bytes, mimetype='audio/wav')

def tts(text: str):
    resp = tts_service.synthesize(text, voice_name=voice_name, language_code=language_code, sample_rate_hz=sample_rate_hz)
    audio_samples = np.frombuffer(resp.audio, dtype=data_type)
    return audio_samples

def tts_to_bytesio(tts_object: object) -> bytes:
    bytes_wav = bytes()
    byte_io = io.BytesIO(bytes_wav)
    write(byte_io, sample_rate_hz, tts_object)
    result_bytes = byte_io.read()
    return result_bytes
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
