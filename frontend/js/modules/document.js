// Document Upload Functions
import { API_BASE_URL } from '../config.js';
import { updateStatus, showError, showToast, showStatusIndicator, removeStatusIndicator, formatFileSize } from './ui.js';

// DOM Elements
let uploadButton, fileInput, documentArea, documentList;

// Session manager reference
let sessionManager = null;

// Initialize document elements
export function initializeDocumentElements() {
    uploadButton = document.getElementById('uploadButton');
    fileInput = document.getElementById('fileInput');
    documentArea = document.getElementById('documentArea');
    documentList = document.getElementById('documentList');

    if (!uploadButton || !fileInput || !documentArea || !documentList) {
        throw new Error('Required document elements not found');
    }

    return { uploadButton, fileInput, documentArea, documentList };
}

// Set session manager reference
export function setSessionManager(manager) {
    sessionManager = manager;
}

// Handle file upload
export async function handleFileUpload(event) {
    console.log('[Document] File upload triggered');
    const file = event.target.files[0];
    if (!file) return;

    // Validate file size (max 10MB)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
        showError('File too large. Maximum size is 10MB.');
        fileInput.value = '';
        return;
    }

    // Ensure we have a session
    const currentSessionId = sessionManager.getCurrentSessionId();
    if (!currentSessionId) {
        showError('No active session. Please reload the page.');
        fileInput.value = '';
        return;
    }

    try {
        updateStatus('Uploading document...', true);

        // Create FormData
        const formData = new FormData();
        formData.append('file', file);
        formData.append('session_id', currentSessionId);

        // Show upload progress
        const statusId = showStatusIndicator(`📤 Uploading ${file.name}...`);

        // Upload file
        const response = await fetch(`${API_BASE_URL}/api/upload`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Upload failed');
        }

        const result = await response.json();

        removeStatusIndicator(statusId);

        // Reload documents for this session first
        await loadSessionDocuments(currentSessionId);

        // Show success toast notification
        showToast(`Document uploaded successfully: ${file.name}`, 'success');

        updateStatus('Ready', true);

        // Clear file input
        fileInput.value = '';

    } catch (error) {
        console.error('[Document] File upload error:', error);
        showError(`Failed to upload document: ${error.message}`);
        updateStatus('Ready', true);
        fileInput.value = '';
    }
}

// Load documents for a session
export async function loadSessionDocuments(sessionId) {
    console.log('[Document] Loading documents for session:', sessionId);
    try {
        const response = await fetch(`${API_BASE_URL}/api/documents/${sessionId}`);
        if (!response.ok) {
            throw new Error('Failed to fetch documents');
        }

        const data = await response.json();
        const documents = data.documents || [];

        console.log('[Document] Loaded documents:', documents.length);

        // Display documents
        displayDocuments(documents);

    } catch (error) {
        console.error('[Document] Error loading documents:', error);
    }
}

// Display documents in the UI
export function displayDocuments(documents) {
    console.log('[Document] Displaying documents:', documents.length);
    if (!documentList || !documentArea) return;

    if (documents.length === 0) {
        documentArea.style.display = 'none';
        return;
    }

    documentArea.style.display = 'block';
    documentList.innerHTML = '';

    documents.forEach(doc => {
        const docItem = document.createElement('div');
        docItem.className = 'document-item';
        docItem.title = `Click to show in folder: ${doc.filename}`;
        docItem.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
            </svg>
            <span class="document-name" title="${doc.filename}">${doc.filename}</span>
            <span class="document-size">${formatFileSize(doc.file_size)}</span>
        `;

        // Click handler to show in Finder/Explorer
        docItem.addEventListener('click', async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/api/documents/show-in-folder`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        file_path: doc.file_path
                    })
                });

                if (response.ok) {
                    showToast('📂 Opened in Finder', 'success');
                } else {
                    throw new Error('Failed to open folder');
                }
            } catch (error) {
                console.error('[Document] Error opening folder:', error);
                showToast(`File location: ${doc.file_path}`, 'success');
            }
        });

        documentList.appendChild(docItem);
    });
}
