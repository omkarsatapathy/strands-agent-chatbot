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

export { API_BASE_URL, CONFIG };
