import { API_BASE_URL } from '../config.js';
import { showError } from './ui.js';
import { addMessage, clearConversationHistory, setConversationHistory } from './messaging.js';

let sessionManager = null;
let sidebar, sessionList, sidebarToggle, newChatButton;
let chatMessages;

function initializeSessionElements(elements, manager) {
    sidebar = elements.sidebar;
    sessionList = elements.sessionList;
    sidebarToggle = elements.sidebarToggle;
    newChatButton = elements.newChatButton;
    chatMessages = elements.chatMessages;
    sessionManager = manager;
}

// Initialize sessions
async function initializeSessions(createNewChatFn) {
    try {
        await loadSessions();

        if (!sessionManager.getCurrentSessionId()) {
            await createNewChatFn();
        }
    } catch (error) {
        console.error('Failed to initialize sessions:', error);
        showError('Failed to load chat history');
    }
}

// Load all sessions from backend
async function loadSessions() {
    try {
        const sessions = await sessionManager.listSessions();
        renderSessions(sessions);
    } catch (error) {
        console.error('Failed to load sessions:', error);
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

        sessionItem.addEventListener('click', async (e) => {
            if (!e.target.closest('.session-delete')) {
                await loadSession(session.session_id);
            }
        });

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
async function loadSession(sessionId) {
    try {
        const sessionData = await sessionManager.getSession(sessionId, true);

        sessionManager.setCurrentSessionId(sessionId);

        chatMessages.innerHTML = '';
        clearConversationHistory();

        const history = [];
        if (sessionData.messages && sessionData.messages.length > 0) {
            sessionData.messages.forEach(msg => {
                addMessage(msg.content, msg.role === 'user' ? 'user' : 'bot');
                history.push({ role: msg.role, content: msg.content });
            });
        }
        setConversationHistory(history);

        // Dispatch event for document loading
        window.dispatchEvent(new CustomEvent('sessionLoaded', { detail: { sessionId } }));

        await loadSessions();
        closeSidebarOnMobile();

        console.log('Loaded session:', sessionId);
    } catch (error) {
        console.error('Failed to load session:', error);
        showError('Failed to load chat session');
    }
}

// Create a new chat session
async function createNewChat() {
    try {
        const session = await sessionManager.createSession('New Chat');

        chatMessages.innerHTML = '';
        clearConversationHistory();

        await loadSessions();
        closeSidebarOnMobile();

        console.log('Created new session:', session.session_id);
    } catch (error) {
        console.error('Failed to create new session:', error);
        showError('Failed to create new chat');
    }
}

// Delete session and update UI
async function deleteSessionAndUpdate(sessionId) {
    try {
        await sessionManager.deleteSession(sessionId);

        if (sessionManager.getCurrentSessionId() === sessionId) {
            await createNewChat();
        } else {
            await loadSessions();
        }
    } catch (error) {
        console.error('Failed to delete session:', error);
        showError('Failed to delete chat');
    }
}

// Toggle sidebar (mobile)
function toggleSidebar() {
    if (sidebar) {
        sidebar.classList.toggle('open');
    }
}

// Close sidebar on mobile
function closeSidebarOnMobile() {
    if (window.innerWidth <= 768 && sidebar) {
        sidebar.classList.remove('open');
    }
}

export {
    initializeSessionElements,
    initializeSessions,
    loadSessions,
    loadSession,
    createNewChat,
    deleteSessionAndUpdate,
    toggleSidebar,
    closeSidebarOnMobile
};
