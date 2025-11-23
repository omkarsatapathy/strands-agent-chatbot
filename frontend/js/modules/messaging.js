// Messaging Functions
import { API_BASE_URL, CONFIG } from '../config.js';
import { fetchWithRetry } from './api.js';
import {
    updateStatus,
    showError,
    showStatusIndicator,
    updateStatusIndicator,
    removeStatusIndicator,
    showTypingIndicator,
    removeTypingIndicator
} from './ui.js';
import { openMapsPopup, initializeMapsPopup } from './maps.js';

// DOM Elements
let chatMessages, messageInput, sendButton, searchButton;
let cameraButton, imageUploadButton, imageInput, imagePreviewArea, imagePreview, removeImageBtn;

// Camera modal elements
let cameraModal, cameraVideo, cameraCanvas, capturedImage, cameraError, cameraErrorText;
let closeCameraModal, switchCameraBtn, captureBtn, retakeBtn, usePhotoBtn;

// Conversation history
let conversationHistory = [];

// State management
let requestInProgress = false;
let pendingImageBase64 = null;  // Store base64 image data for sending
let pendingImageDataUrl = null; // Store data URL for preview

// Camera state
let currentStream = null;
let facingMode = 'environment'; // 'user' for front camera, 'environment' for back

// Session manager reference (will be set by main.js)
let sessionManager = null;

// Initialize messaging elements
export function initializeMessagingElements() {
    chatMessages = document.getElementById('chatMessages');
    messageInput = document.getElementById('messageInput');
    sendButton = document.getElementById('sendButton');
    searchButton = document.getElementById('searchButton');

    // Image/camera elements
    cameraButton = document.getElementById('cameraButton');
    imageUploadButton = document.getElementById('imageUploadButton');
    imageInput = document.getElementById('imageInput');
    imagePreviewArea = document.getElementById('imagePreviewArea');
    imagePreview = document.getElementById('imagePreview');
    removeImageBtn = document.getElementById('removeImageBtn');

    // Camera modal elements
    cameraModal = document.getElementById('cameraModal');
    cameraVideo = document.getElementById('cameraVideo');
    cameraCanvas = document.getElementById('cameraCanvas');
    capturedImage = document.getElementById('capturedImage');
    cameraError = document.getElementById('cameraError');
    cameraErrorText = document.getElementById('cameraErrorText');
    closeCameraModal = document.getElementById('closeCameraModal');
    switchCameraBtn = document.getElementById('switchCameraBtn');
    captureBtn = document.getElementById('captureBtn');
    retakeBtn = document.getElementById('retakeBtn');
    usePhotoBtn = document.getElementById('usePhotoBtn');

    if (!chatMessages || !messageInput || !sendButton) {
        throw new Error('Required messaging elements not found');
    }

    // Setup image handling
    setupImageHandling();
    setupCameraModal();

    // Initialize maps popup
    initializeMapsPopup();

    return { chatMessages, messageInput, sendButton, searchButton, cameraButton, imageInput };
}

// Setup image handling events
function setupImageHandling() {
    // Image upload button - opens file picker for images
    if (imageUploadButton && imageInput) {
        imageUploadButton.addEventListener('click', () => {
            imageInput.click();
        });

        imageInput.addEventListener('change', handleImageSelect);
    }

    // Camera button - opens camera modal
    if (cameraButton) {
        cameraButton.addEventListener('click', openCameraModal);
    }

    if (removeImageBtn) {
        removeImageBtn.addEventListener('click', clearPendingImage);
    }
}

// Setup camera modal events
function setupCameraModal() {
    if (!cameraModal) return;

    // Close modal
    if (closeCameraModal) {
        closeCameraModal.addEventListener('click', closeCameraModalHandler);
    }

    // Close on backdrop click
    const backdrop = cameraModal.querySelector('.camera-modal-backdrop');
    if (backdrop) {
        backdrop.addEventListener('click', closeCameraModalHandler);
    }

    // Switch camera
    if (switchCameraBtn) {
        switchCameraBtn.addEventListener('click', switchCamera);
    }

    // Capture photo
    if (captureBtn) {
        captureBtn.addEventListener('click', capturePhoto);
    }

    // Retake photo
    if (retakeBtn) {
        retakeBtn.addEventListener('click', retakePhoto);
    }

    // Use photo
    if (usePhotoBtn) {
        usePhotoBtn.addEventListener('click', usePhoto);
    }
}

// Open camera modal
async function openCameraModal() {
    if (!cameraModal) return;

    cameraModal.style.display = 'flex';
    document.body.style.overflow = 'hidden';

    // Reset state
    showCaptureMode();

    // Start camera
    await startCamera();
}

