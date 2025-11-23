// Session Management Functions
import { API_BASE_URL } from '../config.js';
import { showError } from './ui.js';
import { addMessage, clearConversationHistory, setConversationHistory } from './messaging.js';

// DOM Elements
let sidebar, sessionList, sidebarToggle, newChatButton, sidebarOverlay;

// Session manager instance
let sessionManager = null;

// Chat messages reference
let chatMessages = null;

// Initialize session elements
export function initializeSessionElements() {
    sidebar = document.getElementById('sidebar');
    sessionList = document.getElementById('sessionList');
    sidebarToggle = document.getElementById('sidebarToggle');
    newChatButton = document.getElementById('newChatButton');
    chatMessages = document.getElementById('chatMessages');
    sidebarOverlay = document.getElementById('sidebarOverlay');

    if (!sidebar || !sessionList) {
        throw new Error('Required session elements not found');
    }

    // Add overlay click listener to close sidebar
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', closeSidebar);
    }

    return { sidebar, sessionList, sidebarToggle, newChatButton };
}

// Set session manager reference
export function setSessionManager(manager) {
    sessionManager = manager;
}

// Initialize sessions
export async function initializeSessions() {
    console.log('[Session] Initializing sessions...');
    try {
        const sessions = await sessionManager.listSessions();
        console.log('[Session] Loaded sessions:', sessions.length);
        renderSessions(sessions);

        // If there are existing sessions, load the most recent one
        if (sessions.length > 0) {
            console.log('[Session] Loading most recent session...');
            await loadSession(sessions[0].session_id);
        } else {
            // Only create a new session if no sessions exist at all
            console.log('[Session] No existing sessions, creating new one...');
            await createNewChat();
        }
    } catch (error) {
        console.error('[Session] Failed to initialize sessions:', error);
        showError('Failed to load chat history');
    }
}

// Load all sessions from backend
export async function loadSessions() {
    console.log('[Session] Loading sessions from backend...');
    try {
        const sessions = await sessionManager.listSessions();
        console.log('[Session] Loaded sessions:', sessions.length);
        renderSessions(sessions);
    } catch (error) {
        console.error('[Session] Failed to load sessions:', error);
    }
}

// Render sessions in sidebar
function renderSessions(sessions) {
    if (!sessionList) return;

    sessionList.innerHTML = '';

    if (sessions.length === 0) {
        sessionList.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-tertiary); font-size: 14px;">No chat history yet</div>';
        return;
    }

    sessions.forEach(session => {
        const sessionItem = document.createElement('div');
        sessionItem.className = 'session-item';
        sessionItem.dataset.sessionId = session.session_id;
        if (session.session_id === sessionManager.getCurrentSessionId()) {
            sessionItem.classList.add('active');
        }

        sessionItem.innerHTML = `
            <div class="session-info">
                <div class="session-title">${escapeHtml(session.title)}</div>
                <div class="session-date">${sessionManager.formatDate(session.updated_at)}</div>
            </div>
            <button class="session-delete" title="Delete chat">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"></path>
                </svg>
            </button>
        `;

        // Click to load session
        sessionItem.addEventListener('click', async (e) => {
            if (!e.target.closest('.session-delete') && !e.target.closest('.delete-confirm')) {
                await loadSession(session.session_id);
            }
        });

        // Delete button - show inline confirmation
        const deleteBtn = sessionItem.querySelector('.session-delete');
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            showDeleteConfirmation(sessionItem, session.session_id);
        });

        sessionList.appendChild(sessionItem);
    });
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Show inline delete confirmation
function showDeleteConfirmation(sessionItem, sessionId) {
    // Remove any existing confirmations
    const existingConfirm = document.querySelector('.session-item.deleting');
    if (existingConfirm && existingConfirm !== sessionItem) {
        resetSessionItem(existingConfirm);
    }

    // If already showing confirmation, reset it
    if (sessionItem.classList.contains('deleting')) {
        resetSessionItem(sessionItem);
        return;
    }

    // Store original content
    const originalContent = sessionItem.innerHTML;
    sessionItem.dataset.originalContent = originalContent;
    sessionItem.classList.add('deleting');

    // Show confirmation UI
    sessionItem.innerHTML = `
        <div class="delete-confirm">
            <span class="delete-confirm-text">Delete?</span>
            <button class="delete-confirm-btn confirm">Delete</button>
            <button class="delete-confirm-btn cancel">Cancel</button>
        </div>
    `;

    // Handle confirm click
    const confirmBtn = sessionItem.querySelector('.delete-confirm-btn.confirm');
    confirmBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        await deleteSessionAndUpdate(sessionId);
    });

    // Handle cancel click
    const cancelBtn = sessionItem.querySelector('.delete-confirm-btn.cancel');
    cancelBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        resetSessionItem(sessionItem);
    });

    // Auto-cancel after 5 seconds
    setTimeout(() => {
        if (sessionItem.classList.contains('deleting')) {
            resetSessionItem(sessionItem);
        }
    }, 5000);
}

