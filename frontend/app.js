// API Configuration
const API_BASE_URL = window.location.origin;

// Configuration constants
const CONFIG = {
    MAX_RETRIES: 3,
    RETRY_DELAY: 1000, // ms
    REQUEST_TIMEOUT: 60000, // 60 seconds
    HEALTH_CHECK_INTERVAL: 30000, // 30 seconds
    MAX_CONVERSATION_HISTORY: 10,  // Limit to 10 messages (matches backend)
    AUTO_RECONNECT: true
};

// DOM Elements
let chatMessages, messageInput, sendButton, clearButton, searchButton, statusText, statusDot, mouseIcon;
let sidebar, sessionList, sidebarToggle, newChatButton;
let uploadButton, fileInput, documentArea, documentList;

// Conversation history
let conversationHistory = [];

// State management
let healthCheckInterval = null;
let isOnline = false;
let requestInProgress = false;
let messageCount = 0;

// Session management
let sessionManager = null;

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    try {
        initializeDOMElements();
        checkServerHealth();
        setupEventListeners();
        autoResizeTextarea();
        startHealthCheckInterval();
        setupOfflineDetection();

        // Initialize session manager
        sessionManager = new SessionManager(API_BASE_URL);

        // Load sessions and create new session if none exists
        await initializeSessions();
    } catch (error) {
        console.error('Initialization error:', error);
        showError('Failed to initialize application. Please refresh the page.');
    }
});

// Initialize DOM elements with error handling
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

// Start periodic health checks
function startHealthCheckInterval() {
    // Disabled periodic health checks to reduce server load
    // Health check will only run on page load and when network status changes
    if (healthCheckInterval) {
        clearInterval(healthCheckInterval);
        healthCheckInterval = null;
    }
}

// Setup offline/online detection
function setupOfflineDetection() {
    window.addEventListener('online', () => {
        console.log('Network connection restored');
        showError('Connection restored', 'success');
        checkServerHealth();
    });

    window.addEventListener('offline', () => {
        console.log('Network connection lost');
        updateStatus('Offline', false);
        showError('No internet connection. Please check your network.');
    });
}

// Event Listeners
function setupEventListeners() {
    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    if (clearButton) clearButton.addEventListener('click', createNewChat);
    if (searchButton) searchButton.addEventListener('click', performWebSearch);
    if (newChatButton) newChatButton.addEventListener('click', createNewChat);
    if (sidebarToggle) sidebarToggle.addEventListener('click', toggleSidebar);
    if (uploadButton) uploadButton.addEventListener('click', () => fileInput.click());
    if (fileInput) fileInput.addEventListener('change', handleFileUpload);
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
}

// Auto-resize textarea
function autoResizeTextarea() {
    messageInput.style.height = 'auto';
    messageInput.style.height = messageInput.scrollHeight + 'px';
}

// ============= Session Management Functions =============

