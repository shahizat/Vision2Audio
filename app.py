from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, File, UploadFile, Request, Depends, Response, status
from fastapi.responses import HTMLResponse, StreamingResponse
from starlette.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn
import httpx
import base64
import os
from pydub import AudioSegment
import io
import json
from PIL import Image
from io import BytesIO, StringIO
import grpc
import riva.client
import numpy as np
from scipy.io.wavfile import write
import logging
from typing import List

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Vision2Audio")

# Riva ASR/TTS Setup
auth = riva.client.Auth(uri='localhost:50051')
riva_asr = riva.client.ASRService(auth)
tts_service = riva.client.SpeechSynthesisService(auth)

language_code = "en-US"
sample_rate_hz = 44100
voice_name = "English-US.Female-1"
data_type = np.int16

# Gemma3n Server URL
GEMMA3N_SERVER_URL = "http://localhost:9000/v1/chat/completions"

app = FastAPI()

class ChatInput(BaseModel):
    prompts: List[str]
    image_path: str

# Static and Templates Setup
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get('/')
async def index_loader(request: Request):
    return templates.TemplateResponse('index.html', {"request": request})

@app.route('/describe', methods=['POST'])
async def describe(request: Request):
    data = await request.json()
    encoded_string = data.get('image', '')
    audio_transcription = data.get('audioTranscription', '')
    logger.info("Audio transcription: " + audio_transcription)

    try:
        # Decode image from base64
        image_data = base64.b64decode(encoded_string)
        image = Image.open(io.BytesIO(image_data))

        if image.mode == "RGBA":
            image = image.convert("RGB")

        image.save("temp_image.jpg")

        # Build the messages array
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant. Be concise and accurate. Don't use more that 10 words."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encoded_string}"
                        }
                    },
                    {
                        "type": "text",
                        "text": audio_transcription
                    }
                ]
            }
        ]

        payload = {
            "model": "google/gemma-3n-e4b-it",
            "messages": messages,
            "max_tokens": 200,
            "stream": True
        }

        async def generate_reply():
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", GEMMA3N_SERVER_URL, json=payload) as resp:
                    if resp.status_code != 200:
                        logger.error(f"Model server returned {resp.status_code}")
                        yield f'{{"error": "Model server error: {resp.status_code}"}}\n\n'
                        return
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            content = line[6:]
                            try:
                                content_json = json.loads(content)
                                token = content_json["choices"][0].get("delta", {}).get("content", "")
                                if token:
                                    yield f'{token}\n\n'
                            except json.JSONDecodeError:
                                continue
        return StreamingResponse(generate_reply(), media_type='text/event-stream')

    except Exception as e:
        logger.error(f"Error in /describe: {str(e)}", exc_info=True)
        return {"error": "Failed to process request", "detail": str(e)}


@app.post('/stopRecording')
async def stop_recording(audio: UploadFile = File(...)):
    try:
        transcript = await process_audio(audio)
        return {"transcript": transcript}
    except ValueError as ve:
        return {"transcript": "", "error": str(ve)}
    except Exception as e:
        logger.error(f"Audio processing failed: {str(e)}", exc_info=True)
        return {"transcript": "", "error": f"Internal server error: {str(e)}"}


async def process_audio(audio_data: UploadFile):
    buffer = BytesIO()
    buffer.write(audio_data.file.read())
    buffer.seek(0)
    audio = AudioSegment.from_file(buffer)
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)

    processed_buffer = BytesIO()
    audio.export(processed_buffer, format="wav")
    processed_buffer.seek(0)

    asr_transcript = asr(processed_buffer)
    return asr_transcript


@app.post('/tts')
async def tts_endpoint(request: Request):
    text = (await request.json())['answer']
    try:
        audio_samples = tts(text)
        result_bytes = tts_to_bytesio(audio_samples)
        return StreamingResponse(BytesIO(result_bytes), media_type='audio/wav')
    except Exception as e:
        logger.error(f"TTS failed: {str(e)}", exc_info=True)
        return {"error": "TTS generation failed", "detail": str(e)}


def tts(text: str):
    resp = tts_service.synthesize(text, voice_name=voice_name, language_code=language_code, sample_rate_hz=sample_rate_hz)
    audio_samples = np.frombuffer(resp.audio, dtype=data_type)
    return audio_samples


def tts_to_bytesio(tts_object: object) -> bytes:
    byte_io = io.BytesIO()
    write(byte_io, sample_rate_hz, tts_object)
    return byte_io.getvalue()


def asr(audio_input):
    if isinstance(audio_input, io.IOBase):
        content = audio_input.read()
    else:
        with io.open(audio_input, 'rb') as fh:
            content = fh.read()

    config = riva.client.RecognitionConfig()
    config.language_code = "en-US"
    config.max_alternatives = 1
    config.enable_automatic_punctuation = True
    config.audio_channel_count = 1

    response = riva_asr.offline_recognize(content, config)

    if not response.results:
        raise ValueError("ASR returned no results.")

    result = response.results[0]

    if not result.alternatives:
        raise ValueError("ASR result has no alternatives.")

    return result.alternatives[0].transcript


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000)