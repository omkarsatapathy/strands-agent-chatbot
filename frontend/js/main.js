// Main Entry Point
import { API_BASE_URL, checkSetupStatus, IS_SETUP_DONE } from './config.js';
import { initializeSetup } from './setup.js';
import { checkServerHealth, getModelProviders, getResponseStyles } from './modules/api.js';
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
let modelProviderSelect, responseStyleSelect, styleToggleBtn, styleDropdown, themeToggle;

// Initialize model providers dropdown
async function initializeModelProviders() {
    try {
        const data = await getModelProviders();
        const providers = data.providers || [];
        const defaultProvider = data.default;

        if (!modelProviderSelect) {
            console.error('Model provider select element not found');
            return;
        }

        // Clear existing options
        modelProviderSelect.innerHTML = '';

        if (providers.length === 0) {
            modelProviderSelect.innerHTML = '<option value="">No providers available</option>';
            modelProviderSelect.disabled = true;
            return;
        }

        // Store providers data globally
        providersData = providers;

        // Add available providers
        providers.forEach(provider => {
            const option = document.createElement('option');
            option.value = provider.name;
            option.textContent = provider.display_name;
            option.dataset.available = provider.available ? 'true' : 'false';

            // Don't disable LlamaCPP models - allow clicking to trigger download wizard
            // Only disable non-downloadable providers
            if (!provider.available && !MODEL_CONFIGS[provider.name]) {
                option.disabled = true;
            }

            if (!provider.available) {
                option.textContent += ' (Not configured)';
                option.style.color = '#9ca3af';  // Gray out unavailable options
            }

            if (provider.name === defaultProvider) {
                option.selected = true;
            }

            modelProviderSelect.appendChild(option);
        });

        // Handle click on disabled options - intercept mousedown on select
        modelProviderSelect.addEventListener('mousedown', (e) => {
            // Store the currently selected value before any change
            modelProviderSelect.dataset.previousValue = modelProviderSelect.value;
        });

        // Store in localStorage for persistence and handle disabled option clicks
        modelProviderSelect.addEventListener('change', (e) => {
            const selectedOption = modelProviderSelect.options[modelProviderSelect.selectedIndex];

            // Check if this is a LlamaCPP model that's not available
            if (selectedOption && selectedOption.dataset.available === 'false') {
                const providerName = selectedOption.value;

                // Check if it's a LlamaCPP model (can be downloaded)
                if (MODEL_CONFIGS[providerName]) {
                    // Revert to previous selection
                    const prevValue = modelProviderSelect.dataset.previousValue;
                    if (prevValue) {
                        modelProviderSelect.value = prevValue;
                    }

                    // Show mini wizard
                    if (miniModelWizard) {
                        miniModelWizard.show(providerName);
                    }
                    return;
                }
            }

            localStorage.setItem('selectedModelProvider', modelProviderSelect.value);
            console.log('Model provider changed to:', modelProviderSelect.value);
        });

        // Restore from localStorage if available
        const savedProvider = localStorage.getItem('selectedModelProvider');
        if (savedProvider) {
            const option = Array.from(modelProviderSelect.options).find(
                opt => opt.value === savedProvider && !opt.disabled
            );
            if (option) {
                modelProviderSelect.value = savedProvider;
            }
        }

        console.log('Model providers initialized:', providers);
    } catch (error) {
        console.error('Failed to initialize model providers:', error);
        if (modelProviderSelect) {
            modelProviderSelect.innerHTML = '<option value="">Error loading providers</option>';
            modelProviderSelect.disabled = true;
        }
    }
}

// Get currently selected model provider
export function getSelectedModelProvider() {
    if (!modelProviderSelect || !modelProviderSelect.value) {
        return null;
    }
    return modelProviderSelect.value;
}

