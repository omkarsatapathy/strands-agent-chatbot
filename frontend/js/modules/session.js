// Session Management Functions
import { API_BASE_URL } from '../config.js';
import { showError } from './ui.js';
import { addMessage, clearConversationHistory, setConversationHistory } from './messaging.js';

// DOM Elements
let sidebar, sessionList, sidebarToggle, newChatButton;

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

    if (!sidebar || !sessionList) {
        throw new Error('Required session elements not found');
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
        await loadSessions();

        // Create a new session if none exists
        if (!sessionManager.getCurrentSessionId()) {
            console.log('[Session] No active session, creating new one...');
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
        sessionList.innerHTML = '<div style="padding: 20px; text-align: center; color: #8696a0; font-size: 14px;">No chat history yet</div>';
        return;
    }

    sessions.forEach(session => {
        const sessionItem = document.createElement('div');
        sessionItem.className = 'session-item';
        if (session.session_id === sessionManager.getCurrentSessionId()) {
            sessionItem.classList.add('active');
        }

        sessionItem.innerHTML = `
            <div style="flex: 1; min-width: 0;">
                <div class="session-title">${session.title}</div>
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
            if (!e.target.closest('.session-delete')) {
                await loadSession(session.session_id);
            }
        });

        // Delete button
        const deleteBtn = sessionItem.querySelector('.session-delete');
        deleteBtn.addEventListener('click', async (e) => {
            e.stopPropagation();
            if (confirm('Delete this chat?')) {
                await deleteSessionAndUpdate(session.session_id);
            }
        });

        sessionList.appendChild(sessionItem);
    });
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

// Create a new chat session
export async function createNewChat() {
    console.log('[Session] Creating new chat...');
    try {
        // Create new session
        const session = await sessionManager.createSession('New Chat');

        // Clear current chat
        if (chatMessages) {
            chatMessages.innerHTML = '';
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

// Toggle sidebar (mobile)
export function toggleSidebar() {
    if (sidebar) {
        sidebar.classList.toggle('open');
    }
}

// Close sidebar on mobile
export function closeSidebarOnMobile() {
    if (window.innerWidth <= 768 && sidebar) {
        sidebar.classList.remove('open');
    }
}
