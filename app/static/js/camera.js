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

        const video =
            document.getElementById("attendance-camera");

        const canvas =
            document.getElementById("attendance-frame");

        const start =
            document.getElementById("attendance-start");

        const state =
            document.getElementById("camera-state");

        const title =
            document.getElementById("decision-title");

        const msg =
            document.getElementById("decision-message");

        const conf =
            document.getElementById("confidence");

        const stageFace =
            document.getElementById("stage-face");

        const stageQuality =
            document.getElementById("stage-quality");

        const stageLive =
            document.getElementById("stage-live");

        const stageRecognition =
            document.getElementById("stage-recognition");

        const stageDb =
            document.getElementById("stage-db");


        let timer = null;
        let busy = false;


        /* -------------------------------------------------
           Stage helper
           ------------------------------------------------- */

        function setStage(element, status, label) {

            if (!element) return;

            element.className = "";

            if (status === "done") {

                element.textContent = "✓ " + label;
                element.classList.add("stage-done");

            } else if (status === "active") {

                element.textContent = "◉ " + label;
                element.classList.add("stage-active");

            } else if (status === "failed") {

                element.textContent = "✗ " + label;
                element.classList.add("stage-failed");

            } else {

                element.textContent = "○ " + label;
            }
        }


        /* -------------------------------------------------
           Reset pipeline
           ------------------------------------------------- */

        function resetPipeline() {

            setStage(
                stageFace,
                "idle",
                "Face detection"
            );

            setStage(
                stageQuality,
                "idle",
                "Face quality"
            );

            setStage(
                stageLive,
                "idle",
                "Liveness"
            );

            setStage(
                stageRecognition,
                "idle",
                "Recognition"
            );

            setStage(
                stageDb,
                "idle",
                "Database record"
            );
        }


        /* -------------------------------------------------
           Update pipeline
           ------------------------------------------------- */

        function renderPipeline(currentStage, decision) {

            const stage =
                String(currentStage || "")
                    .trim()
                    .toLowerCase();


            /*
             * No face
             */

            if (
                stage.includes("face detection") &&
                decision === "waiting"
            ) {

                setStage(
                    stageFace,
                    "active",
                    "Face detection"
                );

                setStage(
                    stageQuality,
                    "idle",
                    "Face quality"
                );

                setStage(
                    stageLive,
                    "idle",
                    "Liveness"
                );

                setStage(
                    stageRecognition,
                    "idle",
                    "Recognition"
                );

                setStage(
                    stageDb,
                    "idle",
                    "Database record"
                );

                return;
            }


            /*
             * Face detection rejected
             */

            if (
                stage.includes("face detection") &&
                decision === "rejected"
            ) {

                setStage(
                    stageFace,
                    "failed",
                    "Face detection"
                );

                setStage(
                    stageQuality,
                    "idle",
                    "Face quality"
                );

                setStage(
                    stageLive,
                    "idle",
                    "Liveness"
                );

                setStage(
                    stageRecognition,
                    "idle",
                    "Recognition"
                );

                setStage(
                    stageDb,
                    "idle",
                    "Database record"
                );

                return;
            }


            /*
             * Face quality
             */

            if (stage.includes("face quality")) {

                setStage(
                    stageFace,
                    "done",
                    "Face detection"
                );

                if (decision === "rejected") {

                    setStage(
                        stageQuality,
                        "failed",
                        "Face quality"
                    );

                } else {

                    setStage(
                        stageQuality,
                        "active",
                        "Face quality"
                    );
                }

                return;
            }


            /*
             * Liveness
             *
             * IMPORTANT:
             * "rejected" here does NOT stop the camera.
             * The liveness detector needs more frames.
             */

            if (stage.includes("liveness")) {

                setStage(
                    stageFace,
                    "done",
                    "Face detection"
                );

                setStage(
                    stageQuality,
                    "done",
                    "Face quality"
                );

                if (decision === "rejected") {

                    setStage(
                        stageLive,
                        "failed",
                        "Liveness"
                    );

                } else {

                    setStage(
                        stageLive,
                        "active",
                        "Liveness"
                    );
                }

                setStage(
                    stageRecognition,
                    "idle",
                    "Recognition"
                );

                setStage(
                    stageDb,
                    "idle",
                    "Database record"
                );

                return;
            }


            /*
             * Recognition
             */

            if (stage.includes("recognition")) {

                setStage(
                    stageFace,
                    "done",
                    "Face detection"
                );

                setStage(
                    stageQuality,
                    "done",
                    "Face quality"
                );

                setStage(
                    stageLive,
                    "done",
                    "Liveness"
                );

                if (decision === "rejected") {

                    setStage(
                        stageRecognition,
                        "failed",
                        "Recognition"
                    );

                } else {

                    setStage(
                        stageRecognition,
                        "active",
                        "Recognition"
                    );
                }

                setStage(
                    stageDb,
                    "idle",
                    "Database record"
                );

                return;
            }


            /*
             * Successful attendance
             */

            if (decision === "accepted") {

                setStage(
                    stageFace,
                    "done",
                    "Face detection"
                );

                setStage(
                    stageQuality,
                    "done",
                    "Face quality"
                );

                setStage(
                    stageLive,
                    "done",
                    "Liveness"
                );

                setStage(
                    stageRecognition,
                    "done",
                    "Recognition"
                );

                setStage(
                    stageDb,
                    "done",
                    "Database record"
                );

                return;
            }


            /*
             * Duplicate attendance
             */

            if (decision === "duplicate") {

                setStage(
                    stageFace,
                    "done",
                    "Face detection"
                );

                setStage(
                    stageQuality,
                    "done",
                    "Face quality"
                );

                setStage(
                    stageLive,
                    "done",
                    "Liveness"
                );

                setStage(
                    stageRecognition,
                    "done",
                    "Recognition"
                );

                setStage(
                    stageDb,
                    "done",
                    "Database record"
                );

                return;
            }
        }


        /* -------------------------------------------------
           Stop polling
           ------------------------------------------------- */

        function stopPolling() {

            if (timer) {

                clearInterval(timer);
                timer = null;
            }
        }
        
        let unknownRegistrationMode = false;
        let unknownTargetId = null;

        /* -------------------------------------------------
           Process one frame
           ------------------------------------------------- */

        async function processFrame() {

            if (
                busy ||
                video.readyState < 2
            ) {
                return;
            }

            busy = true;

            try {
                const imgData = capture(video, canvas);
                
                let endpointUrl = "/api/attendance/" + sessionId + "/process-frame";
                if (unknownRegistrationMode && unknownTargetId) {
                    endpointUrl = "/api/attendance/" + sessionId + "/register-unknown/process-frame?target=" + encodeURIComponent(unknownTargetId);
                }
                
                const response = await fetch(
                    endpointUrl,
                    {
                        method: "POST",
                        headers: {
                            "Content-Type":
                                "application/json"
                        },
                        body: JSON.stringify({ image: imgData })
                    }
                );


                let data;

                try {

                    data = await response.json();

                } catch {

                    throw new Error(
                        "Invalid response from server."
                    );
                }


                if (!response.ok) {

                    throw new Error(
                        data.message ||
                        "Server error while processing attendance."
                    );
                }


                /* -------------------------------
                   Decision information
                   ------------------------------- */

                title.textContent =
                    data.stage || "Processing";

                msg.textContent =
                    data.message || "";


                if (
                    data.confidence !== undefined &&
                    data.confidence !== null
                ) {

                    conf.textContent =
                        "Recognition confidence: " +
                        data.confidence +
                        "%";

                } else {

                    conf.textContent = "";
                }


                /* -------------------------------
                   Pipeline
                   ------------------------------- */

                renderPipeline(
                    data.stage,
                    data.decision
                );
                
                /* -------------------------------
                   Unknown Person
                   ------------------------------- */
                   
                if (data.decision === "unknown") {
                    stopPolling();
                    const modal = document.getElementById("unknown-modal");
                    const list = document.getElementById("unknown-list");
                    list.innerHTML = "";
                    
                    data.unknowns.forEach(uid => {
                        const btn = document.createElement("button");
                        btn.className = "primary-btn";
                        btn.style.width = "100%";
                        btn.textContent = "Register " + uid;
                        btn.onclick = () => {
                            unknownTargetId = uid;
                            unknownRegistrationMode = true;
                            modal.classList.add("d-none");
                            
                            resetPipeline();
                            title.textContent = "Registration Mode";
                            msg.textContent = "Please follow the instructions on screen.";
                            state.textContent = "Registering " + uid;
                            
                            processFrame();
                            timer = setInterval(processFrame, 250);
                        };
                        list.appendChild(btn);
                    });
                    
                    modal.classList.remove("d-none");
                    
                    document.getElementById("unknown-cancel-btn").onclick = () => {
                        modal.classList.add("d-none");
                        resetPipeline();
                        title.textContent = "Ready for next student";
                        msg.textContent = "Next student, please look at the camera.";
                        conf.textContent = "";
                        state.textContent = "Camera active";
                        processFrame();
                        timer = setInterval(processFrame, 250);
                    };
                    return;
                }
                
                if (data.decision === "unknown_ready") {
                    stopPolling();
                    const modal = document.getElementById("student-details-modal");
                    modal.classList.remove("d-none");
                    
                    document.getElementById("student-cancel-btn").onclick = () => {
                        modal.classList.add("d-none");
                        unknownRegistrationMode = false;
                        unknownTargetId = null;
                        
                        resetPipeline();
                        title.textContent = "Ready for next student";
                        msg.textContent = "Next student, please look at the camera.";
                        conf.textContent = "";
                        state.textContent = "Camera active";
                        processFrame();
                        timer = setInterval(processFrame, 250);
                    };
                    
                    document.getElementById("student-save-btn").onclick = async () => {
                        const studentId = document.getElementById("student-select").value;
                        if (!studentId) {
                            showToast("Please select a student.", "warning");
                            return;
                        }
                        
                        const btn = document.getElementById("student-save-btn");
                        btn.disabled = true;
                        btn.textContent = "Saving...";
                        
                        try {
                            const res = await fetch("/api/attendance/" + sessionId + "/finalize-unknown", {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({ target: unknownTargetId, student_id: studentId })
                            });
                            const fData = await res.json();
                            if (!fData.ok) {
                                throw new Error(fData.message || "Failed to finalize registration.");
                            }
                            
                            modal.classList.add("d-none");
                            showToast(fData.message, "success", "Success");
                            
                            unknownRegistrationMode = false;
                            unknownTargetId = null;
                            
                            setTimeout(() => {
                                resetPipeline();
                                title.textContent = "Ready for next student";
                                msg.textContent = "Next student, please look at the camera.";
                                conf.textContent = "";
                                state.textContent = "Camera active";
                                processFrame();
                                timer = setInterval(processFrame, 250);
                            }, 2000);
                            
                        } catch (err) {
                            showToast(err.message, "error");
                        } finally {
                            btn.disabled = false;
                            btn.textContent = "Save & Mark Present";
                        }
                    };
                    return;
                }


                /* -------------------------------
                   Accepted
                   ------------------------------- */

                if (data.decision === "accepted") {
                    title.textContent = "Attendance Accepted";
                    msg.textContent = data.message || "Attendance recorded successfully.";
                    state.textContent = "Preparing for next student...";
                    
                    let toastTitle = data.message || "Attendance marked";
                    let toastMsg = "";
                    if (data.confidence) {
                        toastMsg = `Recognition confidence: ${data.confidence}%<br>Liveness: Passed`;
                    }
                    showToast(toastMsg, "success", toastTitle);

                    stopPolling();

                    setTimeout(() => {
                        resetPipeline();
                        title.textContent = "Ready for next student";
                        msg.textContent = "Next student, please look at the camera.";
                        conf.textContent = "";
                        state.textContent = "Camera active";
                        processFrame();
                        timer = setInterval(processFrame, 250);
                    }, 2500);

                } else if (data.decision === "duplicate") {
                    title.textContent = "Already Marked";
                    msg.textContent = data.message || "This student has already been marked. Next student, please.";
                    state.textContent = "Preparing for next student...";
                    
                    showToast(msg.textContent, "warning", title.textContent);

                    stopPolling();

    setTimeout(() => {

        resetPipeline();

        title.textContent =
            "Ready for next student";

        msg.textContent =
            "Next student, please look at the camera.";

        conf.textContent = "";

        state.textContent =
            "Camera active";

        processFrame();
        timer = setInterval(
            processFrame,
            250
        );

    }, 2500);
}


                /*
                 * IMPORTANT:
                 *
                 * waiting / rejected responses
                 * do NOT stop polling.
                 *
                 * The system must keep receiving frames
                 * so the student can retry and the liveness
                 * detector can obtain consecutive frames.
                 */

            } catch (e) {

                title.textContent =
                    "Processing error";

                msg.textContent =
                    e.message ||
                    "Unable to process the camera frame.";

            } finally {

                busy = false;
            }
        }


        /* -------------------------------------------------
           Start camera
           ------------------------------------------------- */

        start.onclick = async () => {

            try {

                start.disabled = true;

                state.textContent =
                    "Starting camera...";

                title.textContent =
                    "Preparing camera";

                msg.textContent =
                    "Please look directly at the camera.";

                resetPipeline();


                await startVideo(video);


                state.textContent =
                    "Camera active";

                start.textContent =
                    "Camera enabled";


                /*
                 * Small delay before first frame.
                 * This allows the webcam to initialise.
                 */

                await new Promise(resolve => {
                    setTimeout(resolve, 500);
                });


                /*
                 * Start immediately,
                 * then continue every 250ms.
                 */

                await processFrame();

                timer = setInterval(
                    processFrame,
                    250
                );


            } catch (e) {

                start.disabled = false;

                state.textContent =
                    "Camera unavailable";

                title.textContent =
                    "Camera unavailable";

                msg.textContent =
                    e.message ||
                    "Please check camera permissions.";
            }
        };
    }
};