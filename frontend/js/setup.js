// Setup Wizard Module
import { API_BASE_URL, IS_SETUP_DONE, setSetupDone } from './config.js';

class SetupWizard {
    constructor() {
        this.currentPage = 1;
        this.totalPages = 6;
        this.apiKeys = {
            openai: '',
            gemini: ''
        };
        this.skippedKeys = {
            openai: false,
            gemini: false,
            llama: false,
            model: false
        };
        this.pendingSkipType = null;
        this.llamaInstalling = false;
        this.modelDownloading = false;
        this.eventSource = null;

        // DOM Elements
        this.overlay = document.getElementById('setupOverlay');
        this.wizard = document.getElementById('setupWizard');
        this.welcomeAnimation = document.getElementById('welcomeAnimation');
        this.skipModal = document.getElementById('skipWarningModal');
        this.skipWarningText = document.getElementById('skipWarningText');

        // Llama.cpp elements
        this.llamaStatus = document.getElementById('llamaStatus');
        this.terminalContainer = document.getElementById('terminalContainer');
        this.terminalOutput = document.getElementById('terminalOutput');
        this.llamaNote = document.getElementById('llamaNote');
        this.llamaInstallBtn = document.getElementById('llamaInstallBtn');

        // Model download elements
        this.modelDownloadBtn = document.getElementById('modelDownloadBtn');
        this.downloadProgressContainer = document.getElementById('downloadProgressContainer');
        this.downloadProgressFill = document.getElementById('downloadProgressFill');
        this.downloadProgressPercent = document.getElementById('downloadProgressPercent');
        this.downloadProgressSpeed = document.getElementById('downloadProgressSpeed');
        this.downloadStatus = document.getElementById('downloadStatus');
        this.modelTerminalContainer = document.getElementById('modelTerminalContainer');
        this.modelTerminalOutput = document.getElementById('modelTerminalOutput');

        this.init();
    }

    init() {
        // Check if setup is already done
        if (IS_SETUP_DONE) {
            console.log('[Setup] Setup already completed, skipping wizard');
            this.hideSetup();
            return;
        }

        console.log('[Setup] Starting setup wizard...');
        this.showSetup();
        this.bindEvents();
    }

    showSetup() {
        if (this.overlay) {
            this.overlay.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        }
    }

    hideSetup() {
        if (this.overlay) {
            this.overlay.style.display = 'none';
            document.body.style.overflow = '';
        }
    }

    bindEvents() {
        // Button clicks
        this.wizard?.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-action]');
            if (!btn) return;

            const action = btn.dataset.action;
            const skipType = btn.dataset.skipType;

