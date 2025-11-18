// UI Helper Functions

// DOM Elements
let statusText, statusDot, chatMessages;

// Initialize UI elements
export function initializeUIElements() {
    statusText = document.querySelector('.status-text');
    statusDot = document.querySelector('.status-dot');
    chatMessages = document.getElementById('chatMessages');

    if (!statusText || !statusDot || !chatMessages) {
        throw new Error('Required UI elements not found');
    }

    return { statusText, statusDot, chatMessages };
}

// Update status indicator
export function updateStatus(text, isOnline) {
    if (statusText && statusDot) {
        statusText.textContent = text;
        statusDot.style.background = isOnline ? '#4ade80' : '#f87171';
    }
}

// Show error message
export function showError(message, type = 'error') {
    if (!chatMessages) return;

    const errorDiv = document.createElement('div');
    errorDiv.className = type === 'success' ? 'success-message' : 'error-message';
    errorDiv.textContent = message;

    chatMessages.appendChild(errorDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    setTimeout(() => {
        errorDiv.remove();
    }, 5000);
}

// Show toast notification
export function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast-notification ${type}`;

    const icon = type === 'success' ? '✅' : '❌';

    toast.innerHTML = `
        <div class="toast-icon">${icon}</div>
        <div class="toast-content">${message}</div>
        <button class="toast-close">OK</button>
    `;

    document.body.appendChild(toast);

    const closeBtn = toast.querySelector('.toast-close');
    const closeToast = () => {
        toast.classList.add('hiding');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    };

    closeBtn.addEventListener('click', closeToast);
    setTimeout(closeToast, 3000);
}

// Show status indicator (replaces typing indicator)
export function showStatusIndicator(statusText) {
    if (!chatMessages) return null;

    const statusDiv = document.createElement('div');
    statusDiv.className = 'message bot-message status-message';
    statusDiv.id = 'status-indicator-' + Date.now();

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const statusElement = document.createElement('div');
    statusElement.className = 'status-text-indicator';
    statusElement.textContent = statusText;

    contentDiv.appendChild(statusElement);
    statusDiv.appendChild(contentDiv);
    chatMessages.appendChild(statusDiv);

    chatMessages.scrollTop = chatMessages.scrollHeight;

    return statusDiv.id;
}

// Update status indicator text
export function updateStatusIndicator(id, statusText) {
    if (!chatMessages) return;

    const statusDiv = document.getElementById(id);
    if (statusDiv) {
        const statusElement = statusDiv.querySelector('.status-text-indicator');
        if (statusElement) {
            statusElement.textContent = statusText;
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }
}

// Remove status indicator
export function removeStatusIndicator(id) {
    const indicator = document.getElementById(id);
    if (indicator) {
        indicator.remove();
    }
}

// Show typing indicator (kept for backward compatibility)
export function showTypingIndicator() {
    if (!chatMessages) return null;

    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot-message';
    typingDiv.id = 'typing-indicator-' + Date.now();

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const typingIndicator = document.createElement('div');
    typingIndicator.className = 'typing-indicator';
    typingIndicator.innerHTML = '<span></span><span></span><span></span>';

    contentDiv.appendChild(typingIndicator);
    typingDiv.appendChild(contentDiv);
    chatMessages.appendChild(typingDiv);

    chatMessages.scrollTop = chatMessages.scrollHeight;

    return typingDiv.id;
}

// Remove typing indicator
export function removeTypingIndicator(id) {
    const indicator = document.getElementById(id);
    if (indicator) {
        indicator.remove();
    }
}

// Format file size
export function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}
