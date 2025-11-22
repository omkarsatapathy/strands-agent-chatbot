// Setup Wizard Module
import { API_BASE_URL, IS_SETUP_DONE, setSetupDone } from './config.js';

class SetupWizard {
    constructor() {
        this.currentPage = 1;
        this.totalPages = 4;
        this.apiKeys = {
            openai: '',
            gemini: ''
        };
        this.skippedKeys = {
            openai: false,
            gemini: false
        };
        this.pendingSkipType = null;

        // DOM Elements
        this.overlay = document.getElementById('setupOverlay');
        this.wizard = document.getElementById('setupWizard');
        this.welcomeAnimation = document.getElementById('welcomeAnimation');
        this.skipModal = document.getElementById('skipWarningModal');
        this.skipWarningText = document.getElementById('skipWarningText');

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
            gemini: 'Without a Gemini API key, Google Gemini models will not be available. You can configure this later.'
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
        if (this.currentPage === 4 && this.pendingSkipType === 'gemini') {
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
}

// Initialize setup wizard when DOM is ready
export function initializeSetup() {
    return new SetupWizard();
}

// Export for use in main.js
export default SetupWizard;
