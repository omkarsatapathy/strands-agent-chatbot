import { API_BASE_URL } from '../config.js';
import { updateStatus, showError, showToast, showStatusIndicator, removeStatusIndicator, formatFileSize } from './ui.js';

let uploadButton, fileInput, documentArea, documentList;
let sessionManager = null;

function initializeDocumentElements(elements, manager) {
    uploadButton = elements.uploadButton;
    fileInput = elements.fileInput;
    documentArea = elements.documentArea;
    documentList = elements.documentList;
    sessionManager = manager;
}

// Handle file upload
async function handleFileUpload(event, createNewChatFn) {
    const file = event.target.files[0];
    if (!file) return;

    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
        showError('File too large. Maximum size is 10MB.');
        fileInput.value = '';
        return;
    }

    const currentSessionId = sessionManager.getCurrentSessionId();
    if (!currentSessionId) {
        showError('No active session. Creating new session...');
        await createNewChatFn();
        setTimeout(() => handleFileUpload(event, createNewChatFn), 500);
        return;
    }

    try {
        updateStatus('Uploading document...', true);

        const formData = new FormData();
        formData.append('file', file);
        formData.append('session_id', currentSessionId);

        const statusId = showStatusIndicator(`📤 Uploading ${file.name}...`);

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

        await loadSessionDocuments(currentSessionId);

        showToast(`Document uploaded successfully: ${file.name}`, 'success');

        updateStatus('Ready', true);

        fileInput.value = '';

    } catch (error) {
        console.error('File upload error:', error);
        showError(`Failed to upload document: ${error.message}`);
        updateStatus('Ready', true);
        fileInput.value = '';
    }
}

// Load documents for a session
async function loadSessionDocuments(sessionId) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/documents/${sessionId}`);
        if (!response.ok) {
            throw new Error('Failed to fetch documents');
        }

        const data = await response.json();
        const documents = data.documents || [];

        displayDocuments(documents);

    } catch (error) {
        console.error('Error loading documents:', error);
    }
}

// Display documents in the UI
function displayDocuments(documents) {
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
                console.error('Error opening folder:', error);
                showToast(`File location: ${doc.file_path}`, 'success');
            }
        });

        documentList.appendChild(docItem);
    });
}

export {
    initializeDocumentElements,
    handleFileUpload,
    loadSessionDocuments,
    displayDocuments
};
