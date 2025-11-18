// Main Entry Point
import { API_BASE_URL } from './config.js';
import { checkServerHealth } from './modules/api.js';
import {
    initializeUIElements,
    updateStatus,
    showError
} from './modules/ui.js';
import {
    initializeMessagingElements,
    sendMessage,
    performWebSearch,
    setSessionManager as setMessagingSessionManager
} from './modules/messaging.js';
import {
    initializeSessionElements,
    initializeSessions,
    loadSessions,
    createNewChat,
    toggleSidebar,
    setSessionManager as setSessionManagerRef
} from './modules/session.js';
import {
    initializeDocumentElements,
    handleFileUpload,
    loadSessionDocuments,
    setSessionManager as setDocumentSessionManager
} from './modules/document.js';

// Session Manager class (imported from session-manager.js)
class SessionManager {
    constructor(apiBaseUrl) {
        this.apiBaseUrl = apiBaseUrl;
        this.currentSessionId = null;
        this.sessions = [];
    }

    generateSessionTitle(message) {
        const maxLength = 30;
        if (message.length <= maxLength) {
            return message;
        }
        return message.substring(0, maxLength) + '...';
    }

    async createSession(firstMessage = 'New Chat') {
        try {
            const title = this.generateSessionTitle(firstMessage);
            const response = await fetch(`${this.apiBaseUrl}/api/sessions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ title })
            });

            if (!response.ok) {
                throw new Error(`Failed to create session: ${response.status}`);
            }

            const session = await response.json();
            this.currentSessionId = session.session_id;
            return session;
        } catch (error) {
            console.error('Error creating session:', error);
            throw error;
        }
    }

    getCurrentSessionId() {
        return this.currentSessionId;
    }

    setCurrentSessionId(sessionId) {
        this.currentSessionId = sessionId;
    }

    async listSessions(limit = 50) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/sessions?limit=${limit}`);

            if (!response.ok) {
                throw new Error(`Failed to list sessions: ${response.status}`);
            }

            const data = await response.json();
            this.sessions = data.sessions || [];
            return this.sessions;
        } catch (error) {
            console.error('Error listing sessions:', error);
            throw error;
        }
    }

    async getSession(sessionId, includeMessages = true) {
        try {
            const response = await fetch(
                `${this.apiBaseUrl}/api/sessions/${sessionId}?include_messages=${includeMessages}`
            );

            if (!response.ok) {
                throw new Error(`Failed to get session: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Error getting session:', error);
            throw error;
        }
    }

    async deleteSession(sessionId) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/sessions/${sessionId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error(`Failed to delete session: ${response.status}`);
            }

            this.sessions = this.sessions.filter(s => s.session_id !== sessionId);

            if (this.currentSessionId === sessionId) {
                this.currentSessionId = null;
            }

            return true;
        } catch (error) {
            console.error('Error deleting session:', error);
            throw error;
        }
    }

    async saveMessage(role, content) {
        if (!this.currentSessionId) {
            console.warn('No active session to save message to');
            return null;
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}/api/messages`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: this.currentSessionId,
                    role,
                    content
                })
            });

            if (!response.ok) {
                throw new Error(`Failed to save message: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Error saving message:', error);
            throw error;
        }
    }

    async getMessages(sessionId) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/messages/${sessionId}`);

            if (!response.ok) {
                throw new Error(`Failed to get messages: ${response.status}`);
            }

            const data = await response.json();
            return data.messages || [];
        } catch (error) {
            console.error('Error getting messages:', error);
            throw error;
        }
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) {
            return 'Just now';
        } else if (diffMins < 60) {
            return `${diffMins}m ago`;
        } else if (diffHours < 24) {
            return `${diffHours}h ago`;
        } else if (diffDays < 7) {
            return `${diffDays}d ago`;
        } else {
            return date.toLocaleDateString();
        }
    }
}

// Global session manager instance
let sessionManager = null;

// Global DOM elements
let messageInput, sendButton, clearButton, searchButton;
let sidebarToggle, newChatButton, uploadButton, fileInput;

