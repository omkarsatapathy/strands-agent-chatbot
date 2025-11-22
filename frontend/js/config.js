// API Configuration
export const API_BASE_URL = window.location.origin;

// Setup Status - Check localStorage first, fallback to checking with backend
export let IS_SETUP_DONE = localStorage.getItem('setupComplete') === 'true';

// Function to update setup status
export function setSetupDone(value) {
    IS_SETUP_DONE = value;
    localStorage.setItem('setupComplete', value ? 'true' : 'false');
}

// Check setup status from backend (call this on init)
export async function checkSetupStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/setup/status`);
        if (response.ok) {
            const data = await response.json();
            IS_SETUP_DONE = data.setup_complete;
            localStorage.setItem('setupComplete', data.setup_complete ? 'true' : 'false');
            return data.setup_complete;
        }
    } catch (error) {
        console.error('[Config] Error checking setup status:', error);
    }
    return IS_SETUP_DONE;
}

// Configuration constants
export const CONFIG = {
    MAX_RETRIES: 3,
    RETRY_DELAY: 1000, // ms
    REQUEST_TIMEOUT: 60000, // 60 seconds
    HEALTH_CHECK_INTERVAL: 30000, // 30 seconds
    MAX_CONVERSATION_HISTORY: 10,  // Limit to 10 messages (matches backend)
    AUTO_RECONNECT: true
};
