import { API_BASE_URL } from './config.js';
import { checkServerHealth } from './modules/api.js';
import { initializeUIElements, updateStatus, showError } from './modules/ui.js';
import { initializeMessagingElements, sendMessage, performWebSearch } from './modules/messaging.js';
import { initializeSessionElements, initializeSessions, loadSessions, toggleSidebar, createNewChat } from './modules/session.js';
import { initializeDocumentElements, handleFileUpload, loadSessionDocuments } from './modules/document.js';

// Import SessionManager (non-module script)
const SessionManager = window.SessionManager;

// DOM Elements
let chatMessages, messageInput, sendButton, clearButton, searchButton, statusText, statusDot, mouseIcon;
let sidebar, sessionList, sidebarToggle, newChatButton;
let uploadButton, fileInput, documentArea, documentList;

// State management
let isOnline = false;
let sessionManager = null;

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', async () => {
    console.log('🚀 Application starting...');
    try {
        console.log('1. Initializing DOM elements...');
        initializeDOMElements();

        console.log('2. Checking server health...');
        const healthResult = await checkServerHealth();
        isOnline = healthResult.isOnline;
        updateStatus(healthResult.status, healthResult.isOnline);
        console.log('   Server status:', healthResult);

        console.log('3. Setting up event listeners...');
        setupEventListeners();
        autoResizeTextarea();
        setupOfflineDetection();

        console.log('4. Initializing session manager...');
        sessionManager = new SessionManager(API_BASE_URL);
        console.log('   SessionManager created');

        console.log('5. Initializing module elements...');
        initializeUIElements({ statusText, statusDot, chatMessages });
        initializeMessagingElements({ chatMessages, messageInput, sendButton, searchButton }, sessionManager);
        initializeSessionElements({ sidebar, sessionList, sidebarToggle, newChatButton, chatMessages }, sessionManager);
        initializeDocumentElements({ uploadButton, fileInput, documentArea, documentList }, sessionManager);

        console.log('6. Loading sessions...');
        await initializeSessions(createNewChat);
        console.log('✅ Application initialized successfully!');
    } catch (error) {
        console.error('❌ Initialization error:', error);
        console.error('Stack trace:', error.stack);
        alert('Failed to initialize application: ' + error.message + '\n\nCheck console for details.');
    }
});

// Initialize DOM elements
function initializeDOMElements() {
    chatMessages = document.getElementById('chatMessages');
    messageInput = document.getElementById('messageInput');
    sendButton = document.getElementById('sendButton');
    clearButton = document.getElementById('clearButton');
    searchButton = document.getElementById('searchButton');
    statusText = document.querySelector('.status-text');
    statusDot = document.querySelector('.status-dot');
    mouseIcon = document.getElementById('mouseIcon');
    sidebar = document.getElementById('sidebar');
    sessionList = document.getElementById('sessionList');
    sidebarToggle = document.getElementById('sidebarToggle');
    newChatButton = document.getElementById('newChatButton');
    uploadButton = document.getElementById('uploadButton');
    fileInput = document.getElementById('fileInput');
    documentArea = document.getElementById('documentArea');
    documentList = document.getElementById('documentList');

    if (!chatMessages || !messageInput || !sendButton || !statusText || !statusDot || !mouseIcon) {
        throw new Error('Required DOM elements not found');
    }
}

// Setup offline/online detection
function setupOfflineDetection() {
    window.addEventListener('online', async () => {
        console.log('Network connection restored');
        showError('Connection restored', 'success');
        const healthResult = await checkServerHealth();
        isOnline = healthResult.isOnline;
        updateStatus(healthResult.status, healthResult.isOnline);
    });

    window.addEventListener('offline', () => {
        console.log('Network connection lost');
        isOnline = false;
        updateStatus('Offline', false);
        showError('No internet connection. Please check your network.');
    });
}

// Event Listeners
function setupEventListeners() {
    sendButton.addEventListener('click', () => sendMessage(isOnline, loadSessions));
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage(isOnline, loadSessions);
        }
    });
    if (clearButton) clearButton.addEventListener('click', createNewChat);
    if (searchButton) searchButton.addEventListener('click', performWebSearch);
    if (newChatButton) newChatButton.addEventListener('click', createNewChat);
    if (sidebarToggle) sidebarToggle.addEventListener('click', toggleSidebar);
    if (uploadButton) uploadButton.addEventListener('click', () => fileInput.click());
    if (fileInput) fileInput.addEventListener('change', (e) => handleFileUpload(e, createNewChat));
    messageInput.addEventListener('input', autoResizeTextarea);

    // Listen for session loaded events to load documents
    window.addEventListener('sessionLoaded', async (e) => {
        const { sessionId } = e.detail;
        await loadSessionDocuments(sessionId);
    });

    // Prevent zoom on double-tap for iOS
    messageInput.addEventListener('touchend', (e) => {
        const now = new Date().getTime();
        const lastTap = messageInput.dataset.lastTap || 0;
        if (now - lastTap < 300) {
            e.preventDefault();
        }
        messageInput.dataset.lastTap = now;
    });
}

// Auto-resize textarea
function autoResizeTextarea() {
    messageInput.style.height = 'auto';
    messageInput.style.height = messageInput.scrollHeight + 'px';
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    // Any cleanup needed
});
