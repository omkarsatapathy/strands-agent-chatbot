import { API_BASE_URL, CONFIG } from '../config.js';
import { fetchWithRetry } from './api.js';
import { updateStatus, showError, showStatusIndicator, updateStatusIndicator, removeStatusIndicator, showTypingIndicator, removeTypingIndicator } from './ui.js';

// Conversation history
let conversationHistory = [];
let chatMessages, messageInput, sendButton, searchButton;
let requestInProgress = false;
let sessionManager = null;

// Track last status update time for minimum display duration
let lastStatusUpdateTime = 0;
let statusUpdateQueue = [];
let isProcessingStatusQueue = false;

function initializeMessagingElements(elements, manager) {
    chatMessages = elements.chatMessages;
    messageInput = elements.messageInput;
    sendButton = elements.sendButton;
    searchButton = elements.searchButton;
    sessionManager = manager;
}

function getConversationHistory() {
    return conversationHistory;
}

function setConversationHistory(history) {
    conversationHistory = history;
}

function clearConversationHistory() {
    conversationHistory = [];
}

// Convert markdown tables to HTML
function convertMarkdownTables(text) {
    const lines = text.split('\n');
    let result = [];
    let inTable = false;
    let tableRows = [];

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();

        if (line.startsWith('|') && line.endsWith('|')) {
            if (/^\|[\s\-|]+\|$/.test(line)) {
                continue;
            }

            if (!inTable) {
                inTable = true;
                tableRows = [];
            }

            const cells = line.split('|').slice(1, -1).map(cell => cell.trim());
            tableRows.push(cells);
        } else {
            if (inTable) {
                result.push(convertTableToHTML(tableRows));
                tableRows = [];
                inTable = false;
            }
            result.push(line);
        }
    }

    if (inTable && tableRows.length > 0) {
        result.push(convertTableToHTML(tableRows));
    }

    return result.join('\n');
}

function convertTableToHTML(rows) {
    if (rows.length === 0) return '';

    let html = '<table class="markdown-table">';

    html += '<thead><tr>';
    for (const cell of rows[0]) {
        html += `<th>${cell}</th>`;
    }
    html += '</tr></thead>';

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
    if (!chatMessages) return;

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const textElement = document.createElement('div');

    let formattedText = text;
    formattedText = convertMarkdownTables(formattedText);
    formattedText = formattedText.replace(/^## (.+)$/gm, '<h3>$1</h3>');
    formattedText = formattedText.replace(/^### (.+)$/gm, '<h4>$1</h4>');
    formattedText = formattedText.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    formattedText = formattedText.replace(/\n/g, '<br>');

    textElement.innerHTML = formattedText;
    textElement.style.whiteSpace = 'pre-wrap';

    contentDiv.appendChild(textElement);
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);

    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Process status updates with minimum display time
async function processStatusUpdate(statusId, statusText) {
    const now = Date.now();
    const timeSinceLastUpdate = now - lastStatusUpdateTime;
    const minDisplayTime = 1500; // 1.5 seconds

    if (timeSinceLastUpdate < minDisplayTime) {
        await new Promise(resolve => setTimeout(resolve, minDisplayTime - timeSinceLastUpdate));
    }

    updateStatusIndicator(statusId, statusText);
    lastStatusUpdateTime = Date.now();
}

// Queue status updates
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

                if (data.response) {
                    addMessage(data.response, 'bot');
                    conversationHistory.push({ role: 'assistant', content: data.response });

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

// Send message with SSE streaming
async function sendMessage(isOnline, loadSessions) {
    const message = messageInput.value.trim();
    if (!message || requestInProgress) return;

    if (!navigator.onLine) {
        showError('No internet connection. Please check your network.');
        return;
    }

    if (!isOnline) {
        showError('Server is offline. Please wait and try again.');
        return;
    }

    if (!sessionManager || !sessionManager.getCurrentSessionId()) {
        console.error('No active session');
        showError('No active session. Creating new session...');
        return;
    }

    requestInProgress = true;

    addMessage(message, 'user');
    conversationHistory.push({ role: 'user', content: message });

    try {
        await sessionManager.saveMessage('user', message);

        if (conversationHistory.length === 1) {
            const title = sessionManager.generateSessionTitle(message);
            await fetch(`${API_BASE_URL}/api/sessions/${sessionManager.getCurrentSessionId()}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title })
            });
            await loadSessions();
        }
    } catch (error) {
        console.error('Failed to save user message:', error);
    }

    messageInput.value = '';
    sendButton.disabled = true;
    updateStatus('Generating...', true);

    const statusId = showStatusIndicator('⏳ Agent is thinking...');
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

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();

            if (done) {
                console.log('Stream complete');
                break;
            }

            buffer += decoder.decode(value, { stream: true });

            const lines = buffer.split('\n');
            buffer = lines.pop();

            let eventType = 'message';
            let eventData = '';

            for (const line of lines) {
                if (line.startsWith('event:')) {
                    eventType = line.substring(6).trim();
                } else if (line.startsWith('data:')) {
                    eventData = line.substring(5).trim();
                } else if (line === '') {
                    if (eventData) {
                        handleStreamEvent(eventType, eventData, statusId);
                        eventData = '';
                        eventType = 'message';
                    }
                } else if (line.startsWith(':')) {
                    continue;
                }
            }
        }

    } catch (error) {
        removeStatusIndicator(statusId);

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

        if (conversationHistory.length > 0 && conversationHistory[conversationHistory.length - 1].role === 'user') {
            conversationHistory.pop();
        }
    } finally {
        sendButton.disabled = false;
        requestInProgress = false;
        updateStatus('Ready', true);
    }
}

// Perform web search
async function performWebSearch() {
    const query = messageInput.value.trim();
    if (!query || requestInProgress) {
        if (!query) showError('Please enter a search query');
        return;
    }

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

        try {
            await sessionManager.saveMessage('user', query);
            await sessionManager.saveMessage('assistant', resultsText);
        } catch (error) {
            console.error('Failed to save search messages:', error);
        }

        messageInput.value = '';

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

export {
    initializeMessagingElements,
    getConversationHistory,
    setConversationHistory,
    clearConversationHistory,
    addMessage,
    sendMessage,
    performWebSearch
};
