async function startVideo(video) {
    const stream = await navigator.mediaDevices.getUserMedia({
        video: {
            width: { ideal: 1280 },
            height: { ideal: 720 }
        },
        audio: false
    });

    console.log("[1 CAMERA] stream started");

    video.srcObject = stream;
    await video.play();

    console.log("[1 CAMERA] videoWidth = " + video.videoWidth);
    console.log("[1 CAMERA] videoHeight = " + video.videoHeight);
    console.log("[1 CAMERA] video ready = true");

    return stream;
}


function capture(video, canvas) {
    if (!video.videoWidth || !video.videoHeight) {
        throw new Error("Camera frame is not ready yet.");
    }

    // Scale down to 640px width to speed up network and backend processing
    const targetWidth = 640;
    const scale = targetWidth / video.videoWidth;
    canvas.width = targetWidth;
    canvas.height = video.videoHeight * scale;

    const context = canvas.getContext("2d");
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    const dataUrl = canvas.toDataURL("image/jpeg", 0.7);
    
    console.log("[2 FRAME CAPTURE] captured");
    console.log("[2 FRAME CAPTURE] width = " + canvas.width);
    console.log("[2 FRAME CAPTURE] height = " + canvas.height);
    console.log("[2 FRAME CAPTURE] base64 length = " + dataUrl.length);

    return dataUrl;
}


/* =========================================================
   STUDENT FACE REGISTRATION
   ========================================================= */

window.FaceCapture = {

    init(studentId) {

        const video = document.getElementById("camera");
        const canvas = document.getElementById("frame");
        const start = document.getElementById("start-camera");
        const stop = document.getElementById("stop-camera");
        const captureBtn = document.getElementById("capture-face");
        const status = document.getElementById("capture-status");

        let ready = false;
        let streamObj = null;
        let captureTimer = null;
        let isProcessing = false;

        start.onclick = async () => {
            try {
                setButtonLoading(start, "Starting...");
                status.textContent = "Starting camera...";

                streamObj = await startVideo(video);

                ready = true;
                resetButton(start);
                start.disabled = true;
                captureBtn.disabled = false;
                stop.disabled = false;

                status.textContent = "Camera ready — move slightly, then capture.";
                showToast("Camera enabled", "info");

            } catch (e) {
                resetButton(start);
                status.textContent = "Camera unavailable: " + e.message;
                showToast("Camera unavailable: " + e.message, "error");
            }
        };

        stop.onclick = () => {
            if (!ready) return;
            
            showConfirmModal("Disable camera?", "Facial capture will stop until the camera is enabled again.", "Disable Camera", () => {
                // Disable camera
                if (streamObj) {
                    streamObj.getTracks().forEach(track => track.stop());
                }
                video.srcObject = null;
                ready = false;
                
                // Stop registration polling
                if (captureTimer) {
                    clearInterval(captureTimer);
                    captureTimer = null;
                }
                isProcessing = false;
                
                captureBtn.disabled = true;
                stop.disabled = true;
                resetButton(captureBtn); // just in case it was loading
                start.disabled = false;
                
                status.textContent = "Camera disabled.";
                showToast("Camera disabled", "warning");
            }, "warning");
        };

        captureBtn.onclick = () => {
            if (!ready) {
                status.textContent = "Please enable the camera first.";
                return;
            }

            setButtonLoading(captureBtn, "Processing...");
            status.textContent = "Starting capture sequence...";

            const captureFrame = async () => {
                if (!ready || isProcessing) return;
                isProcessing = true;

                try {
                    const imgData = capture(video, canvas);
                    console.log("[3 API REQUEST] Sending frame to /api/students/" + studentId + "/face-capture");
                    
                    const response = await fetch(
                        "/api/students/" + studentId + "/face-capture",
                        {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ image: imgData })
                        }
                    );

                    const data = await response.json();
                    if (!ready) return;

                    if (data.ok) {
                        clearInterval(captureTimer);
                        status.textContent = "Facial profile registered successfully.";
                        showToast("Facial profile registered successfully.", "success");
                        setTimeout(() => {
                            window.location.href = "/students";
                        }, 1200);
                    } else {
                        if (data.message && (data.message.includes("timed out") || data.message.includes("Liveness failed"))) {
                            clearInterval(captureTimer);
                            status.textContent = data.message;
                            showToast(data.message, "warning");
                            resetButton(captureBtn);
                        } else {
                            // Only update text to avoid spamming toast on every frame
                            let uiMsg = data.message || "Processing facial profile...";
                            if (uiMsg.includes("face")) uiMsg = "No face detected. Please position your face inside the camera.";
                            if (data.stage && data.stage.includes("Liveness")) uiMsg = data.message;
                            else if (uiMsg.includes("liveness")) uiMsg = "Please follow liveness instructions.";
                            if (uiMsg.includes("multiple")) uiMsg = "Multiple faces detected. Please make sure only one person is visible.";
                            if (uiMsg.includes("blur") || uiMsg.includes("quality")) uiMsg = "Image quality is too low. Please keep your face steady.";
                            status.textContent = uiMsg;
                        }
                    }
                } catch (e) {
                    if (!ready) return;
                    clearInterval(captureTimer);
                    status.textContent = "Capture error: " + e.message;
                    showToast("Facial registration failed.", "error");
                    resetButton(captureBtn);
                } finally {
                    isProcessing = false;
                }
            };

            captureFrame();
            captureTimer = setInterval(captureFrame, 200);
        };
    }
};