// Close camera modal
function closeCameraModalHandler() {
    if (!cameraModal) return;

    stopCamera();
    cameraModal.style.display = 'none';
    document.body.style.overflow = '';
}

// Start camera stream
async function startCamera() {
    try {
        // Hide error, show video
        if (cameraError) cameraError.style.display = 'none';
        if (cameraVideo) cameraVideo.style.display = 'block';

        const constraints = {
            video: {
                facingMode: facingMode,
                width: { ideal: 1280 },
                height: { ideal: 960 }
            },
            audio: false
        };

        currentStream = await navigator.mediaDevices.getUserMedia(constraints);

        if (cameraVideo) {
            cameraVideo.srcObject = currentStream;
            await cameraVideo.play();
        }

        console.log('[Camera] Started successfully');

    } catch (error) {
        console.error('[Camera] Error starting camera:', error);
        showCameraError(getCameraErrorMessage(error));
    }
}

// Stop camera stream
function stopCamera() {
    if (currentStream) {
        currentStream.getTracks().forEach(track => track.stop());
        currentStream = null;
    }

    if (cameraVideo) {
        cameraVideo.srcObject = null;
    }
}

// Switch between front and back camera
async function switchCamera() {
    facingMode = facingMode === 'environment' ? 'user' : 'environment';
    stopCamera();
    await startCamera();
}

// Capture photo from video
function capturePhoto() {
    if (!cameraVideo || !cameraCanvas || !capturedImage) return;

    // Set canvas size to video size
    cameraCanvas.width = cameraVideo.videoWidth;
    cameraCanvas.height = cameraVideo.videoHeight;

    // Draw video frame to canvas
    const ctx = cameraCanvas.getContext('2d');

    // Mirror if using front camera
    if (facingMode === 'user') {
        ctx.translate(cameraCanvas.width, 0);
        ctx.scale(-1, 1);
    }

    ctx.drawImage(cameraVideo, 0, 0);

    // Get image data URL
    const dataUrl = cameraCanvas.toDataURL('image/jpeg', 0.9);

    // Show captured image
    capturedImage.src = dataUrl;
    showReviewMode();

    console.log('[Camera] Photo captured');
}

// Retake photo - go back to capture mode
function retakePhoto() {
    showCaptureMode();
}

// Use the captured photo
function usePhoto() {
    if (!capturedImage || !capturedImage.src) return;

    const dataUrl = capturedImage.src;

    // Extract base64 data
    pendingImageBase64 = dataUrl.split(',')[1];
    pendingImageDataUrl = dataUrl;

    // Show preview in chat input area
    if (imagePreview && imagePreviewArea) {
        imagePreview.src = dataUrl;
        imagePreviewArea.style.display = 'block';
    }

    // Update button states
    if (cameraButton) cameraButton.classList.add('has-image');
    if (imageUploadButton) imageUploadButton.classList.add('has-image');

    // Close modal
    closeCameraModalHandler();

    console.log('[Camera] Photo ready to send');
}

// Show capture mode (video visible, capture button)
function showCaptureMode() {
    if (cameraVideo) cameraVideo.style.display = 'block';
    if (capturedImage) capturedImage.style.display = 'none';
    if (captureBtn) captureBtn.style.display = 'flex';
    if (switchCameraBtn) switchCameraBtn.style.display = 'flex';
    if (retakeBtn) retakeBtn.style.display = 'none';
    if (usePhotoBtn) usePhotoBtn.style.display = 'none';
}

// Show review mode (captured image visible, retake/use buttons)
function showReviewMode() {
    if (cameraVideo) cameraVideo.style.display = 'none';
    if (capturedImage) capturedImage.style.display = 'block';
    if (captureBtn) captureBtn.style.display = 'none';
    if (switchCameraBtn) switchCameraBtn.style.display = 'none';
    if (retakeBtn) retakeBtn.style.display = 'flex';
    if (usePhotoBtn) usePhotoBtn.style.display = 'block';
}

// Show camera error
function showCameraError(message) {
    if (cameraError) cameraError.style.display = 'flex';
    if (cameraErrorText) cameraErrorText.textContent = message;
    if (cameraVideo) cameraVideo.style.display = 'none';
    if (captureBtn) captureBtn.disabled = true;
}

// Get user-friendly camera error message
function getCameraErrorMessage(error) {
    if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
        return 'Camera access denied. Please allow camera permissions in your browser settings.';
    } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
        return 'No camera found on this device.';
    } else if (error.name === 'NotReadableError' || error.name === 'TrackStartError') {
        return 'Camera is in use by another application.';
    } else if (error.name === 'OverconstrainedError') {
        return 'Camera does not support the requested settings.';
    } else {
        return 'Unable to access camera. Please check your device settings.';
    }
}

