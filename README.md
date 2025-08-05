
# Vision2Audio - Giving the blind an understanding through Google's Gemma 3n multimodel model

Vision2Audio is a web application designed to enhance the lives of visually impaired and blind individuals by enabling them to capture images, ask questions about them, and receive spoken answers using cutting-edge AI technologies.

The application leverages NVIDIA's Riva Automatic Speech Recognition (ASR) to convert spoken questions into text. This text is then fed into vLLM, which serves the Gemma3n model to generate comprehensive image descriptions. Finally, NVIDIA's Riva Text-to-Speech (TTS) technology converts the generated text into spoken audio, delivering the answers to the user in audio format through the browser.

### Usage
Start Nvidia Riva server by running the command:
```
bash riva_start.sh
```
Once the Riva server status is running, open another terminal and execute the following command to run vLLM instance:
```
vllm serve google/gemma-3n-e4b-it \
  --gpu-memory-utilization 0.7 \
  --port 9000 \
  --host 0.0.0.0 \
  --enforce-eager
```
Keep the server running in the background. Open another terminal and run:
```
python3 -m uvicorn app:app --port 5000 --host 0.0.0.0 --ssl-keyfile ./key.pem --ssl-certfile ./cert.pem
```
Open another web brower and navigate to https://IP_ADDRESS:5000

### Acknowledgements
- The implementation of the project relies on [Google's Gemma3n model](https://ai.google.dev/gemma/docs/gemma-3n).
- This project has been made possible in part by leveraging the [NVIDIA RIVA SDK](https://developer.nvidia.com/riva?sortBy=developer_learning_library%2Fsort%2Ffeatured_in.riva%3Adesc%2Ctitle%3Aasc&hitsPerPage=6) and the [vLLM](https://github.com/vllm-project/vllm) inference engine. We acknowledge and thank NVIDIA for providing the RIVA SDK, a powerful framework for building speech AI applications, and the vLLM team for their high-performance large language model inference engine.