/* =========================================================
   LIVE ATTENDANCE
   ========================================================= */

window.AttendanceCamera = {
    init(sessionId) {
        const video = document.getElementById('attendance-camera');
        const canvas = document.getElementById('attendance-frame');
        const start = document.getElementById('attendance-start');
        const successPopup =
        document.getElementById('attendance-success-popup');

        const popupStudentName =
        document.getElementById('popup-student-name');

        const popupStudentRoll =
        document.getElementById('popup-student-roll');

        const state = document.getElementById('camera-state');
        const title = document.getElementById('decision-title');
        const msg = document.getElementById('decision-message');
        const conf = document.getElementById('confidence');

        const stages = {
            face: document.getElementById('stage-face'),
            quality: document.getElementById('stage-quality'),
            live: document.getElementById('stage-live'),
            recognition: document.getElementById('stage-recognition'),
            db: document.getElementById('stage-db')
        };

        let timer = null;
        let busy = false;

        function resetStages() {
            stages.face.textContent = '○ Face detection';
            stages.quality.textContent = '○ Face quality';
            stages.live.textContent = '○ Liveness';
            stages.recognition.textContent = '○ Recognition';
            stages.db.textContent = '○ Database record';
        }

        function updateStages(stage, decision) {
            resetStages();

            if (stage === 'Face Detection') {
                stages.face.textContent = '✓ Face detection';
            }

            if (stage === 'Face Quality') {
                stages.face.textContent = '✓ Face detection';
                stages.quality.textContent = '✓ Face quality';
            }

            if (stage === 'Liveness') {
                stages.face.textContent = '✓ Face detection';
                stages.quality.textContent = '✓ Face quality';
                stages.live.textContent = '✓ Liveness';
            }

            if (stage === 'Recognition') {
                stages.face.textContent = '✓ Face detection';
                stages.quality.textContent = '✓ Face quality';
                stages.live.textContent = '✓ Liveness';
                stages.recognition.textContent = '✓ Recognition';
            }

            if (decision === 'accepted') {
                stages.face.textContent = '✓ Face detection';
                stages.quality.textContent = '✓ Face quality';
                stages.live.textContent = '✓ Liveness';
                stages.recognition.textContent = '✓ Recognition';
                stages.db.textContent = '✓ Database record';
            }

            if (decision === 'duplicate') {
                stages.face.textContent = '✓ Face detection';
                stages.quality.textContent = '✓ Face quality';
                stages.live.textContent = '✓ Liveness';
                stages.recognition.textContent = '✓ Recognition';
                stages.db.textContent = '✓ Already recorded';
            }
        }

        start.onclick = async () => {
            try {
                await startVideo(video);

                state.textContent = 'Camera active';
                start.textContent = 'Camera enabled';

                title.textContent = 'Ready';
                msg.textContent = 'Looking for a student...';
                conf.textContent = '';

                if (timer) {
                    clearInterval(timer);
                }

                timer = setInterval(async () => {

                    if (busy || video.readyState < 2) {
                        return;
                    }

                    busy = true;

                    try {
                        const image = capture(video, canvas);

                        const res = await fetch(
                            '/api/attendance/' +
                            sessionId +
                            '/process-frame',
                            {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({
                                    image: image
                                })
                            }
                        );

                        if (!res.ok) {
                            throw new Error(
                                'Server returned HTTP ' + res.status
                            );
                        }

                        const d = await res.json();

                        if (d.decision === 'rejected' || d.decision === 'unknown') {

                          title.textContent = 'Student not recognized';

                          msg.textContent =
                          'No registered student matched. Please look at the camera and try again.';

                          if (d.confidence !== undefined &&
                           d.confidence !== null) {

                           conf.textContent =
                            'Recognition confidence: ' +
                            d.confidence + '%';

                         } else {
                           conf.textContent = '';
                        }

                        setTimeout(() => {

                          if (!busy) {

                            title.textContent = 'Ready';

                            msg.textContent =
                              'Looking for a student...';

                            resetStages();

                            conf.textContent = '';
                          }

                        }, 1500);
                    }

                        updateStages(
                            d.stage,
                            d.decision
                        );

                        title.textContent =
                            d.stage || 'Processing';

                        msg.textContent =
                            d.message || '';

                        if (d.confidence !== undefined &&
                            d.confidence !== null) {

                            conf.textContent =
                                'Recognition confidence: ' +
                                d.confidence + '%';

                        } else {
                            conf.textContent = '';
                        }

                        /*
                         * IMPORTANT:
                         * A rejected recognition must NOT stop
                         * the attendance loop.
                         */

                        if (d.decision === 'rejected') {

                            title.textContent =
                                'Student not recognized';

                            msg.textContent =
                                'No registered student matched. ' +
                                'Please look at the camera and try again.';

                            conf.textContent =
                                d.confidence !== undefined
                                    ? 'Recognition confidence: ' +
                                      d.confidence + '%'
                                    : '';

                            // Allow the next camera frame to be checked.
                            setTimeout(() => {
                                if (!busy) {
                                    title.textContent = 'Ready';
                                    msg.textContent =
                                        'Looking for a student...';
                                    resetStages();
                                    conf.textContent = '';
                                }
                            }, 1500);
                        }

                        if (d.decision === 'accepted') {

                            title.textContent = 'Attendance marked';

                            msg.textContent =
                                d.message || 'Attendance recorded successfully.';

                            // Get student information returned by backend
                            let studentName = 'Student';
                            let studentRoll = '-';

                            if (d.student_name) {
                                studentName = d.student_name;
                            }

                            if (d.student_roll) {
                                studentRoll = d.student_roll;
                            }

                            popupStudentName.textContent = studentName;
                            popupStudentRoll.textContent =
                                'Roll No: ' + studentRoll;

                            // Show large success popup
                            successPopup.classList.add('show');

                            // Keep popup visible for 6 seconds
                            setTimeout(() => {

                                successPopup.classList.remove('show');

                                title.textContent = 'Ready';

                                msg.textContent =
                                    'Looking for a student...';

                                resetStages();

                                conf.textContent = '';

                            }, 6000);
                        }

                        if (d.decision === 'duplicate') {

                            title.textContent =
                                'Already marked';

                            msg.textContent =
                                d.message ||
                                'Attendance has already been recorded for this session.';
                        }

                    } catch (e) {

                        console.error(e);

                        title.textContent =
                            'Processing error';

                        msg.textContent =
                            'Unable to process this frame. Retrying...';

                    } finally {

                        busy = false;
                    }

                }, 900);

            } catch (e) {

                console.error(e);

                state.textContent =
                    'Camera unavailable';

                title.textContent =
                    'Camera unavailable';

                msg.textContent =
                    e.message;
            }
        };
    }
};