// Reset session item to original state
function resetSessionItem(sessionItem) {
    if (sessionItem.dataset.originalContent) {
        sessionItem.innerHTML = sessionItem.dataset.originalContent;
        sessionItem.classList.remove('deleting');
        delete sessionItem.dataset.originalContent;

        // Re-attach event listeners
        const sessionId = sessionItem.dataset.sessionId;
        const deleteBtn = sessionItem.querySelector('.session-delete');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                showDeleteConfirmation(sessionItem, sessionId);
            });
        }
    }
}

// Load a specific session
export async function loadSession(sessionId) {
    console.log('[Session] Loading session:', sessionId);
    try {
        const sessionData = await sessionManager.getSession(sessionId, true);

        // Set as current session
        sessionManager.setCurrentSessionId(sessionId);

        // Clear chat display
        if (chatMessages) {
            chatMessages.innerHTML = '';
        }
        clearConversationHistory();

        // Load messages
        const conversationHistory = [];
        if (sessionData.messages && sessionData.messages.length > 0) {
            sessionData.messages.forEach(msg => {
                addMessage(msg.content, msg.role === 'user' ? 'user' : 'bot');
                conversationHistory.push({ role: msg.role, content: msg.content });
            });
        } else {
            // Show welcome placeholder for empty sessions
            const welcomeDiv = document.createElement('div');
            welcomeDiv.className = 'chat-welcome';
            welcomeDiv.id = 'chatWelcome';
            welcomeDiv.innerHTML = `
                <img src="/static/logo/logo.png" alt="Logo" class="chat-welcome-logo">
                <h2 class="chat-welcome-title">How can I help you today?</h2>
            `;
            chatMessages.appendChild(welcomeDiv);
        }
        setConversationHistory(conversationHistory);

        // Update UI
        await loadSessions(); // Refresh sidebar to show active session
        closeSidebarOnMobile();

        console.log('[Session] Session loaded successfully:', sessionId);

        // Dispatch custom event to notify that session has been loaded
        window.dispatchEvent(new CustomEvent('sessionLoaded', {
            detail: { sessionId }
        }));

    } catch (error) {
        console.error('[Session] Failed to load session:', error);
        showError('Failed to load chat session');
    }
}

// Check if current session is blank (no messages)
async function isCurrentSessionBlank() {
    const currentSessionId = sessionManager.getCurrentSessionId();
    if (!currentSessionId) return false;

    try {
        const sessionData = await sessionManager.getSession(currentSessionId, true);
        return !sessionData.messages || sessionData.messages.length === 0;
    } catch (error) {
        return false;
    }
}

// Create a new chat session
export async function createNewChat() {
    console.log('[Session] Creating new chat...');

    // Check if current session is already blank - don't create another
    const isBlank = await isCurrentSessionBlank();
    if (isBlank) {
        console.log('[Session] Current session is already blank, not creating new one');
        return;
    }

    try {
        // Create new session
        const session = await sessionManager.createSession('New Chat');

        // Clear current chat
        if (chatMessages) {
            chatMessages.innerHTML = '';
            // Re-add the welcome placeholder
            const welcomeDiv = document.createElement('div');
            welcomeDiv.className = 'chat-welcome';
            welcomeDiv.id = 'chatWelcome';
            welcomeDiv.innerHTML = `
                <img src="/static/logo/logo.png" alt="Logo" class="chat-welcome-logo">
                <h2 class="chat-welcome-title">How can I help you today?</h2>
            `;
            chatMessages.appendChild(welcomeDiv);
        }
        clearConversationHistory();

        // Reload sessions
        await loadSessions();

        // Close sidebar on mobile
        closeSidebarOnMobile();

        console.log('[Session] Created new session:', session.session_id);

        // Dispatch custom event to notify that session has been loaded
        window.dispatchEvent(new CustomEvent('sessionLoaded', {
            detail: { sessionId: session.session_id }
        }));

    } catch (error) {
        console.error('[Session] Failed to create new session:', error);
        showError('Failed to create new chat');
    }
}

// Delete session and update UI
export async function deleteSessionAndUpdate(sessionId) {
    console.log('[Session] Deleting session:', sessionId);
    try {
        await sessionManager.deleteSession(sessionId);

        // If deleted session was active, create new one
        if (sessionManager.getCurrentSessionId() === sessionId) {
            await createNewChat();
        } else {
            await loadSessions();
        }
    } catch (error) {
        console.error('[Session] Failed to delete session:', error);
        showError('Failed to delete chat');
    }
}

// Toggle sidebar (mobile/tablet)
export function toggleSidebar() {
    if (sidebar) {
        const isOpen = sidebar.classList.toggle('open');
        // Also toggle overlay
        if (sidebarOverlay) {
            sidebarOverlay.classList.toggle('show', isOpen);
        }
    }
}

// Close sidebar
export function closeSidebar() {
    if (sidebar) {
        sidebar.classList.remove('open');
    }
    if (sidebarOverlay) {
        sidebarOverlay.classList.remove('show');
    }
}

// Close sidebar on mobile/tablet (screens <= 1024px)
export function closeSidebarOnMobile() {
    if (window.innerWidth <= 1024 && sidebar) {
        closeSidebar();
    }
}
