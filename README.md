
# Vision2Audio - Giving the blind an understanding through AI

### More details can be found here - [Hackster.io](https://www.hackster.io/shahizat/vision2audio-giving-the-blind-an-understanding-through-ai-33f929)

Vision2Audio is a web application designed to enhance the lives of visually impaired and blind individuals by enabling them to capture images, ask questions about them, and receive spoken answers using cutting-edge AI technologies.

The application leverages NVIDIA's Riva Automatic Speech Recognition (ASR) to convert spoken questions into text. This text is then fed into the LLaVA (Large Language-and-Vision Assistant) multimodal model using llama.cpp server implementation, which provides comprehensive image description. Finally, NVIDIA's Riva Text-to-Speech (TTS) technology converts the generated text into spoken audio, delivering the answers to the user in an accessible format.

![Alt text](/demo.png "Demo")


### Usage
For simplicity we will assume everything is installed. Start Nvidia Riva server by running the command:
```
bash riva_start.sh
```
Once the Riva server status is running, open another terminal and execute the following command to run llava server via llama.cpp:
```
./bin/server -m models/llava1.5-13B/ggml-model-q4_k.gguf
   --mmproj models/llava1.5-13B/mmproj-model-f16.gguf
   --port 8080
   -ngl 35
```

You can download the models from [here](https://huggingface.co/mys/ggml_bakllava-1/tree/main). Keep the server running in the background. Open another terminal and run:
```
python3 -m flask run --host=0.0.0.0 --debug
```
Open another terminal and run cloudflared tunnel using the following command:
```
cloudflared tunnel --url http://127.0.0.1:5000

```

### Acknowledgements
The implementation of the project relies on:
* It would not be possible without the llama.cpp project by [@ggerganov](https://www.github.com/ggerganov) 
* [ LLaVaVision project - A simple Be My Eyes web app with a llama.cpp/llava backend.](https://github.com/lxe/llavavision)

I thank the original authors for their open-sourcing.

