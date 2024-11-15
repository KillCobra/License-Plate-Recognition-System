document.addEventListener('DOMContentLoaded', () => {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    const browseButton = document.getElementById('browseButton');
    const uploadButton = document.getElementById('uploadButton');
    const preview = document.getElementById('preview');
    const result = document.getElementById('result');
    const loader = document.getElementById('loader');
    const canvas = document.getElementById('canvas');
    const ctx = canvas.getContext('2d');

    // Live Camera Elements
    const startCameraButton = document.getElementById('startCameraButton');
    const stopCameraButton = document.getElementById('stopCameraButton');
    const liveVideo = document.getElementById('liveVideo');
    const liveCanvas = document.getElementById('liveCanvas');
    const liveResult = document.getElementById('liveResult');
    const liveCtx = liveCanvas.getContext('2d');

    // Backend API endpoints
    const API_ENDPOINT = 'http://127.0.0.1:8000/upload/';
    const WEBSOCKET_URL = 'ws://127.0.0.1:8000/live/';

    let websocket;
    let videoStream;
    let sendFrameInterval;

    // Handle browse button click
    browseButton.addEventListener('click', () => {
        fileInput.click();
    });

    // Handle file selection
    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });

    // Handle drag and drop
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });

    // Handle files
    function handleFiles(files) {
        if (files.length > 0) {
            const file = files[0];
            preview.innerHTML = '';
            result.innerHTML = '';
            canvas.classList.add('hidden'); // Hide canvas initially

            const fileType = file.type;

            if (fileType.startsWith('image/')) {
                const img = document.createElement('img');
                img.id = 'previewImage';
                img.src = URL.createObjectURL(file);
                img.onload = () => {
                    URL.revokeObjectURL(img.src);
                    canvas.width = img.width;
                    canvas.height = img.height;
                    preview.appendChild(img);
                };
                preview.appendChild(img);
            } else if (fileType.startsWith('video/')) {
                const video = document.createElement('video');
                video.id = 'previewVideo';
                video.src = URL.createObjectURL(file);
                video.controls = true;
                video.onloadedmetadata = () => {
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                };
                preview.appendChild(video);
            } else {
                alert('Unsupported file type!');
                return;
            }

            uploadButton.disabled = false;
        }
    }

    // Handle upload
    uploadButton.addEventListener('click', () => {
        const file = fileInput.files[0];
        if (!file) {
            alert('No file selected!');
            return;
        }

        uploadButton.disabled = true;
        loader.classList.remove('hidden');
        result.innerHTML = '';
        canvas.classList.add('hidden');
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const formData = new FormData();
        formData.append('file', file);

        fetch(API_ENDPOINT, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            loader.classList.add('hidden');
            if (!response.ok) {
                return response.json().then(errData => {
                    throw new Error(errData.detail || 'Unknown error occurred.');
                });
            }
            return response.json();
        })
        .then(data => {
            displayResults(data);
        })
        .catch(error => {
            console.error('Error:', error);
            result.innerText = 'An error occurred while processing the file.';
            uploadButton.disabled = false;
        });
    });

    // Function to display the results
    function displayResults(data) {
        uploadButton.disabled = false;

        if (data.detail) {
            // Handle errors returned from the backend
            result.innerHTML = `<p style="color: red;">Error: ${data.detail}</p>`;
            return;
        }

        if (data.results && data.results.length > 0) {
            let htmlContent = `<h2>Detected License Plates:</h2><ul>`;
            data.results.forEach((plate, index) => {
                htmlContent += `<li><strong>Plate ${index + 1}:</strong> ${plate.plate}<br>
                                <small>Coordinates: x=${plate.coordinates.x}, y=${plate.coordinates.y}, 
                                width=${plate.coordinates.width}, height=${plate.coordinates.height}</small></li>`;
            });
            htmlContent += `</ul>`;
            result.innerHTML = htmlContent;

            // Draw bounding boxes on the image
            const img = document.getElementById('previewImage');
            if (img) {
                canvas.classList.remove('hidden'); // Show canvas
                ctx.drawImage(img, 0, 0, img.width, img.height);

                data.results.forEach(plate => {
                    const { x, y, width, height } = plate.coordinates;
                    ctx.strokeStyle = 'red';
                    ctx.lineWidth = 2;
                    ctx.strokeRect(x, y, width, height);
                });
            }
        } else {
            result.innerText = 'No license plates detected.';
        }
    }

    // Handle Start Live Camera
    startCameraButton.addEventListener('click', async () => {
        try {
            // Access the webcam
            videoStream = await navigator.mediaDevices.getUserMedia({ video: true });
            liveVideo.srcObject = videoStream;
            liveVideo.classList.remove('hidden');
            liveCanvas.classList.remove('hidden');
            startCameraButton.disabled = true;
            stopCameraButton.disabled = false;
            liveResult.innerHTML = 'Connecting to the server...';

            // Establish WebSocket connection
            websocket = new WebSocket(WEBSOCKET_URL);
            console.log('Attempting WebSocket connection to:', WEBSOCKET_URL);

            websocket.onopen = () => {
                console.log('WebSocket connection established successfully.');
                liveResult.innerHTML = 'Live camera connected.';
                startSendingFrames();
            };

            websocket.onmessage = (event) => {
                let data;
                try {
                    data = JSON.parse(event.data);
                } catch (e) {
                    console.error('Error parsing WebSocket message:', e);
                    return;
                }
                if (data.results) {
                    displayLiveResults(data);
                } else if (data.detail) {
                    liveResult.innerHTML = `<p style="color: red;">Error: ${data.detail}</p>`;
                }
            };

            websocket.onerror = (error) => {
                console.error('Detailed WebSocket error:', error);
                liveResult.innerHTML = `<p style="color: red;">WebSocket error: ${error.message || 'Connection failed'}</p>`;
            };

            websocket.onclose = () => {
                console.log('WebSocket connection closed.');
                liveResult.innerHTML = 'Live camera disconnected.';
                stopSendingFrames();
                startCameraButton.disabled = false;
                stopCameraButton.disabled = true;
            };
        } catch (err) {
            console.error('Error accessing the camera:', err);
            alert('Could not access the camera. Please check your permissions.');
        }
    });

    // Handle Stop Live Camera
    stopCameraButton.addEventListener('click', () => {
        // Stop video stream
        if (videoStream) {
            videoStream.getTracks().forEach(track => track.stop());
            liveVideo.srcObject = null;
        }

        // Close WebSocket connection
        if (websocket && websocket.readyState === WebSocket.OPEN) {
            websocket.close();
        }

        // Clear overlays
        liveCtx.clearRect(0, 0, liveCanvas.width, liveCanvas.height);
        liveResult.innerHTML = 'Live camera stopped.';
        liveVideo.classList.add('hidden');
        liveCanvas.classList.add('hidden');
        stopCameraButton.disabled = true;
        startCameraButton.disabled = false;
    });

    // Function to start sending frames via WebSocket
    function startSendingFrames() {
        sendFrameInterval = setInterval(() => {
            captureAndSendFrame();
        }, 1000); // Send a frame every second
    }

    // Function to stop sending frames
    function stopSendingFrames() {
        clearInterval(sendFrameInterval);
    }

    // Function to capture frame from video and send via WebSocket
    function captureAndSendFrame() {
        if (liveVideo.paused || liveVideo.ended) {
            return;
        }

        liveCanvas.width = liveVideo.videoWidth;
        liveCanvas.height = liveVideo.videoHeight;
        liveCtx.drawImage(liveVideo, 0, 0, liveCanvas.width, liveCanvas.height);
        liveCanvas.toBlob(blob => {
            if (blob) {
                blob.arrayBuffer().then(buffer => {
                    websocket.send(buffer);
                }).catch(err => {
                    console.error('Error converting blob to array buffer:', err);
                });
            }
        }, 'image/jpeg');
    }

    // Function to display live detection results
    function displayLiveResults(data) {
        if (data.results && data.results.length > 0) {
            let htmlContent = `<h3>Detected License Plates:</h3><ul>`;
            data.results.forEach((plate, index) => {
                htmlContent += `<li><strong>Plate ${index + 1}:</strong> ${plate.plate}<br>
                                <small>Coordinates: x=${plate.coordinates.x}, y=${plate.coordinates.y}, 
                                width=${plate.coordinates.width}, height=${plate.coordinates.height}</small></li>`;
            });
            htmlContent += `</ul>`;
            liveResult.innerHTML = htmlContent;

            // Draw bounding boxes on the live canvas
            data.results.forEach(plate => {
                const { x, y, width, height } = plate.coordinates;
                liveCtx.strokeStyle = 'red';
                liveCtx.lineWidth = 2;
                liveCtx.strokeRect(x, y, width, height);
                liveCtx.font = '16px Arial';
                liveCtx.fillStyle = 'red';
                liveCtx.fillText(plate.plate, x, y > 20 ? y - 5 : y + 15);
            });
        } else {
            liveResult.innerText = 'No license plates detected.';
        }
    }
});