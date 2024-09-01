document.addEventListener('DOMContentLoaded', function() {
    const startCameraButton = document.getElementById('startCamera');
    const stopCameraButton = document.getElementById('stopCamera');
    const capture2DButton = document.getElementById('capture2d');
    const capture3DButton = document.getElementById('capture3d');
    const cameraStatus = document.getElementById('cameraStatus');
    const capturedImage = document.getElementById('capturedImage');
    const captured3DImage = document.getElementById('captured3dImage');

    startCameraButton.addEventListener('click', () => {
        fetch('/camera/start', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.status) {
                    startCameraButton.disabled = true;
                    stopCameraButton.disabled = false;
                    capture2DButton.disabled = false;
                    capture3DButton.disabled = false;
                    if (cameraStatus) {
                        cameraStatus.textContent = 'Camera is active';
                    } else {
                        console.error('cameraStatus element is missing in HTML');
                    }
                } else {
                    throw new Error(data.error || 'Unknown error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error starting camera: ' + error.message);
            });
    });

    stopCameraButton.addEventListener('click', () => {
        fetch('/camera/stop', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.status) {
                    startCameraButton.disabled = false;
                    stopCameraButton.disabled = true;
                    capture2DButton.disabled = true;
                    capture3DButton.disabled = true;
                    capturedImage.style.display = 'none';
                    captured3DImage.style.display = 'none';
                    if (cameraStatus) {
                        cameraStatus.textContent = 'Camera is not active';
                    }
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error stopping camera: ' + error.message);
            });
    });

    capture2DButton.addEventListener('click', () => {
        fetch('/camera/capture', { method: 'GET' })
            .then(response => response.blob())
            .then(blob => {
                capturedImage.src = URL.createObjectURL(blob);
                capturedImage.style.display = 'block';
                captured3DImage.style.display = 'none';
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error capturing 2D image: ' + error.message);
            });
    });

    capture3DButton.addEventListener('click', () => {
        fetch('/camera/capture3d', { method: 'GET' })
            .then(response => response.blob())
            .then(blob => {
                captured3DImage.src = URL.createObjectURL(blob);
                captured3DImage.style.display = 'block';
                capturedImage.style.display = 'none';
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error capturing 3D image: ' + error.message);
            });
    });

    document.getElementById('settingsForm').addEventListener('submit', (e) => {
        e.preventDefault();
        const width = document.getElementById('width').value;
        const height = document.getElementById('height').value;
        const frameRate = document.getElementById('frameRate').value;

        fetch('/camera/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ width, height, frame_rate: frameRate })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status) {
                updateStatus();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error applying settings: ' + error.message);
        });
    });

    function updateStatus() {
        fetch('/camera/status')
            .then(response => response.json())
            .then(data => {
                if (cameraStatus) {
                    if (data.camera_active) {
                        cameraStatus.textContent = `Camera is active - Resolution: ${data.resolution}, Frame Rate: ${data.frame_rate}`;
                    } else {
                        cameraStatus.textContent = 'Camera is not active';
                    }
                } else {
                    console.error('cameraStatus element is missing in HTML');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error fetching camera status: ' + error.message);
            });
    }
});
