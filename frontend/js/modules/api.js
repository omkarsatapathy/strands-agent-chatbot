// API Helper Functions
import { API_BASE_URL, CONFIG } from '../config.js';

// Sleep utility
export function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Fetch with timeout
export async function fetchWithTimeout(url, options, timeout = CONFIG.REQUEST_TIMEOUT) {
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
export async function fetchWithRetry(url, options, retries = CONFIG.MAX_RETRIES) {
    let lastError;

    for (let i = 0; i < retries; i++) {
        try {
            if (i > 0) {
                console.log(`Retry attempt ${i + 1}/${retries}`);
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

// Check server health
export async function checkServerHealth() {
    try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/api/health`, {}, 5000);
        if (response.ok) {
            return { isOnline: true, message: 'Ready' };
        } else {
            return { isOnline: false, message: 'Server Error' };
        }
    } catch (error) {
        console.error('Health check failed:', error);
        return { isOnline: false, message: 'Offline' };
    }
}

// Get available model providers
export async function getModelProviders() {
    try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/api/models/providers`, {}, 5000);
        if (response.ok) {
            return await response.json();
        } else {
            console.error('Failed to get model providers');
            return { providers: [], default: null };
        }
    } catch (error) {
        console.error('Error getting model providers:', error);
        return { providers: [], default: null };
    }
}