// Handle image selection
function handleImageSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
        showError('Please select an image file');
        return;
    }

    // Validate file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
        showError('Image size must be less than 10MB');
        return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
        const dataUrl = e.target.result;
        // Extract base64 data (remove data:image/...;base64, prefix)
        pendingImageBase64 = dataUrl.split(',')[1];
        pendingImageDataUrl = dataUrl;

        // Show preview
        if (imagePreview && imagePreviewArea) {
            imagePreview.src = dataUrl;
            imagePreviewArea.style.display = 'block';
        }

        // Update button states
        if (cameraButton) cameraButton.classList.add('has-image');
        if (imageUploadButton) imageUploadButton.classList.add('has-image');

        console.log('[Messaging] Image loaded, size:', pendingImageBase64.length);
    };
    reader.readAsDataURL(file);

    // Reset input so same file can be selected again
    event.target.value = '';
}

// Clear pending image
export function clearPendingImage() {
    pendingImageBase64 = null;
    pendingImageDataUrl = null;

    if (imagePreviewArea) {
        imagePreviewArea.style.display = 'none';
    }
    if (imagePreview) {
        imagePreview.src = '';
    }
    if (cameraButton) {
        cameraButton.classList.remove('has-image');
    }
    if (imageUploadButton) {
        imageUploadButton.classList.remove('has-image');
    }

    console.log('[Messaging] Pending image cleared');
}

// Check if there's a pending image
export function hasPendingImage() {
    return pendingImageBase64 !== null;
}

// Get pending image base64
export function getPendingImageBase64() {
    return pendingImageBase64;
}

// Set session manager reference
export function setSessionManager(manager) {
    sessionManager = manager;
}

// Get conversation history
export function getConversationHistory() {
    return conversationHistory;
}

// Set conversation history
export function setConversationHistory(history) {
    conversationHistory = history;
}

// Clear conversation history
export function clearConversationHistory() {
    conversationHistory = [];
}

// Convert markdown tables to HTML
function convertMarkdownTables(text) {
    const lines = text.split('\n');
    let result = [];
    let inTable = false;
    let tableRows = [];

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();

        // Check if this is a table row (starts and ends with |)
        if (line.startsWith('|') && line.endsWith('|')) {
            // Check if it's a separator line (contains only |, -, and spaces)
            if (/^\|[\s\-|]+\|$/.test(line)) {
                continue; // Skip separator lines
            }

            if (!inTable) {
                inTable = true;
                tableRows = [];
            }

            // Parse the row
            const cells = line.split('|').slice(1, -1).map(cell => cell.trim());
            tableRows.push(cells);
        } else {
            // Not a table line
            if (inTable) {
                // End of table, convert to HTML
                result.push(convertTableToHTML(tableRows));
                tableRows = [];
                inTable = false;
            }
            result.push(line);
        }
    }

    // Handle table at end of text
    if (inTable && tableRows.length > 0) {
        result.push(convertTableToHTML(tableRows));
    }

    return result.join('\n');
}

function convertTableToHTML(rows) {
    if (rows.length === 0) return '';

    let html = '<table class="markdown-table">';

    // First row is header
    html += '<thead><tr>';
    for (const cell of rows[0]) {
        html += `<th>${cell}</th>`;
    }
    html += '</tr></thead>';

    // Remaining rows are body
    if (rows.length > 1) {
        html += '<tbody>';
        for (let i = 1; i < rows.length; i++) {
            html += '<tr>';
            for (const cell of rows[i]) {
                html += `<td>${cell}</td>`;
            }
            html += '</tr>';
        }
        html += '</tbody>';
    }

    html += '</table>';
    return html;
}