// Initialize response styles dropdown
async function initializeResponseStyles() {
    try {
        console.log('[Main] Fetching response styles...');
        const data = await getResponseStyles();
        console.log('[Main] Response styles data:', data);

        const styles = data.styles || ['Normal'];
        const defaultStyle = data.default || 'Normal';
        const descriptions = data.descriptions || {};

        if (!responseStyleSelect) {
            console.error('[Main] Response style select element not found');
            return;
        }

        console.log('[Main] Found responseStyleSelect element, populating with', styles.length, 'styles');

        // Clear existing options
        responseStyleSelect.innerHTML = '';

        // Add style options
        styles.forEach(style => {
            const option = document.createElement('option');
            option.value = style;
            option.textContent = style;
            option.title = descriptions[style] || '';

            if (style === defaultStyle) {
                option.selected = true;
            }

            responseStyleSelect.appendChild(option);
        });

        // Store in localStorage for persistence
        responseStyleSelect.addEventListener('change', () => {
            localStorage.setItem('selectedResponseStyle', responseStyleSelect.value);
            console.log('Response style changed to:', responseStyleSelect.value);
        });

        // Restore from localStorage if available
        const savedStyle = localStorage.getItem('selectedResponseStyle');
        if (savedStyle && styles.includes(savedStyle)) {
            responseStyleSelect.value = savedStyle;
        }

        console.log('Response styles initialized:', styles);
    } catch (error) {
        console.error('Failed to initialize response styles:', error);
        if (responseStyleSelect) {
            responseStyleSelect.innerHTML = '<option value="Normal">Normal</option>';
        }
    }
}

// Get currently selected response style
export function getSelectedResponseStyle() {
    if (!responseStyleSelect || !responseStyleSelect.value) {
        return 'Normal';
    }
    return responseStyleSelect.value;
}

// Model configurations for mini wizard
const MODEL_CONFIGS = {
    'llamacpp-gpt-oss': {
        name: 'GPT-OSS-20B',
        desc: 'General purpose, high quality responses',
        size: '~13.8 GB',
        modelKey: 'gpt-oss'
    },
    'llamacpp-qwen3': {
        name: 'Qwen3-8B',
        desc: 'Fast, efficient multilingual model',
        size: '~5.2 GB',
        modelKey: 'qwen3'
    }
};

// Store providers data globally for click handler
let providersData = [];

// Mini Model Download Wizard
class MiniModelWizard {
    constructor() {
        this.overlay = document.getElementById('miniModelWizard');
        this.modelCard = document.getElementById('miniModelCard');
        this.modelName = document.getElementById('miniModelName');
        this.modelDesc = document.getElementById('miniModelDesc');
        this.modelSize = document.getElementById('miniModelSize');
        this.downloadBtn = document.getElementById('miniWizardDownload');
        this.skipBtn = document.getElementById('miniWizardSkip');
        this.terminalContainer = document.getElementById('miniTerminalContainer');
        this.terminalOutput = document.getElementById('miniTerminalOutput');
        this.progressContainer = this.modelCard?.querySelector('.model-progress-container');
        this.progressFill = this.modelCard?.querySelector('.model-progress-fill');
        this.progressPercent = this.modelCard?.querySelector('.model-progress-percent');
        this.statusDiv = this.modelCard?.querySelector('.model-status');

        this.currentModel = null;
        this.downloading = false;
        this.eventSource = null;

        this.bindEvents();
    }

    bindEvents() {
        this.skipBtn?.addEventListener('click', () => this.hide());
        this.downloadBtn?.addEventListener('click', () => this.startDownload());
        this.overlay?.querySelector('.setup-backdrop')?.addEventListener('click', () => {
            if (!this.downloading) this.hide();
        });
    }

