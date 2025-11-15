// API Configuration
const API_BASE_URL = 'http://localhost:8000';

// DOM Elements
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const clearButton = document.getElementById('clearButton');
const searchButton = document.getElementById('searchButton');
const statusText = document.querySelector('.status-text');
const statusDot = document.querySelector('.status-dot');

// Conversation history
let conversationHistory = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkServerHealth();
    setupEventListeners();
    autoResizeTextarea();
});

// Event Listeners
function setupEventListeners() {
    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    clearButton.addEventListener('click', clearChat);
    searchButton.addEventListener('click', performWebSearch);
    messageInput.addEventListener('input', autoResizeTextarea);
}

// Auto-resize textarea
function autoResizeTextarea() {
    messageInput.style.height = 'auto';
    messageInput.style.height = messageInput.scrollHeight + 'px';
}

// Check server health
async function checkServerHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/health`);
        if (response.ok) {
            updateStatus('Ready', true);
        } else {
            updateStatus('Server Error', false);
        }
    } catch (error) {
        updateStatus('Offline', false);
        console.error('Health check failed:', error);
    }
}

// Update status indicator
function updateStatus(text, isOnline) {
    statusText.textContent = text;
    statusDot.style.background = isOnline ? '#4ade80' : '#f87171';
}

// Send message with streaming support
async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;

    // Add user message to chat
    addMessage(message, 'user');
    conversationHistory.push({ role: 'user', content: message });

    // Clear input
    messageInput.value = '';
    autoResizeTextarea();

    // Disable send button
    sendButton.disabled = true;
    updateStatus('Generating...', true);

    // Show typing indicator
    const typingId = showTypingIndicator();

    // Get last 10 conversation pairs (20 messages: 10 user + 10 assistant)
    // Keep the most recent history to maintain context while limiting payload size
    const recentHistory = conversationHistory.slice(-20);

    try {
        const response = await fetch(`${API_BASE_URL}/api/chat`, {
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

        const data = await response.json();
        console.log('Received data:', data);

        // Remove typing indicator
        removeTypingIndicator(typingId);

        if (data.response) {
            console.log('Adding bot message:', data.response);
            addMessage(data.response, 'bot');
            conversationHistory.push({ role: 'assistant', content: data.response });
        } else {
            console.error('No response in data:', data);
            showError('No response received from server');
        }

    } catch (error) {
        removeTypingIndicator(typingId);
        showError('Failed to get response from server. Please try again.');
        console.error('Error:', error);
    } finally {
        sendButton.disabled = false;
        updateStatus('Ready', true);
    }
}

// Perform web search
async function performWebSearch() {
    const query = messageInput.value.trim();
    if (!query) {
        alert('Please enter a search query');
        return;
    }

    updateStatus('Searching...', true);
    sendButton.disabled = true;

    try {
        const response = await fetch(`${API_BASE_URL}/api/search`, {
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
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Format search results
        let resultsText = `Search results for "${query}":\n\n`;
        data.results.forEach((result, index) => {
            if (result.error) {
                resultsText += result.error;
            } else {
                resultsText += `${index + 1}. ${result.title}\n${result.snippet}\n${result.link}\n\n`;
            }
        });

        addMessage(query, 'user');
        addMessage(resultsText, 'bot');

        messageInput.value = '';
        autoResizeTextarea();

    } catch (error) {
        showError('Failed to perform search. Please try again.');
        console.error('Error:', error);
    } finally {
        sendButton.disabled = false;
        updateStatus('Ready', true);
    }
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

// Show typing indicator
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
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
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
        chatMessages.innerHTML = '';
        conversationHistory = [];

        // Add welcome message
        addMessage("Hello! I'm your AI assistant. How can I help you today?", 'bot');
    }
}