// Add message to chat
export function addMessage(text, sender, costData = null) {
    console.log('addMessage called with:', text.substring(0, 100));

    if (!chatMessages) return;

    // Hide welcome placeholder when first message is added
    const chatWelcome = document.getElementById('chatWelcome');
    if (chatWelcome) {
        chatWelcome.classList.add('hidden');
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const textElement = document.createElement('div');

    // Check for maps widget metadata and extract it
    let mapsWidgetData = null;
    console.log('🔍 Checking for maps widget in text, length:', text.length);

    const mapsWidgetMatch = text.match(/<!--MAPS_WIDGET:([\s\S]*?)-->/);
    console.log('🔍 Maps widget match result:', mapsWidgetMatch ? 'FOUND' : 'NOT FOUND');

    if (mapsWidgetMatch) {
        console.log('🔍 Matched content preview:', mapsWidgetMatch[1].substring(0, 200));
        try {
            mapsWidgetData = JSON.parse(mapsWidgetMatch[1]);
            // Remove the metadata from displayed text
            text = text.replace(/<!--MAPS_WIDGET:[\s\S]*?-->/, '').trim();
            console.log('✅ Maps widget data found:', mapsWidgetData);
        } catch (e) {
            console.error('❌ Failed to parse maps widget data:', e);
            console.error('❌ Raw data that failed to parse:', mapsWidgetMatch[1]);
        }
    } else {
        console.log('❌ No maps widget marker found in text');
    }

    // Process markdown-style formatting
    let formattedText = text;

    // Convert markdown tables to HTML tables
    formattedText = convertMarkdownTables(formattedText);

    // Convert ## Heading to <h3>
    formattedText = formattedText.replace(/^## (.+)$/gm, '<h3>$1</h3>');

    // Convert ### Heading to <h4>
    formattedText = formattedText.replace(/^### (.+)$/gm, '<h4>$1</h4>');

    // Convert **text** to <strong> (non-greedy match)
    formattedText = formattedText.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Convert newlines to <br>
    formattedText = formattedText.replace(/\n/g, '<br>');

    console.log('Formatted text:', formattedText.substring(0, 100));

    textElement.innerHTML = formattedText;
    textElement.style.whiteSpace = 'pre-wrap';

    contentDiv.appendChild(textElement);

    // Add "View on Map" button if maps widget data exists
    if (mapsWidgetData && mapsWidgetData.maps_widget) {
        console.log('🗺️ Creating View on Map button');
        const mapsButton = document.createElement('button');
        mapsButton.className = 'maps-button';
        mapsButton.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                <circle cx="12" cy="10" r="3"></circle>
            </svg>
            View on Map
        `;
        mapsButton.onclick = () => {
            console.log('🗺️ Map button clicked, data:', mapsWidgetData);
            openMapsPopup(mapsWidgetData.maps_widget);
        };
        contentDiv.appendChild(mapsButton);
    }

    // Add audio player for assistant/bot messages
    console.log('[addMessage] Checking sender type:', sender);
    if (sender === 'assistant' || sender === 'bot') {
        console.log('[addMessage] Creating audio player for bot/assistant message');
        const audioContainer = createAudioPlayer(text, costData);
        console.log('[addMessage] Audio container created:', audioContainer);
        contentDiv.appendChild(audioContainer);
        console.log('[addMessage] Audio container appended to contentDiv');
    } else {
        console.log('[addMessage] Skipping audio player - sender is:', sender);
    }

    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);

    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Create audio player for text-to-speech (on-demand generation)
function createAudioPlayer(text, costData = null) {
    console.log('[AudioPlayer] Creating audio player for text:', text.substring(0, 50));

    const audioContainer = document.createElement('div');
    audioContainer.className = 'audio-player-container';

    // Status text
    const statusText = document.createElement('div');
    statusText.className = 'audio-status';
    statusText.innerHTML = '🎵 Click play to generate audio';

    // Progress bar container
    const progressContainer = document.createElement('div');
    progressContainer.className = 'audio-progress-container';

    const progressBar = document.createElement('div');
    progressBar.className = 'audio-progress-bar';
    progressBar.style.width = '0%';

    progressContainer.appendChild(progressBar);

    // Controls container
    const controlsContainer = document.createElement('div');
    controlsContainer.className = 'audio-controls';

    // Play/Pause button
    const playButton = document.createElement('button');
    playButton.className = 'audio-control-button';
    playButton.innerHTML = `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M8 5v14l11-7z"/>
        </svg>
    `;
    playButton.disabled = false;
    playButton.title = 'Generate and play audio';

    // Time display
    const timeDisplay = document.createElement('div');
    timeDisplay.className = 'audio-time';
    timeDisplay.textContent = 'Click to play';

    controlsContainer.appendChild(playButton);
    controlsContainer.appendChild(progressContainer);
    controlsContainer.appendChild(timeDisplay);

    audioContainer.appendChild(statusText);
    audioContainer.appendChild(controlsContainer);

    // Add cost display below audio controls if cost data is available
    // Store initial chat cost for this specific message
    const chatCostInr = (costData && costData.cost_inr !== undefined) ? costData.cost_inr : 0;

    if (chatCostInr > 0) {
        const costDisplay = document.createElement('div');
        costDisplay.className = 'cost-display';
        costDisplay.style.fontSize = '11px';
        costDisplay.style.color = '#888';
        costDisplay.style.marginTop = '4px';
        costDisplay.innerHTML = `Chat cost: ₹${chatCostInr.toFixed(4)}`;
        audioContainer.appendChild(costDisplay);
    }

    let audioElement = null;
    let isPlaying = false;
    let audioGenerated = false;
    let isGenerating = false;

    // Format time helper
    const formatTime = (seconds) => {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    // Update progress bar
    const updateProgress = () => {
        if (audioElement) {
            const progress = (audioElement.currentTime / audioElement.duration) * 100;
            progressBar.style.width = `${progress}%`;
            timeDisplay.textContent = `${formatTime(audioElement.currentTime)} / ${formatTime(audioElement.duration)}`;
        }
    };

    // Generate audio function
    const generateAudio = async () => {
        if (isGenerating || audioGenerated) return;

        try {
            isGenerating = true;
            playButton.disabled = true;
            statusText.innerHTML = '🎵 Generating audio...';
            timeDisplay.textContent = 'Loading...';

            console.log('[AudioPlayer] Generating audio on-demand...');

            const url = `${API_BASE_URL}/api/voice/generate`;
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: text,
                    response_format: 'wav'
                })
            });

            if (!response.ok) {
                throw new Error(`Failed to generate audio: ${response.status}`);
            }

            const audioBlob = await response.blob();
            const audioUrl = URL.createObjectURL(audioBlob);

            audioElement = new Audio(audioUrl);
            audioGenerated = true;

            // Calculate TTS cost separately (characters * TTS pricing)
            // TTS pricing: $15/1M chars for tts-1, USD to INR = 85
            const ttsChars = text.length;
            const ttsCostUsd = (ttsChars / 1_000_000) * 15.0;
            const ttsCostInr = ttsCostUsd * 85;

            // Update cost display to show chat + TTS breakdown
            let costDisplay = audioContainer.querySelector('.cost-display');
            if (!costDisplay) {
                costDisplay = document.createElement('div');
                costDisplay.className = 'cost-display';
                costDisplay.style.fontSize = '11px';
                costDisplay.style.color = '#888';
                costDisplay.style.marginTop = '4px';
                audioContainer.appendChild(costDisplay);
            }

            const totalCost = chatCostInr + ttsCostInr;
            costDisplay.innerHTML = `Chat: ₹${chatCostInr.toFixed(4)} | TTS: ₹${ttsCostInr.toFixed(4)} | Total: ₹${totalCost.toFixed(4)}`;

            console.log(`[AudioPlayer] Cost breakdown - Chat: ₹${chatCostInr.toFixed(4)}, TTS: ₹${ttsCostInr.toFixed(4)}, Total: ₹${totalCost.toFixed(4)}`);

            // Wait for metadata to load
            audioElement.addEventListener('loadedmetadata', () => {
                statusText.innerHTML = '🎵 Audio ready';
                playButton.disabled = false;
                timeDisplay.textContent = `0:00 / ${formatTime(audioElement.duration)}`;
                isGenerating = false;

                // Auto-play after generation
                playAudio();
            });

            // Update progress
            audioElement.addEventListener('timeupdate', updateProgress);

            // Handle end
            audioElement.addEventListener('ended', () => {
                isPlaying = false;
                playButton.innerHTML = `
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M8 5v14l11-7z"/>
                    </svg>
                `;
                statusText.innerHTML = '🎵 Audio ready';
                progressBar.style.width = '0%';
                audioElement.currentTime = 0;
            });

            // Handle errors
            audioElement.addEventListener('error', (e) => {
                console.error('[AudioPlayer] Playback error:', e);
                statusText.innerHTML = '❌ Playback error';
                playButton.disabled = true;
                isGenerating = false;
            });

            console.log('[AudioPlayer] Audio generated successfully');

        } catch (error) {
            console.error('[AudioPlayer] Generation error:', error);
            statusText.innerHTML = '❌ Failed to generate audio';
            playButton.disabled = false;
            timeDisplay.textContent = 'Try again';
            isGenerating = false;
            audioGenerated = false;
        }
    };

    // Play audio function
    const playAudio = async () => {
        if (!audioElement) return;

        try {
            await audioElement.play();
            playButton.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                    <rect x="6" y="4" width="4" height="16"/>
                    <rect x="14" y="4" width="4" height="16"/>
                </svg>
            `;
            statusText.innerHTML = '▶️ Playing';
            isPlaying = true;
        } catch (error) {
            console.error('[AudioPlayer] Play error:', error);
            statusText.innerHTML = '❌ Playback failed';
        }
    };

    // Play/Pause button handler
    playButton.addEventListener('click', async () => {
        // If audio not generated yet, generate it first
        if (!audioGenerated && !isGenerating) {
            await generateAudio();
            return;
        }

        // If currently generating, do nothing
        if (isGenerating) return;

        // Play/Pause logic
        if (isPlaying) {
            audioElement.pause();
            playButton.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M8 5v14l11-7z"/>
                </svg>
            `;
            statusText.innerHTML = '⏸️ Paused';
            isPlaying = false;
        } else {
            await playAudio();
        }
    });

    // Click on progress bar to seek
    progressContainer.addEventListener('click', (e) => {
        if (!audioElement || !audioGenerated) return;

        const rect = progressContainer.getBoundingClientRect();
        const clickX = e.clientX - rect.left;
        const percentage = clickX / rect.width;
        audioElement.currentTime = percentage * audioElement.duration;
    });

    console.log('[AudioPlayer] Returning audio container (on-demand generation)');
    return audioContainer;
}

// Track last status update time for minimum display duration
let lastStatusUpdateTime = 0;
let statusUpdateQueue = [];
let isProcessingStatusQueue = false;

// Process status updates with minimum display time
async function processStatusUpdate(statusId, statusText) {
    const now = Date.now();
    const timeSinceLastUpdate = now - lastStatusUpdateTime;
    const minDisplayTime = 1500; // 1.5 seconds

    if (timeSinceLastUpdate < minDisplayTime) {
        // Wait for remaining time
        await new Promise(resolve => setTimeout(resolve, minDisplayTime - timeSinceLastUpdate));
    }

    updateStatusIndicator(statusId, statusText);
    lastStatusUpdateTime = Date.now();
}

// Queue status updates to ensure minimum display time
async function queueStatusUpdate(statusId, statusText) {
    statusUpdateQueue.push({ statusId, statusText });

    if (!isProcessingStatusQueue) {
        isProcessingStatusQueue = true;
        while (statusUpdateQueue.length > 0) {
            const { statusId, statusText } = statusUpdateQueue.shift();
            await processStatusUpdate(statusId, statusText);
        }
        isProcessingStatusQueue = false;
    }
}

// Handle SSE stream events
async function handleStreamEvent(eventType, eventData, statusId) {
    try {
        const data = JSON.parse(eventData);

        switch (eventType) {
            case 'connected':
                console.log('Connected to stream');
                await queueStatusUpdate(statusId, '⚡ On it...');
                break;

            case 'thinking':
                console.log('Agent thinking:', data.status);
                await queueStatusUpdate(statusId, data.status);
                updateStatus(data.status, true);
                break;

            case 'tool':
                console.log('Tool called:', data);
                const toolStatus = `${data.display_name} (${data.tool_count}/${data.max_tools})`;
                await queueStatusUpdate(statusId, toolStatus);
                updateStatus(data.display_name, true);
                break;

            case 'done':
                console.log('Stream done:', data);
                removeStatusIndicator(statusId);
                updateStatus(data.status, true);

                // Add response to chat with cost data
                if (data.response) {
                    const costData = {
                        cost_inr: data.cost_inr || 0,
                        cost_usd: data.cost_usd || 0,
                        tokens: data.tokens || {}
                    };
                    addMessage(data.response, 'bot', costData);
                    conversationHistory.push({ role: 'assistant', content: data.response });

                    // Save assistant response to database
                    try {
                        await sessionManager.saveMessage('assistant', data.response);
                    } catch (error) {
                        console.error('Failed to save assistant message:', error);
                    }
                }
                break;

            case 'error':
                console.error('Stream error:', data);
                removeStatusIndicator(statusId);
                showError('Error: ' + data.error);
                break;

            case 'cancelled':
                console.log('Stream cancelled');
                removeStatusIndicator(statusId);
                break;

            default:
                console.log('Unknown event:', eventType, data);
        }
    } catch (error) {
        console.error('Error parsing event data:', error, eventData);
    }
}

// Handle image message - send to Gemini for analysis
async function handleImageMessage(userMessage) {
    const imageBase64 = pendingImageBase64;
    const imageDataUrl = pendingImageDataUrl;
    const displayMessage = userMessage || 'Describe this image';

    // Clear the pending image first
    clearPendingImage();

    // Clear input
    messageInput.value = '';
    if (messageInput.style) {
        messageInput.style.height = 'auto';
    }

    // Add user message with image to chat
    addMessageWithImage(displayMessage, 'user', imageDataUrl);
    conversationHistory.push({ role: 'user', content: `[Image attached] ${displayMessage}` });

    // Disable send button
    sendButton.disabled = true;
    updateStatus('Analyzing image...', true);

    // Show status indicator
    const statusId = showStatusIndicator('📷 Analyzing image with Gemini...');

    try {
        console.log('[Messaging] Sending image for analysis...');

        const response = await fetch(`${API_BASE_URL}/api/image/analyze`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                image_base64: imageBase64,
                message: userMessage || 'Describe what you see in this image in detail.'
            })
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Image analysis failed (${response.status}): ${errorText}`);
        }

        const data = await response.json();

        removeStatusIndicator(statusId);

        // Add bot response
        addMessage(data.description, 'bot');
        conversationHistory.push({ role: 'assistant', content: data.description });

        // Save messages to database
        try {
            await sessionManager.saveMessage('user', `[Image attached] ${displayMessage}`);
            await sessionManager.saveMessage('assistant', data.description);

            // Update session title if first message
            if (conversationHistory.length === 2) {
                const title = sessionManager.generateSessionTitle(displayMessage);
                await fetch(`${API_BASE_URL}/api/sessions/${sessionManager.getCurrentSessionId()}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title })
                });
                window.dispatchEvent(new CustomEvent('sessionNeedsReload'));
            }
        } catch (error) {
            console.error('Failed to save messages:', error);
        }

        console.log('[Messaging] Image analysis complete');

    } catch (error) {
        removeStatusIndicator(statusId);
        showError('Failed to analyze image: ' + error.message);
        console.error('[Messaging] Image analysis error:', error);

        // Remove last user message from history if request failed
        if (conversationHistory.length > 0 && conversationHistory[conversationHistory.length - 1].role === 'user') {
            conversationHistory.pop();
        }
    } finally {
        sendButton.disabled = false;
        requestInProgress = false;
        updateStatus('Ready', true);
    }
}

// Add message with image to chat
function addMessageWithImage(text, sender, imageDataUrl) {
    if (!chatMessages) return;

    // Hide welcome placeholder
    const chatWelcome = document.getElementById('chatWelcome');
    if (chatWelcome) {
        chatWelcome.classList.add('hidden');
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    // Add image if present
    if (imageDataUrl) {
        const imgElement = document.createElement('img');
        imgElement.src = imageDataUrl;
        imgElement.className = 'message-image';
        imgElement.alt = 'Attached image';
        contentDiv.appendChild(imgElement);
    }

    // Add text
    const textElement = document.createElement('div');
    textElement.innerHTML = text.replace(/\n/g, '<br>');
    textElement.style.whiteSpace = 'pre-wrap';
    contentDiv.appendChild(textElement);

    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);

    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Send message with SSE streaming support
export async function sendMessage() {
    const message = messageInput.value.trim();
    const hasImage = pendingImageBase64 !== null;

    // Allow sending if there's a message OR an image
    if (!message && !hasImage) return;

    // Check if request already in progress
    if (requestInProgress) {
        console.log('Request already in progress, ignoring...');
        return;
    }

    // Check network connectivity
    if (!navigator.onLine) {
        showError('No internet connection. Please check your network.');
        return;
    }

    // Ensure we have a session
    if (!sessionManager || !sessionManager.getCurrentSessionId()) {
        console.error('No active session');
        showError('No active session. Please reload the page.');
        return;
    }

    requestInProgress = true;

    // If there's an image, handle image analysis flow
    if (hasImage) {
        await handleImageMessage(message);
        return;
    }

    // Add user message to chat
    addMessage(message, 'user');
    conversationHistory.push({ role: 'user', content: message });

    // Save message to database
    try {
        await sessionManager.saveMessage('user', message);

        // Update session title if this is the first message
        if (conversationHistory.length === 1) {
            const title = sessionManager.generateSessionTitle(message);
            await fetch(`${API_BASE_URL}/api/sessions/${sessionManager.getCurrentSessionId()}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title })
            });
            // Trigger session reload event
            window.dispatchEvent(new CustomEvent('sessionNeedsReload'));
        }
    } catch (error) {
        console.error('Failed to save user message:', error);
    }

    // Clear input
    messageInput.value = '';
    if (messageInput.style) {
        messageInput.style.height = 'auto';
    }

    // Disable send button
    sendButton.disabled = true;
    updateStatus('Generating...', true);

    // Show status indicator
    const statusId = showStatusIndicator('⏳ Agent is thinking...');

    // Get last conversation pairs (limit to MAX_CONVERSATION_HISTORY)
    const recentHistory = conversationHistory.slice(-CONFIG.MAX_CONVERSATION_HISTORY);

    try {
        console.log('Starting SSE stream to:', `${API_BASE_URL}/api/chat/stream`);

        // Get selected model provider
        const modelProviderSelect = document.getElementById('modelProvider');
        const modelProvider = modelProviderSelect ? modelProviderSelect.value : null;

        // Get selected response style
        const responseStyleSelect = document.getElementById('responseStyle');
        const responseStyle = responseStyleSelect ? responseStyleSelect.value : 'Normal';

        console.log('Using model provider:', modelProvider || 'default');
        console.log('Using response style:', responseStyle);

        const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                conversation_history: recentHistory,
                session_id: sessionManager.getCurrentSessionId(),
                model_provider: modelProvider,
                response_style: responseStyle
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        // Read the SSE stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();

            if (done) {
                console.log('Stream complete');
                break;
            }

            // Decode chunk and add to buffer
            buffer += decoder.decode(value, { stream: true });

            // Process complete SSE messages
            const lines = buffer.split('\n');
            buffer = lines.pop(); // Keep incomplete line in buffer

            let eventType = 'message';
            let eventData = '';

            for (const line of lines) {
                if (line.startsWith('event:')) {
                    eventType = line.substring(6).trim();
                } else if (line.startsWith('data:')) {
                    eventData = line.substring(5).trim();
                } else if (line === '') {
                    // Empty line indicates end of event
                    if (eventData) {
                        await handleStreamEvent(eventType, eventData, statusId);
                        eventData = '';
                        eventType = 'message';
                    }
                } else if (line.startsWith(':')) {
                    // Heartbeat comment, ignore
                    continue;
                }
            }
        }

    } catch (error) {
        removeStatusIndicator(statusId);

        // User-friendly error messages
        let errorMessage = 'Failed to get response. ';
        if (error.message.includes('timeout')) {
            errorMessage += 'Server is taking too long to respond.';
        } else if (error.message.includes('Failed to fetch') || error.message.includes('Load failed')) {
            errorMessage += 'Cannot connect to server.';
        } else {
            errorMessage += error.message;
        }

        showError(errorMessage);
        console.error('Error:', error);

        // Remove the last user message from history if request failed
        if (conversationHistory.length > 0 && conversationHistory[conversationHistory.length - 1].role === 'user') {
            conversationHistory.pop();
        }
    } finally {
        sendButton.disabled = false;
        requestInProgress = false;
        updateStatus('Ready', true);
    }
}