// Initialize sessions
async function initializeSessions() {
    try {
        await loadSessions();

        // Create a new session if none exists
        if (!sessionManager.getCurrentSessionId()) {
            await createNewChat();
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
async function loadSession(sessionId) {
    try {
        const sessionData = await sessionManager.getSession(sessionId, true);

        // Set as current session
        sessionManager.setCurrentSessionId(sessionId);

        // Clear chat display
        chatMessages.innerHTML = '';
        conversationHistory = [];

        // Load messages
        if (sessionData.messages && sessionData.messages.length > 0) {
            sessionData.messages.forEach(msg => {
                addMessage(msg.content, msg.role === 'user' ? 'user' : 'bot');
                conversationHistory.push({ role: msg.role, content: msg.content });
            });
        }

        // Load documents for this session
        await loadSessionDocuments(sessionId);

        // Update UI
        await loadSessions(); // Refresh sidebar to show active session
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
        // Create new session
        const session = await sessionManager.createSession('New Chat');

        // Clear current chat
        chatMessages.innerHTML = '';
        conversationHistory = [];

        // Reload sessions
        await loadSessions();

        // Close sidebar on mobile
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

        // If deleted session was active, create new one
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

// Fetch with timeout
async function fetchWithTimeout(url, options, timeout = CONFIG.REQUEST_TIMEOUT) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
        const response = await fetch(url, {
            ...options,
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        return response;
    } catch (error) {
        clearTimeout(timeoutId);
        if (error.name === 'AbortError') {
            throw new Error('Request timeout - server took too long to respond');
        }
        throw error;
    }
}

// Retry logic for failed requests
async function fetchWithRetry(url, options, retries = CONFIG.MAX_RETRIES) {
    let lastError;

    for (let i = 0; i < retries; i++) {
        try {
            if (i > 0) {
                console.log(`Retry attempt ${i + 1}/${retries}`);
                updateStatus(`Retrying (${i + 1}/${retries})...`, true);
                await sleep(CONFIG.RETRY_DELAY * i); // Exponential backoff
            }

            const response = await fetchWithTimeout(url, options);
            return response;
        } catch (error) {
            lastError = error;
            console.error(`Request failed (attempt ${i + 1}/${retries}):`, error);

            // Don't retry on certain errors
            if (error.message.includes('404') || error.message.includes('401')) {
                throw error;
            }
        }
    }

    throw lastError || new Error('Request failed after retries');
}

// Sleep utility
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Check server health
async function checkServerHealth() {
    try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/api/health`, {}, 5000);
        if (response.ok) {
            isOnline = true;
            updateStatus('Ready', true);
        } else {
            isOnline = false;
            updateStatus('Server Error', false);
        }
    } catch (error) {
        isOnline = false;
        updateStatus('Offline', false);
        console.error('Health check failed:', error);
    }
}

// Update status indicator
function updateStatus(text, isOnline) {
    statusText.textContent = text;
    statusDot.style.background = isOnline ? '#4ade80' : '#f87171';
}

// Send message with SSE streaming support
async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;

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

    // Check server health
    if (!isOnline) {
        showError('Server is offline. Please wait and try again.');
        return;
    }

    // Ensure we have a session
    if (!sessionManager || !sessionManager.getCurrentSessionId()) {
        console.error('No active session');
        showError('No active session. Creating new session...');
        try {
            await createNewChat();
        } catch (error) {
            console.error('Failed to create session:', error);
            showError('Failed to create session. Please refresh the page.');
            return;
        }
    }

    requestInProgress = true;

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
            await loadSessions(); // Refresh sidebar
        }
    } catch (error) {
        console.error('Failed to save user message:', error);
    }

    // Clear input
    messageInput.value = '';
    autoResizeTextarea();

    // Disable send button
    sendButton.disabled = true;
    updateStatus('Generating...', true);

    // Show status indicator (replace typing animation)
    const statusId = showStatusIndicator('⏳ Agent is thinking...');

    // Get last conversation pairs (limit to MAX_CONVERSATION_HISTORY)
    const recentHistory = conversationHistory.slice(-CONFIG.MAX_CONVERSATION_HISTORY);

    try {
        console.log('Starting SSE stream to:', `${API_BASE_URL}/api/chat/stream`);

        const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                conversation_history: recentHistory,
                session_id: sessionManager.getCurrentSessionId()
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
                        handleStreamEvent(eventType, eventData, statusId);
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
            saveConversationHistory();
        }
    } finally {
        sendButton.disabled = false;
        requestInProgress = false;
        updateStatus('Ready', true);
    }
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

                // Add response to chat
                if (data.response) {
                    addMessage(data.response, 'bot');
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

// Perform web search
async function performWebSearch() {
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
                await loadSessions();
            }
        } catch (error) {
            console.error('Failed to save search messages:', error);
        }

        messageInput.value = '';
        autoResizeTextarea();

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
function addMessage(text, sender) {
    console.log('addMessage called with:', text.substring(0, 100));

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const textElement = document.createElement('div');

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
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);

    // Increment message count
    messageCount++;

    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Create streaming message container
function createStreamingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot-message';
    messageDiv.id = 'streaming-message-' + Date.now();

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const textElement = document.createElement('p');
    textElement.style.whiteSpace = 'pre-wrap';
    textElement.className = 'streaming-text';

    // Add initial cursor
    const cursor = document.createElement('span');
    cursor.className = 'streaming-cursor';
    cursor.textContent = '▋';

    textElement.appendChild(cursor);

    contentDiv.appendChild(textElement);
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);

    chatMessages.scrollTop = chatMessages.scrollHeight;

    console.log('Created streaming message:', messageDiv.id);
    return messageDiv.id;
}

// Update streaming message
function updateStreamingMessage(id, text) {
    const messageDiv = document.getElementById(id);
    if (!messageDiv) {
        console.error('Streaming message not found:', id);
        return;
    }

    const textElement = messageDiv.querySelector('p.streaming-text');
    if (textElement) {
        // Create text node + cursor
        textElement.innerHTML = '';

        // Add the text
        const textNode = document.createTextNode(text);
        textElement.appendChild(textNode);

        // Re-add cursor
        const cursor = document.createElement('span');
        cursor.className = 'streaming-cursor';
        cursor.textContent = '▋';
        textElement.appendChild(cursor);

        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// Finalize streaming message (remove cursor)
function finalizeStreamingMessage(id) {
    console.log('Finalizing streaming message:', id);
    const messageDiv = document.getElementById(id);
    if (messageDiv) {
        const cursor = messageDiv.querySelector('.streaming-cursor');
        if (cursor) {
            cursor.remove();
            console.log('Cursor removed');
        }
    }
}

// Remove streaming message
function removeStreamingMessage(id) {
    const messageDiv = document.getElementById(id);
    if (messageDiv) {
        messageDiv.remove();
    }
}

// Show status indicator (replaces typing indicator)
function showStatusIndicator(statusText) {
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
function updateStatusIndicator(id, statusText) {
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
function removeStatusIndicator(id) {
    const indicator = document.getElementById(id);
    if (indicator) {
        indicator.remove();
    }
}

// Show typing indicator (kept for backward compatibility)
function showTypingIndicator() {
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
function removeTypingIndicator(id) {
    const indicator = document.getElementById(id);
    if (indicator) {
        indicator.remove();
    }
}

// Show error message
function showError(message, type = 'error') {
    const errorDiv = document.createElement('div');
    errorDiv.className = type === 'success' ? 'success-message' : 'error-message';
    errorDiv.textContent = message;

    chatMessages.appendChild(errorDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    setTimeout(() => {
        errorDiv.remove();
    }, 5000);
}

// Clear chat is now handled by createNewChat function

// ============= Document Upload Functions =============

// Handle file upload
async function handleFileUpload(event) {
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
        showError('No active session. Creating new session...');
        await createNewChat();
        // Retry upload after session creation
        setTimeout(() => handleFileUpload(event), 500);
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

        // Display documents
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
                console.error('Error opening folder:', error);
                showToast(`File location: ${doc.file_path}`, 'success');
            }
        });

        documentList.appendChild(docItem);
    });
}

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Show toast notification
function showToast(message, type = 'success') {
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast-notification ${type}`;

    const icon = type === 'success' ? '✅' : '❌';

    toast.innerHTML = `
        <div class="toast-icon">${icon}</div>
        <div class="toast-content">${message}</div>
        <button class="toast-close">OK</button>
    `;

    document.body.appendChild(toast);

    // Close button handler
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

    // Auto-dismiss after 3 seconds
    setTimeout(closeToast, 3000);
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (healthCheckInterval) {
        clearInterval(healthCheckInterval);
    }
});
