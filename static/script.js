// Audio Context and Howler.js Initialization
Howler.autoUnlock = true;
Howler.usingWebAudio = true;
Howler.html5PoolSize = 1;

// Global state variables
let userInteracted = false;
let mediaRecorder;
let isRecording = false;
let currentTTS = null;
let stream = null;
let video = document.getElementById('videoElement');
let facingMode = 'environment';

// Function to handle initial user interaction
function handleFirstInteraction() {
  if (!userInteracted) {
    userInteracted = true;
    sessionStorage.setItem('userInteracted', 'true');
    
    // Play silent audio to unlock audio context
    const silentAudio = new Howl({
      src: ['data:audio/wav;base64,UklGRl9vT19XQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YU...'],
      volume: 0,
      onend: function() {
        console.log('Audio context unlocked');
      }
    });
    silentAudio.play();
    
    // Remove event listeners
    document.removeEventListener('click', handleFirstInteraction);
    document.removeEventListener('touchstart', handleFirstInteraction);
  }
}

// Check for previous interaction
userInteracted = sessionStorage.getItem('userInteracted') === 'true';

// Add event listeners for initial interaction
if (!userInteracted) {
  document.addEventListener('click', handleFirstInteraction, { once: true });
  document.addEventListener('touchstart', handleFirstInteraction, { once: true });
}

// Media capture function
function captureUserMedia(mediaConstraints, successCallback, errorCallback) {
  navigator.mediaDevices.getUserMedia(mediaConstraints)
    .then(successCallback)
    .catch(errorCallback);
}

// Media constraints
var mediaConstraints = {
  audio: true
};

// Function to stop current TTS playback
function stopTTS() {
  if (currentTTS) {
    currentTTS.stop();
    currentTTS = null;
  }
}

// Start/stop recording handler
document.querySelector('#start-recording').onclick = function() {
  if (!isRecording) {
    this.disabled = true;
    isRecording = true;
    stopTTS();
    captureUserMedia(mediaConstraints, onMediaSuccess, onMediaError);
    const descriptionDiv = document.getElementById('description');
    descriptionDiv.textContent = 'Recording...';
  } else {
    stopRecording();
  }
};

function onMediaSuccess(stream) {
  var audiosContainer = document.getElementById('audios-container');
  var audio = document.createElement('audio');
  audio.controls = true;
  audio.muted = true;
  audio.srcObject = stream;
  audio.play();
  audiosContainer.appendChild(audio);

  mediaRecorder = new MediaStreamRecorder(stream);
  mediaRecorder.stream = stream;
  mediaRecorder.recorderType = StereoAudioRecorder;
  mediaRecorder.mimeType = 'audio/wav';

  mediaRecorder.ondataavailable = function(blob) {
    if (isRecording) {
      var a = document.createElement('a');
      a.target = '_blank';
      a.href = URL.createObjectURL(blob);
      audiosContainer.appendChild(a);
      audiosContainer.appendChild(document.createElement('hr'));
      sendAudioToBackend(blob);
    }
  };

  var timeInterval = 5000;
  mediaRecorder.start(parseInt(timeInterval));

  setTimeout(function() {
    isRecording = false;
    mediaRecorder.stop();
    mediaRecorder.stream.stop();
    document.querySelector('#start-recording').disabled = false;
  }, timeInterval);
}

function onMediaError(e) {
  console.error('media error', e);
}

// Video functions
function startVideo() {
  if (stream) {
    stream.getTracks().forEach(track => track.stop());
  }
  
  const constraints = {
    video: {
      facingMode: facingMode,
      width: { ideal: 1280 },
      height: { ideal: 720 }
    }
  };

  navigator.mediaDevices.getUserMedia(constraints)
    .then(function(mediaStream) {
      stream = mediaStream;
      video.srcObject = mediaStream;
      video.playsInline = true;
      video.setAttribute('playsinline', 'true');
      video.muted = true;
      
      video.onloadedmetadata = function(e) {
        video.play().catch(err => {
          console.log('Video play error:', err);
        });
        if (facingMode === 'user') {
          video.style.transform = 'scaleX(-1)';
        } else {
          video.style.transform = 'scaleX(1)';
        }
      };
    })
    .catch(function(err) {
      console.log(err.name + ': ' + err.message);
      if (err.name === 'OverconstrainedError') {
        constraints.video.width = { ideal: 640 };
        constraints.video.height = { ideal: 480 };
        navigator.mediaDevices.getUserMedia(constraints)
          .then(mediaStream => {
            stream = mediaStream;
            video.srcObject = mediaStream;
            video.play();
          });
      }
    });
}

