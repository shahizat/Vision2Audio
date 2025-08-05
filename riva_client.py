import io
import grpc
import riva.client
import wave

# Create a Riva client and connect to the Riva Speech API server
auth = riva.client.Auth(uri='localhost:50051')
riva_asr = riva.client.ASRService(auth)

# Path to the audio file (must be .wav in LINEAR_PCM format)
input_wav_path = "./test.wav"

# Read the audio file content into memory
with open(input_wav_path, 'rb') as wav_file:
    audio_content = wav_file.read()

# Optionally: save a copy of the file elsewhere
output_wav_path = "./saved_output.wav"
with open(output_wav_path, 'wb') as out_file:
    out_file.write(audio_content)
print(f"Audio file saved to: {output_wav_path}")

# Configure the recognition settings
config = riva.client.RecognitionConfig()
config.language_code = "en-US"
config.max_alternatives = 1
config.enable_automatic_punctuation = True
config.audio_channel_count = 1

# Perform offline ASR (automatic speech recognition)
response = riva_asr.offline_recognize(audio_content, config)

# Extract and print the best transcript
asr_best_transcript = response.results[0].alternatives[0].transcript
print("ASR Transcript:", asr_best_transcript)

# Print the full response object
print("\n\nFull Response Message:")
print(response)