    show(providerName) {
        const config = MODEL_CONFIGS[providerName];
        if (!config) return;

        this.currentModel = config.modelKey;

        // Update UI
        if (this.modelName) this.modelName.textContent = config.name;
        if (this.modelDesc) this.modelDesc.textContent = config.desc;
        if (this.modelSize) this.modelSize.textContent = config.size;
        if (this.modelCard) this.modelCard.dataset.model = config.modelKey;

        // Reset state
        if (this.progressContainer) this.progressContainer.style.display = 'none';
        if (this.progressFill) this.progressFill.style.width = '0%';
        if (this.terminalContainer) this.terminalContainer.style.display = 'none';
        if (this.terminalOutput) this.terminalOutput.innerHTML = '';
        if (this.statusDiv) {
            this.statusDiv.className = 'model-status';
            this.statusDiv.querySelector('.status-text').textContent = 'Ready to download';
        }
        if (this.downloadBtn) {
            this.downloadBtn.disabled = false;
            this.downloadBtn.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="7 10 12 15 17 10"></polyline>
                    <line x1="12" y1="15" x2="12" y2="3"></line>
                </svg>
                Download`;
        }

        // Show overlay
        if (this.overlay) {
            this.overlay.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        }
    }

    hide() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
        if (this.overlay) {
            this.overlay.style.display = 'none';
            document.body.style.overflow = '';
        }
        this.downloading = false;
    }

    async startDownload() {
        if (this.downloading || !this.currentModel) return;

        this.downloading = true;

        // Show progress
        if (this.progressContainer) this.progressContainer.style.display = 'block';
        if (this.terminalContainer) this.terminalContainer.style.display = 'block';
        if (this.terminalOutput) this.terminalOutput.innerHTML = '';

        // Update status
        if (this.statusDiv) {
            this.statusDiv.className = 'model-status downloading';
            this.statusDiv.querySelector('.status-text').textContent = 'Downloading...';
        }

        // Disable buttons
        if (this.downloadBtn) {
            this.downloadBtn.disabled = true;
            this.downloadBtn.innerHTML = 'Downloading...';
        }
        if (this.skipBtn) this.skipBtn.disabled = true;

        try {
            this.eventSource = new EventSource(`${API_BASE_URL}/api/setup/model-download?model=${this.currentModel}`);

            this.eventSource.onmessage = (event) => {
                const data = event.data;
                this.appendOutput(data);

                // Parse progress
                const fetchingMatch = data.match(/Fetching\s+\d+\s+files:\s*(\d+)%/);
                if (fetchingMatch) {
                    const percent = parseFloat(fetchingMatch[1]);
                    if (this.progressFill) this.progressFill.style.width = `${percent}%`;
                    if (this.progressPercent) this.progressPercent.textContent = `${percent}%`;
                }

                const progressMatch = data.match(/(\d+(?:\.\d+)?)\s*%\|/);
                if (progressMatch) {
                    const percent = parseFloat(progressMatch[1]);
                    if (this.progressFill) this.progressFill.style.width = `${percent}%`;
                    if (this.progressPercent) this.progressPercent.textContent = `${percent.toFixed(0)}%`;
                }

                // Check for completion
                if (data.includes('[COMPLETE]')) {
                    this.eventSource.close();
                    this.downloading = false;

                    if (this.progressFill) this.progressFill.style.width = '100%';
                    if (this.progressPercent) this.progressPercent.textContent = '100%';
                    if (this.statusDiv) {
                        this.statusDiv.className = 'model-status completed';
                        this.statusDiv.querySelector('.status-text').textContent = 'Downloaded & Ready';
                    }
                    if (this.downloadBtn) {
                        this.downloadBtn.innerHTML = '✓ Downloaded';
                    }

                    // Refresh model providers after successful download
                    setTimeout(() => {
                        this.hide();
                        initializeModelProviders();
                    }, 1500);
                }

                // Check for error
                if (data.includes('[ERROR]')) {
                    this.downloading = false;
                    if (this.statusDiv) {
                        this.statusDiv.className = 'model-status error';
                        this.statusDiv.querySelector('.status-text').textContent = 'Download failed';
                    }
                    if (this.downloadBtn) {
                        this.downloadBtn.disabled = false;
                        this.downloadBtn.innerHTML = 'Retry';
                    }
                    if (this.skipBtn) this.skipBtn.disabled = false;
                }
            };

            this.eventSource.onerror = () => {
                this.eventSource.close();
                this.downloading = false;
                if (this.statusDiv) {
                    this.statusDiv.className = 'model-status error';
                    this.statusDiv.querySelector('.status-text').textContent = 'Connection lost';
                }
                if (this.downloadBtn) {
                    this.downloadBtn.disabled = false;
                    this.downloadBtn.innerHTML = 'Retry';
                }
                if (this.skipBtn) this.skipBtn.disabled = false;
            };

        } catch (error) {
            console.error('Download error:', error);
            this.downloading = false;
            if (this.downloadBtn) {
                this.downloadBtn.disabled = false;
                this.downloadBtn.innerHTML = 'Retry';
            }
            if (this.skipBtn) this.skipBtn.disabled = false;
        }
    }

    appendOutput(text) {
        if (!this.terminalOutput) return;

        let formatted = text;
        if (text.includes('[STEP]')) formatted = `<span class="step">${text}</span>`;
        else if (text.includes('[SUCCESS]')) formatted = `<span class="success">${text}</span>`;
        else if (text.includes('[ERROR]')) formatted = `<span class="error">${text}</span>`;
        else if (text.includes('[INFO]') || text.includes('[COMPLETE]')) formatted = `<span class="info">${text}</span>`;

        this.terminalOutput.innerHTML += formatted + '\n';
        this.terminalOutput.scrollTop = this.terminalOutput.scrollHeight;
    }
}

let miniModelWizard = null;

// Initialize theme from localStorage or system preference
function initializeTheme() {
    const savedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    let theme = savedTheme || (systemPrefersDark ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', theme);

    // Update meta theme-color
    const metaThemeColor = document.querySelector('meta[name="theme-color"]');
    if (metaThemeColor) {
        metaThemeColor.setAttribute('content', theme === 'dark' ? '#1F273D' : '#ffffff');
    }
}

// Toggle theme
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);

    // Update meta theme-color
    const metaThemeColor = document.querySelector('meta[name="theme-color"]');
    if (metaThemeColor) {
        metaThemeColor.setAttribute('content', newTheme === 'dark' ? '#1F273D' : '#ffffff');
    }

    console.log('[Main] Theme changed to:', newTheme);
}

// Clear current session chat (clears messages in current session only)
async function clearCurrentChat() {
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        chatMessages.innerHTML = '';
    }

    // Clear conversation history in messaging module
    const { clearConversationHistory } = await import('./modules/messaging.js');
    clearConversationHistory();

    console.log('[Main] Current chat cleared');
}

// Initialize application
async function initializeApp() {
    console.log('=== INITIALIZING APPLICATION ===');
    console.log('API_BASE_URL:', API_BASE_URL);

    try {
        // Check setup status first
        console.log('[Main] Checking setup status...');
        const setupComplete = await checkSetupStatus();

        // Initialize setup wizard if not done
        if (!setupComplete) {
            console.log('[Main] Setup not complete, showing setup wizard...');
            initializeSetup();
        }

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

        // Initialize model provider selector
        console.log('[Main] Initializing model provider selector...');
        modelProviderSelect = document.getElementById('modelProvider');

        // Initialize response style selector
        console.log('[Main] Initializing response style selector...');
        responseStyleSelect = document.getElementById('responseStyle');
        styleToggleBtn = document.getElementById('styleToggleBtn');
        styleDropdown = document.getElementById('styleDropdown');

        // Initialize mini model wizard
        miniModelWizard = new MiniModelWizard();

        await initializeModelProviders();
        await initializeResponseStyles();

        // Initialize theme toggle
        console.log('[Main] Initializing theme toggle...');
        themeToggle = document.getElementById('themeToggle');
        initializeTheme();

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

    // Clear button - clears current session chat
    clearButton = document.getElementById('clearButton');
    if (clearButton) {
        clearButton.addEventListener('click', clearCurrentChat);
    }

    // Theme toggle
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
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

    // Style toggle dropdown
    if (styleToggleBtn && styleDropdown) {
        styleToggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const isOpen = styleDropdown.classList.contains('show');
            styleDropdown.classList.toggle('show');
            styleToggleBtn.classList.toggle('active', !isOpen);
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!styleDropdown.contains(e.target) && !styleToggleBtn.contains(e.target)) {
                styleDropdown.classList.remove('show');
                styleToggleBtn.classList.remove('active');
            }
        });

        // Close dropdown when style is selected
        if (responseStyleSelect) {
            responseStyleSelect.addEventListener('change', () => {
                styleDropdown.classList.remove('show');
                styleToggleBtn.classList.remove('active');
            });
        }
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