// Initialize application
async function initializeApp() {
    console.log('=== INITIALIZING APPLICATION ===');
    console.log('API_BASE_URL:', API_BASE_URL);

    try {
        // Initialize UI elements
        console.log('[Main] Initializing UI elements...');
        initializeUIElements();

        // Initialize messaging elements
        console.log('[Main] Initializing messaging elements...');
        const messagingElements = initializeMessagingElements();
        messageInput = messagingElements.messageInput;
        sendButton = messagingElements.sendButton;
        searchButton = messagingElements.searchButton;

        // Initialize session elements
        console.log('[Main] Initializing session elements...');
        const sessionElements = initializeSessionElements();
        sidebarToggle = sessionElements.sidebarToggle;
        newChatButton = sessionElements.newChatButton;

        // Initialize document elements
        console.log('[Main] Initializing document elements...');
        const documentElements = initializeDocumentElements();
        uploadButton = documentElements.uploadButton;
        fileInput = documentElements.fileInput;

        // Check server health
        console.log('[Main] Checking server health...');
        const healthStatus = await checkServerHealth();
        updateStatus(healthStatus.message, healthStatus.isOnline);

        // Setup event listeners
        console.log('[Main] Setting up event listeners...');
        setupEventListeners();

        // Auto-resize textarea
        autoResizeTextarea();

        // Setup offline detection
        setupOfflineDetection();

        // Initialize session manager
        console.log('[Main] Creating session manager...');
        sessionManager = new SessionManager(API_BASE_URL);

        // Share session manager with modules
        setMessagingSessionManager(sessionManager);
        setSessionManagerRef(sessionManager);
        setDocumentSessionManager(sessionManager);

        // Load sessions and create new session if none exists
        console.log('[Main] Initializing sessions...');
        await initializeSessions();

        console.log('=== APPLICATION INITIALIZED SUCCESSFULLY ===');

    } catch (error) {
        console.error('[Main] Initialization error:', error);
        showError('Failed to initialize application. Please refresh the page.');
    }
}

// Setup event listeners
function setupEventListeners() {
    console.log('[Main] Setting up event listeners...');

    // Send message
    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Clear button / New chat
    if (clearButton) {
        clearButton.addEventListener('click', createNewChat);
    }

    // Search button
    if (searchButton) {
        searchButton.addEventListener('click', performWebSearch);
    }

    // New chat button
    if (newChatButton) {
        newChatButton.addEventListener('click', createNewChat);
    }

    // Sidebar toggle
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', toggleSidebar);
    }

    // File upload
    if (uploadButton) {
        uploadButton.addEventListener('click', () => fileInput.click());
    }
    if (fileInput) {
        fileInput.addEventListener('change', handleFileUpload);
    }

    // Textarea auto-resize
    messageInput.addEventListener('input', autoResizeTextarea);

    // Prevent zoom on double-tap for iOS
    messageInput.addEventListener('touchend', (e) => {
        const now = new Date().getTime();
        const lastTap = messageInput.dataset.lastTap || 0;
        if (now - lastTap < 300) {
            e.preventDefault();
        }
        messageInput.dataset.lastTap = now;
    });

    // Listen for session loaded event to load documents
    console.log('[Main] Setting up sessionLoaded event listener...');
    window.addEventListener('sessionLoaded', async (event) => {
        console.log('[Main] sessionLoaded event received:', event.detail);
        const sessionId = event.detail.sessionId;
        if (sessionId) {
            console.log('[Main] Loading documents for session:', sessionId);
            await loadSessionDocuments(sessionId);
        }
    });

    // Listen for session needs reload event
    window.addEventListener('sessionNeedsReload', async () => {
        console.log('[Main] sessionNeedsReload event received');
        await loadSessions();
    });

    console.log('[Main] Event listeners setup complete');
}

// Auto-resize textarea
function autoResizeTextarea() {
    messageInput.style.height = 'auto';
    messageInput.style.height = messageInput.scrollHeight + 'px';
}

// Setup offline/online detection
function setupOfflineDetection() {
    console.log('[Main] Setting up offline/online detection...');

    window.addEventListener('online', async () => {
        console.log('[Main] Network connection restored');
        showError('Connection restored', 'success');
        const healthStatus = await checkServerHealth();
        updateStatus(healthStatus.message, healthStatus.isOnline);
    });

    window.addEventListener('offline', () => {
        console.log('[Main] Network connection lost');
        updateStatus('Offline', false);
        showError('No internet connection. Please check your network.');
    });
}

// Initialize on DOM content loaded
console.log('[Main] Waiting for DOMContentLoaded...');
document.addEventListener('DOMContentLoaded', initializeApp);