            switch (action) {
                case 'next':
                    this.nextPage();
                    break;
                case 'prev':
                    this.prevPage();
                    break;
                case 'skip':
                    this.showSkipWarning(skipType);
                    break;
                case 'finish':
                    this.finishSetup();
                    break;
                case 'install-llama':
                    this.installLlamaCpp();
                    break;
                case 'download-model':
                    const modelType = btn.dataset.model;
                    this.downloadModel(modelType);
                    break;
            }
        });

        // Toggle password visibility
        this.wizard?.addEventListener('click', (e) => {
            const toggleBtn = e.target.closest('.toggle-visibility');
            if (!toggleBtn) return;

            const wrapper = toggleBtn.closest('.api-input-wrapper');
            const input = wrapper?.querySelector('.api-input');
            const eyeIcon = toggleBtn.querySelector('.eye-icon');
            const eyeOffIcon = toggleBtn.querySelector('.eye-off-icon');

            if (input) {
                if (input.type === 'password') {
                    input.type = 'text';
                    eyeIcon.style.display = 'none';
                    eyeOffIcon.style.display = 'block';
                } else {
                    input.type = 'password';
                    eyeIcon.style.display = 'block';
                    eyeOffIcon.style.display = 'none';
                }
            }
        });

        // Skip warning modal buttons
        document.getElementById('cancelSkip')?.addEventListener('click', () => {
            this.hideSkipWarning();
        });

        document.getElementById('confirmSkip')?.addEventListener('click', () => {
            this.confirmSkip();
        });

        // Close skip modal on backdrop click
        this.skipModal?.querySelector('.skip-warning-backdrop')?.addEventListener('click', () => {
            this.hideSkipWarning();
        });

        // Track API key input changes
        document.getElementById('openaiApiKey')?.addEventListener('input', (e) => {
            this.apiKeys.openai = e.target.value.trim();
        });

        document.getElementById('geminiApiKey')?.addEventListener('input', (e) => {
            this.apiKeys.gemini = e.target.value.trim();
        });
    }

    goToPage(pageNum) {
        if (pageNum < 1 || pageNum > this.totalPages) return;

        // Hide current page
        const currentPageEl = this.wizard?.querySelector(`.setup-page[data-page="${this.currentPage}"]`);
        if (currentPageEl) {
            currentPageEl.classList.remove('active');
        }

        // Show new page
        this.currentPage = pageNum;
        const newPageEl = this.wizard?.querySelector(`.setup-page[data-page="${this.currentPage}"]`);
        if (newPageEl) {
            newPageEl.classList.add('active');
        }

        // Check llama status when entering page 5
        if (pageNum === 5) {
            this.checkLlamaStatus();
        }
    }

    nextPage() {
        // Validate current page if needed
        if (this.currentPage === 3) {
            // OpenAI page - save the key if provided
            const key = this.apiKeys.openai;
            if (key && !key.startsWith('sk-')) {
                this.showInputError('openaiApiKey', 'OpenAI API keys typically start with "sk-"');
                return;
            }
        }

        if (this.currentPage < this.totalPages) {
            this.goToPage(this.currentPage + 1);
        }
    }

    prevPage() {
        if (this.currentPage > 1) {
            this.goToPage(this.currentPage - 1);
        }
    }

    showInputError(inputId, message) {
        const input = document.getElementById(inputId);
        if (input) {
            input.style.borderColor = '#ef4444';
            input.focus();

            // Reset after delay
            setTimeout(() => {
                input.style.borderColor = '';
            }, 2000);
        }
    }

    showSkipWarning(skipType) {
        this.pendingSkipType = skipType;

        const messages = {
            openai: 'Without an OpenAI API key, GPT models will not be available. You can configure this later.',
            gemini: 'Without a Gemini API key, Google Gemini models will not be available. You can configure this later.',
            llama: 'Without llama.cpp, local LLM models will not be available. You can install this later.',
            model: 'Without the AI model, local inference will not be available. You can download it later.'
        };

        if (this.skipWarningText) {
            this.skipWarningText.textContent = messages[skipType] || 'This model provider will not be available.';
        }

        if (this.skipModal) {
            this.skipModal.style.display = 'flex';
        }
    }

    hideSkipWarning() {
        if (this.skipModal) {
            this.skipModal.style.display = 'none';
        }
        this.pendingSkipType = null;
    }

    confirmSkip() {
        if (this.pendingSkipType) {
            this.skippedKeys[this.pendingSkipType] = true;
            this.apiKeys[this.pendingSkipType] = '';

            // Clear the input
            const inputId = this.pendingSkipType === 'openai' ? 'openaiApiKey' : 'geminiApiKey';
            const input = document.getElementById(inputId);
            if (input) {
                input.value = '';
            }
        }

        this.hideSkipWarning();

        // If on last page with skip, finish setup
        if (this.currentPage === 6 && this.pendingSkipType === 'model') {
            this.finishSetup();
        } else {
            this.nextPage();
        }
    }

    async finishSetup() {
        console.log('[Setup] Finishing setup...');

        // Collect API keys to save
        const keysToSave = {};

        if (this.apiKeys.openai && !this.skippedKeys.openai) {
            keysToSave.OPENAI_API_KEY = this.apiKeys.openai;
        }

        if (this.apiKeys.gemini && !this.skippedKeys.gemini) {
            keysToSave.GEMINI_API_KEY = this.apiKeys.gemini;
        }

        try {
            // Save API keys to backend
            if (Object.keys(keysToSave).length > 0) {
                const response = await fetch(`${API_BASE_URL}/api/setup/save-keys`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(keysToSave)
                });

                if (!response.ok) {
                    throw new Error('Failed to save API keys');
                }

                console.log('[Setup] API keys saved successfully');
            }

            // Mark setup as done
            await this.markSetupDone();

            // Show welcome animation
            this.showWelcomeAnimation();

        } catch (error) {
            console.error('[Setup] Error finishing setup:', error);
            // Still proceed even if there's an error
            this.showWelcomeAnimation();
        }
    }

    async markSetupDone() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/setup/complete`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                setSetupDone(true);
                localStorage.setItem('setupComplete', 'true');
            }
        } catch (error) {
            console.error('[Setup] Error marking setup complete:', error);
            // Fallback to localStorage
            localStorage.setItem('setupComplete', 'true');
            setSetupDone(true);
        }
    }

    showWelcomeAnimation() {
        // Hide setup wizard
        this.hideSetup();

        // Show welcome animation
        if (this.welcomeAnimation) {
            this.welcomeAnimation.style.display = 'flex';

            // Auto-hide after animation
            setTimeout(() => {
                this.welcomeAnimation.style.opacity = '0';
                this.welcomeAnimation.style.transition = 'opacity 0.5s ease-out';

                setTimeout(() => {
                    this.welcomeAnimation.style.display = 'none';
                    document.body.style.overflow = '';
                }, 500);
            }, 2500);
        }
    }

    // ==================== LLAMA.CPP METHODS ====================

    async checkLlamaStatus() {
        if (!this.llamaStatus) return;

        this.llamaStatus.innerHTML = '<div class="status-checking">Checking installation status...</div>';

        try {
            const response = await fetch(`${API_BASE_URL}/api/setup/llama-status`);
            const status = await response.json();

            this.renderLlamaStatus(status);
        } catch (error) {
            console.error('[Setup] Error checking llama status:', error);
            this.llamaStatus.innerHTML = `
                <div class="llama-status-item">
                    <span class="status-icon error">✗</span>
                    <span>Unable to check installation status</span>
                </div>
            `;
        }
    }

    renderLlamaStatus(status) {
        if (!this.llamaStatus) return;

        const checkIcon = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"></polyline></svg>';
        const crossIcon = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>';
        const pendingIcon = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle></svg>';

        let html = '';

        // Repository cloned
        html += `
            <div class="llama-status-item">
                <span class="status-icon ${status.cloned ? 'success' : 'pending'}">${status.cloned ? checkIcon : pendingIcon}</span>
                <span>Repository cloned</span>
            </div>
        `;

        // ccache installed
        html += `
            <div class="llama-status-item">
                <span class="status-icon ${status.ccache_installed ? 'success' : 'pending'}">${status.ccache_installed ? checkIcon : pendingIcon}</span>
                <span>ccache installed</span>
            </div>
        `;

        // Built
        html += `
            <div class="llama-status-item">
                <span class="status-icon ${status.built ? 'success' : 'pending'}">${status.built ? checkIcon : pendingIcon}</span>
                <span>llama.cpp built</span>
            </div>
        `;

        // Server available
        html += `
            <div class="llama-status-item">
                <span class="status-icon ${status.server_available ? 'success' : 'pending'}">${status.server_available ? checkIcon : pendingIcon}</span>
                <span>llama-server ready</span>
            </div>
        `;

        this.llamaStatus.innerHTML = html;

        // Update button text based on status
        if (this.llamaInstallBtn) {
            if (status.installed) {
                // Go to model download page if already installed
                this.llamaInstallBtn.textContent = 'Continue';
                this.llamaInstallBtn.dataset.action = 'next';
            } else if (status.cloned && !status.built) {
                this.llamaInstallBtn.textContent = 'Build llama.cpp';
            } else {
                this.llamaInstallBtn.textContent = 'Install llama.cpp';
            }
        }

        // Show note
        if (this.llamaNote) {
            this.llamaNote.style.display = 'block';
        }
    }

    async installLlamaCpp() {
        if (this.llamaInstalling) return;

        this.llamaInstalling = true;

        // Show terminal
        if (this.terminalContainer) {
            this.terminalContainer.style.display = 'block';
        }
        if (this.terminalOutput) {
            this.terminalOutput.innerHTML = '';
        }

        // Disable install button
        if (this.llamaInstallBtn) {
            this.llamaInstallBtn.disabled = true;
            this.llamaInstallBtn.textContent = 'Installing...';
        }

        try {
            // Use EventSource for streaming
            const eventSource = new EventSource(`${API_BASE_URL}/api/setup/llama-install`);
            this.eventSource = eventSource;

            eventSource.onmessage = (event) => {
                const data = event.data;
                this.appendTerminalOutput(data);

                // Check for completion
                if (data.includes('[COMPLETE]')) {
                    eventSource.close();
                    this.llamaInstalling = false;
                    this.checkLlamaStatus();

                    if (this.llamaInstallBtn) {
                        this.llamaInstallBtn.disabled = false;
                        this.llamaInstallBtn.textContent = 'Continue';
                        this.llamaInstallBtn.dataset.action = 'next';
                    }
                }

                // Check for error
                if (data.includes('[ERROR]')) {
                    this.llamaInstalling = false;
                    if (this.llamaInstallBtn) {
                        this.llamaInstallBtn.disabled = false;
                        this.llamaInstallBtn.textContent = 'Retry Installation';
                    }
                }
            };

            eventSource.onerror = (error) => {
                console.error('[Setup] EventSource error:', error);
                eventSource.close();
                this.llamaInstalling = false;

                if (this.llamaInstallBtn) {
                    this.llamaInstallBtn.disabled = false;
                    this.llamaInstallBtn.textContent = 'Retry Installation';
                }

                this.appendTerminalOutput('[ERROR] Connection lost. Please try again.');
            };

        } catch (error) {
            console.error('[Setup] Error installing llama.cpp:', error);
            this.llamaInstalling = false;

            if (this.llamaInstallBtn) {
                this.llamaInstallBtn.disabled = false;
                this.llamaInstallBtn.textContent = 'Retry Installation';
            }

            this.appendTerminalOutput(`[ERROR] ${error.message}`);
        }
    }

    appendTerminalOutput(text) {
        if (!this.terminalOutput) return;

        // Apply color classes based on tags
        let formattedText = text;
        if (text.includes('[STEP]')) {
            formattedText = `<span class="step">${text}</span>`;
        } else if (text.includes('[SUCCESS]')) {
            formattedText = `<span class="success">${text}</span>`;
        } else if (text.includes('[ERROR]')) {
            formattedText = `<span class="error">${text}</span>`;
        } else if (text.includes('[WARNING]')) {
            formattedText = `<span class="warning">${text}</span>`;
        } else if (text.includes('[INFO]') || text.includes('[COMPLETE]')) {
            formattedText = `<span class="info">${text}</span>`;
        }

        this.terminalOutput.innerHTML += formattedText + '\n';
        this.terminalOutput.scrollTop = this.terminalOutput.scrollHeight;
    }

    appendModelTerminalOutput(text) {
        if (!this.modelTerminalOutput) return;

        let formattedText = text;
        if (text.includes('[STEP]')) {
            formattedText = `<span class="step">${text}</span>`;
        } else if (text.includes('[SUCCESS]')) {
            formattedText = `<span class="success">${text}</span>`;
        } else if (text.includes('[ERROR]')) {
            formattedText = `<span class="error">${text}</span>`;
        } else if (text.includes('[WARNING]')) {
            formattedText = `<span class="warning">${text}</span>`;
        } else if (text.includes('[INFO]') || text.includes('[COMPLETE]')) {
            formattedText = `<span class="info">${text}</span>`;
        }

        this.modelTerminalOutput.innerHTML += formattedText + '\n';
        this.modelTerminalOutput.scrollTop = this.modelTerminalOutput.scrollHeight;
    }

    // ==================== MODEL DOWNLOAD METHODS ====================

    async downloadModel(modelType) {
        if (this.modelDownloading) return;

        this.modelDownloading = true;
        this.currentDownloadingModel = modelType;

        // Get model card elements
        const modelCard = document.querySelector(`.model-card[data-model="${modelType}"]`);
        const progressContainer = modelCard?.querySelector('.model-progress-container');
        const progressFill = modelCard?.querySelector('.model-progress-fill');
        const progressPercent = modelCard?.querySelector('.model-progress-percent');
        const progressSpeed = modelCard?.querySelector('.model-progress-speed');
        const statusDiv = modelCard?.querySelector('.model-status');
        const downloadBtn = modelCard?.querySelector('.model-download-btn');

        // Show progress container and terminal
        if (progressContainer) {
            progressContainer.style.display = 'block';
        }
        if (this.modelTerminalContainer) {
            this.modelTerminalContainer.style.display = 'block';
        }
        if (this.modelTerminalOutput) {
            this.modelTerminalOutput.innerHTML = '';
        }

        // Update card and status
        if (modelCard) {
            modelCard.classList.add('downloading');
        }
        if (statusDiv) {
            statusDiv.className = 'model-status downloading';
            statusDiv.querySelector('.status-text').textContent = 'Downloading...';
        }

        // Disable download button
        if (downloadBtn) {
            downloadBtn.disabled = true;
            downloadBtn.classList.add('downloading');
            downloadBtn.innerHTML = 'Downloading...';
        }

        try {
            const eventSource = new EventSource(`${API_BASE_URL}/api/setup/model-download?model=${modelType}`);
            this.eventSource = eventSource;

            eventSource.onmessage = (event) => {
                const data = event.data;
                this.appendModelTerminalOutput(data);

                // Parse progress from "Fetching X files: Y%|" format
                const fetchingMatch = data.match(/Fetching\s+\d+\s+files:\s*(\d+)%/);
                if (fetchingMatch) {
                    const percent = parseFloat(fetchingMatch[1]);
                    if (progressFill) progressFill.style.width = `${percent}%`;
                    if (progressPercent) progressPercent.textContent = `${percent}%`;
                }

                // Also try generic percentage match
                const progressMatch = data.match(/(\d+(?:\.\d+)?)\s*%\|/);
                if (progressMatch) {
                    const percent = parseFloat(progressMatch[1]);
                    if (progressFill) progressFill.style.width = `${percent}%`;
                    if (progressPercent) progressPercent.textContent = `${percent.toFixed(0)}%`;
                }

                // Parse "X/Y" file progress format
                const fileProgressMatch = data.match(/(\d+)\/(\d+)\s*\[/);
                if (fileProgressMatch) {
                    const current = parseInt(fileProgressMatch[1]);
                    const total = parseInt(fileProgressMatch[2]);
                    const percent = (current / total) * 100;
                    if (progressFill) progressFill.style.width = `${percent}%`;
                    if (progressPercent) progressPercent.textContent = `${percent.toFixed(0)}%`;
                }

                // Parse speed if available
                const speedMatch = data.match(/(\d+(?:\.\d+)?\s*(?:MB|GB|KB|B)\/s)/i);
                if (speedMatch && progressSpeed) {
                    progressSpeed.textContent = speedMatch[1];
                }

                // Update status text with current file being downloaded
                if (data.includes("Downloading '") && statusDiv) {
                    const fileMatch = data.match(/Downloading '([^']+)'/);
                    if (fileMatch) {
                        statusDiv.querySelector('.status-text').textContent = `Downloading ${fileMatch[1]}...`;
                    }
                }

                // Check for completion
                if (data.includes('[COMPLETE]')) {
                    eventSource.close();
                    this.modelDownloading = false;

                    if (progressFill) progressFill.style.width = '100%';
                    if (progressPercent) progressPercent.textContent = '100%';

                    if (modelCard) {
                        modelCard.classList.remove('downloading');
                        modelCard.classList.add('completed');
                    }
                    if (statusDiv) {
                        statusDiv.className = 'model-status completed';
                        statusDiv.querySelector('.status-text').textContent = 'Downloaded & Ready';
                    }
                    if (downloadBtn) {
                        downloadBtn.disabled = false;
                        downloadBtn.classList.remove('downloading');
                        downloadBtn.classList.add('completed');
                        downloadBtn.innerHTML = '✓ Downloaded';
                    }

                    // Store selected model
                    localStorage.setItem('selectedLocalModel', modelType);
                }

                // Check for error
                if (data.includes('[ERROR]')) {
                    this.modelDownloading = false;

                    if (modelCard) {
                        modelCard.classList.remove('downloading');
                    }
                    if (statusDiv) {
                        statusDiv.className = 'model-status error';
                        statusDiv.querySelector('.status-text').textContent = 'Download failed';
                    }
                    if (downloadBtn) {
                        downloadBtn.disabled = false;
                        downloadBtn.classList.remove('downloading');
                        downloadBtn.innerHTML = `
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                <polyline points="7 10 12 15 17 10"></polyline>
                                <line x1="12" y1="15" x2="12" y2="3"></line>
                            </svg>
                            Retry`;
                    }
                }
            };

            eventSource.onerror = (error) => {
                console.error('[Setup] EventSource error:', error);
                eventSource.close();
                this.modelDownloading = false;

                if (modelCard) {
                    modelCard.classList.remove('downloading');
                }
                if (statusDiv) {
                    statusDiv.className = 'model-status error';
                    statusDiv.querySelector('.status-text').textContent = 'Connection lost';
                }
                if (downloadBtn) {
                    downloadBtn.disabled = false;
                    downloadBtn.classList.remove('downloading');
                    downloadBtn.innerHTML = `
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="7 10 12 15 17 10"></polyline>
                            <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                        Retry`;
                }

                this.appendModelTerminalOutput('[ERROR] Connection lost. Please try again.');
            };

        } catch (error) {
            console.error('[Setup] Error downloading model:', error);
            this.modelDownloading = false;

            if (modelCard) {
                modelCard.classList.remove('downloading');
            }
            if (statusDiv) {
                statusDiv.className = 'model-status error';
                statusDiv.querySelector('.status-text').textContent = 'Download failed';
            }
            if (downloadBtn) {
                downloadBtn.disabled = false;
                downloadBtn.classList.remove('downloading');
                downloadBtn.innerHTML = `
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                        <polyline points="7 10 12 15 17 10"></polyline>
                        <line x1="12" y1="15" x2="12" y2="3"></line>
                    </svg>
                    Retry`;
            }

            this.appendModelTerminalOutput(`[ERROR] ${error.message}`);
        }
    }
}

// Initialize setup wizard when DOM is ready
export function initializeSetup() {
    return new SetupWizard();
}

// Export for use in main.js
export default SetupWizard;