// Perform web search
export async function performWebSearch() {
    const query = messageInput.value.trim();
    if (!query) {
        showError('Please enter a search query');
        return;
    }

    // Check if request already in progress
    if (requestInProgress) {
        console.log('Request already in progress, ignoring...');
        return;
    }

    // Check network connectivity
    if (!navigator.onLine) {
        showError('No internet connection. Please check your network.');
        return;
    }

    requestInProgress = true;
    updateStatus('Searching...', true);
    sendButton.disabled = true;
    if (searchButton) searchButton.disabled = true;

    const typingId = showTypingIndicator();

    try {
        const response = await fetchWithRetry(`${API_BASE_URL}/api/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                num_results: 5,
                search_type: 'web'
            })
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Search failed (${response.status}): ${errorText}`);
        }

        const data = await response.json();

        removeTypingIndicator(typingId);

        // Format search results
        let resultsText = `Search results for "${query}":\n\n`;
        if (data.results && data.results.length > 0) {
            data.results.forEach((result, index) => {
                if (result.error) {
                    resultsText += result.error;
                } else {
                    resultsText += `${index + 1}. ${result.title}\n${result.snippet}\n${result.link}\n\n`;
                }
            });
        } else {
            resultsText = 'No search results found.';
        }

        addMessage(query, 'user');
        addMessage(resultsText, 'bot');

        conversationHistory.push({ role: 'user', content: query });
        conversationHistory.push({ role: 'assistant', content: resultsText });

        // Save to database
        try {
            await sessionManager.saveMessage('user', query);
            await sessionManager.saveMessage('assistant', resultsText);

            // Update session title if this is the first message
            if (conversationHistory.length === 2) {
                const title = sessionManager.generateSessionTitle(query);
                await fetch(`${API_BASE_URL}/api/sessions/${sessionManager.getCurrentSessionId()}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title })
                });
                // Trigger session reload event
                window.dispatchEvent(new CustomEvent('sessionNeedsReload'));
            }
        } catch (error) {
            console.error('Failed to save search messages:', error);
        }

        messageInput.value = '';
        if (messageInput.style) {
            messageInput.style.height = 'auto';
        }

    } catch (error) {
        removeTypingIndicator(typingId);
        showError('Failed to perform search. ' + error.message);
        console.error('Search error:', error);
    } finally {
        sendButton.disabled = false;
        if (searchButton) searchButton.disabled = false;
        requestInProgress = false;
        updateStatus('Ready', true);
    }
}
