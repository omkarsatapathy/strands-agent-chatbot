// API Configuration
const API_BASE_URL = window.location.origin;

// Configuration constants
const CONFIG = {
    MAX_RETRIES: 3,
    RETRY_DELAY: 1000, // ms
    REQUEST_TIMEOUT: 60000, // 60 seconds
    HEALTH_CHECK_INTERVAL: 30000, // 30 seconds
    MAX_CONVERSATION_HISTORY: 20,
    AUTO_RECONNECT: true
};

// DOM Elements
let chatMessages, messageInput, sendButton, clearButton, searchButton, statusText, statusDot, mouseIcon;

// Conversation history
let conversationHistory = [];

// State management
let healthCheckInterval = null;
let isOnline = false;
let requestInProgress = false;
let messageCount = 0;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    try {
        initializeDOMElements();
        checkServerHealth();
        setupEventListeners();
        autoResizeTextarea();
        startHealthCheckInterval();
        setupOfflineDetection();
        loadConversationHistory();
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

    if (!chatMessages || !messageInput || !sendButton || !statusText || !statusDot || !mouseIcon) {
        throw new Error('Required DOM elements not found');
    }
}

// Start periodic health checks
function startHealthCheckInterval() {
    if (healthCheckInterval) {
        clearInterval(healthCheckInterval);
    }
    healthCheckInterval = setInterval(checkServerHealth, CONFIG.HEALTH_CHECK_INTERVAL);
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
    if (clearButton) clearButton.addEventListener('click', clearChat);
    if (searchButton) searchButton.addEventListener('click', performWebSearch);
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

// Load conversation history from localStorage
function loadConversationHistory() {
    try {
        const saved = localStorage.getItem('conversationHistory');
        if (saved) {
            conversationHistory = JSON.parse(saved);
            console.log('Loaded conversation history:', conversationHistory.length, 'messages');
        }
    } catch (error) {
        console.error('Failed to load conversation history:', error);
    }
}

// Save conversation history to localStorage
function saveConversationHistory() {
    try {
        localStorage.setItem('conversationHistory', JSON.stringify(conversationHistory));
    } catch (error) {
        console.error('Failed to save conversation history:', error);
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

    requestInProgress = true;

    // Add user message to chat
    addMessage(message, 'user');
    conversationHistory.push({ role: 'user', content: message });
    saveConversationHistory();

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
                conversation_history: recentHistory
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

// Handle SSE stream events
function handleStreamEvent(eventType, eventData, statusId) {
    try {
        const data = JSON.parse(eventData);

        switch (eventType) {
            case 'connected':
                console.log('Connected to stream');
                updateStatusIndicator(statusId, '✅ Connected');
                break;

            case 'thinking':
                console.log('Agent thinking:', data.status);
                updateStatusIndicator(statusId, data.status);
                updateStatus(data.status, true);
                break;

            case 'tool':
                console.log('Tool called:', data);
                const toolStatus = `${data.status} (${data.tool_count}/${data.max_tools})`;
                updateStatusIndicator(statusId, toolStatus);
                updateStatus(data.status, true);
                break;

            case 'done':
                console.log('Stream done:', data);
                removeStatusIndicator(statusId);
                updateStatus(data.status, true);

                // Add response to chat
                if (data.response) {
                    addMessage(data.response, 'bot');
                    conversationHistory.push({ role: 'assistant', content: data.response });
                    saveConversationHistory();
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
        saveConversationHistory();

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

// Clear chat
function clearChat() {
    if (confirm('Are you sure you want to clear the chat?')) {
        try {
            chatMessages.innerHTML = '';
            conversationHistory = [];
            messageCount = 0;
            saveConversationHistory();
        } catch (error) {
            console.error('Failed to clear chat:', error);
            showError('Failed to clear chat. Please refresh the page.');
        }
    }
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (healthCheckInterval) {
        clearInterval(healthCheckInterval);
    }
});