// Backend communication functions
function sendAudioToBackend(audioBlob) {
  const descriptionDiv = document.getElementById('description');
  const formData = new FormData();
  formData.append('audio', audioBlob);
  
  fetch('/stopRecording', {
    method: 'POST',
    body: formData,
  })
  .then(response => {
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    return response.json(); 
  })
  .then(data => {
    const asrTranscript = data.transcript;
    console.log('ASR Transcript:', asrTranscript);
    triggerDescribeRequest(asrTranscript)
    descriptionDiv.textContent = `ASR Transcript: ${asrTranscript}`;
  })
  .catch(error => {
    console.error('Error:', error);
  });
}

function triggerDescribeRequest(audioTranscription) {
  let canvas = document.createElement('canvas');
  canvas.width = video.clientWidth;
  canvas.height = video.clientHeight;
  let ctx = canvas.getContext('2d');

  function drawVideoToCanvas() {
    const videoRatio = video.videoWidth / video.videoHeight;
    const canvasRatio = canvas.width / canvas.height;
    let drawWidth, drawHeight, startX, startY;

    if (videoRatio > canvasRatio) {
      drawHeight = video.videoHeight;
      drawWidth = video.videoHeight * canvasRatio;
      startX = (video.videoWidth - drawWidth) / 2;
      startY = 0;
    } else {
      drawWidth = video.videoWidth;
      drawHeight = video.videoWidth / canvasRatio;
      startX = 0;
      startY = (video.videoHeight - drawHeight) / 2;
    }

    ctx.drawImage(video, startX, startY, drawWidth, drawHeight, 0, 0, canvas.width, canvas.height);
  }

  drawVideoToCanvas();

  let dataURL = canvas.toDataURL('image/png');
  let base64ImageContent = dataURL.replace(/^data:image\/(png|jpg);base64,/, '');

  const descriptionDiv = document.getElementById('description');
  descriptionDiv.textContent = 'Loading...';

  const requestData = {
    image: base64ImageContent,
    audioTranscription: audioTranscription,
  };

  fetch('/describe', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(requestData),
  })
  .then((response) => {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    descriptionDiv.textContent = '';
    reader.read().then(function processText({ done, value }) {
      if (done) {
        if (buffer.length) {
          descriptionDiv.textContent += buffer + ' ';
          console.log('vLLM answer:', descriptionDiv.textContent);
          text2speech(descriptionDiv.textContent);
        }
        return;
      }
      const text = buffer + decoder.decode(value, { stream: true });
      const words = text.split(' ');
      buffer = words.pop();
      words.forEach((word) => (descriptionDiv.textContent += word + ' '));
      reader.read().then(processText);
    });
  })
  .catch((err) => console.error(err));
}

function text2speech(text) {
  if (!userInteracted) {
    console.warn('Audio playback blocked - no user interaction yet');
    return;
  }

  fetch('/tts', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ answer: text }),
  })
  .then(response => response.blob())
  .then(blob => {
    const url = URL.createObjectURL(blob);

    if (currentTTS) {
      currentTTS.stop();
    }

    currentTTS = new Howl({
      src: [url],
      html5: true,
      format: ['wav', 'mp3'],
      autoplay: true,
      onend: function() {
        console.log('TTS playback finished');
        URL.revokeObjectURL(url);
        currentTTS = null;
      },
      onloaderror: function(id, err) {
        console.error('Howler load error:', err);
      },
      onplayerror: function() {
        currentTTS.once('unlock', function() {
          currentTTS.play();
        });
      }
    });

    setTimeout(() => {
      currentTTS.play();
    }, 100);
  })
  .catch(error => console.error('Error:', error));
}

// Initialize the video when the page loads
startVideo();

// Add accessibility features
document.addEventListener('DOMContentLoaded', function() {
  // Add ARIA labels for screen readers
  const startButton = document.querySelector('#start-recording');
  startButton.setAttribute('aria-label', 'Start recording button. Press to begin recording audio.');
  
  // Add instructions for visually impaired users
  const instructions = document.createElement('div');
  instructions.setAttribute('aria-live', 'polite');
  instructions.textContent = 'Please tap anywhere on the screen to enable audio playback.';
  document.body.prepend(instructions);
  
  // Remove instructions after first interaction
  document.addEventListener('click', function() {
    instructions.remove();
  }, { once: true });
});