// Session Manager for Chat History
class SessionManager {
    constructor(apiBaseUrl) {
        this.apiBaseUrl = apiBaseUrl;
        this.currentSessionId = null;
        this.sessions = [];
    }

    // Generate session title from first message
    generateSessionTitle(message) {
        const maxLength = 30;
        if (message.length <= maxLength) {
            return message;
        }
        return message.substring(0, maxLength) + '...';
    }

    // Create a new session
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

    // Get current session ID
    getCurrentSessionId() {
        return this.currentSessionId;
    }

    // Set current session ID
    setCurrentSessionId(sessionId) {
        this.currentSessionId = sessionId;
    }

    // List all sessions
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

    // Get a specific session with messages
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

    // Delete a session
    async deleteSession(sessionId) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/sessions/${sessionId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error(`Failed to delete session: ${response.status}`);
            }

            // Remove from local sessions list
            this.sessions = this.sessions.filter(s => s.session_id !== sessionId);

            // If deleted session was current, clear it
            if (this.currentSessionId === sessionId) {
                this.currentSessionId = null;
            }

            return true;
        } catch (error) {
            console.error('Error deleting session:', error);
            throw error;
        }
    }

    // Save a message to current session
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

    // Get messages for a session
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

    // Format date for display
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

// Expose SessionManager to window for use in ES6 modules
window.SessionManager = SessionManager;
