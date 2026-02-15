// Landing page functionality

// Get URL parameters
function getUrlParams() {
    const params = new URLSearchParams(window.location.search);
    return {
        primary: params.get('primary') || '',
        secondary: params.get('secondary') || 'en'
    };
}

// Save language preferences to localStorage
function saveLanguagePreferences(primary, secondary) {
    localStorage.setItem('languagePrefs', JSON.stringify({
        primary,
        secondary,
        timestamp: Date.now()
    }));
}

// Load language preferences from localStorage
function loadLanguagePreferences() {
    const saved = localStorage.getItem('languagePrefs');
    if (saved) {
        try {
            return JSON.parse(saved);
        } catch (e) {
            return null;
        }
    }
    return null;
}

// Conversation starters state
let startersCache = [];

// Fetch conversation starters
async function loadConversationStarters() {
    const topicsContainer = document.getElementById('topicsContainer');
    const timestampEl = document.getElementById('startersTimestamp');
    const statusEl = document.getElementById('startersStatus');
    statusEl.textContent = '';
    statusEl.style.color = '#e53e3e';

    topicsContainer.innerHTML = `
        <div class="loading-topics">
            <div class="spinner"></div>
            <p>Loading conversation starters...</p>
        </div>
    `;

    try {
        const response = await fetch('/api/conversation_starters');
        if (!response.ok) {
            throw new Error('Failed to load conversation starters');
        }
        const data = await response.json();
        startersCache = data.starters || [];
        renderConversationStarters(startersCache);
        timestampEl.textContent = data.generated_at
            ? `Updated ${new Date(data.generated_at).toLocaleString()}`
            : 'Not generated yet';
    } catch (error) {
        console.error('Error loading conversation starters:', error);
        topicsContainer.innerHTML = `
            <div class="error-message">
                <p><strong>Oops!</strong> Failed to load conversation starters.</p>
                <button id="retryLoadStarters">Try Again</button>
            </div>
        `;
        timestampEl.textContent = 'Unable to load starters.';
        const retryBtn = document.getElementById('retryLoadStarters');
        if (retryBtn) {
            retryBtn.addEventListener('click', loadConversationStarters);
        }
        statusEl.textContent = 'Please try refreshing again.';
    }
}

function renderConversationStarters(starters) {
    const topicsContainer = document.getElementById('topicsContainer');
    
    if (!starters || starters.length === 0) {
        topicsContainer.innerHTML = `
            <div class="error-message">
                <p>No conversation starters available right now.</p>
            </div>
        `;
        return;
    }
    
    topicsContainer.innerHTML = starters.map(starter => `
        <div class="topic-card" data-starter-id="${starter.id}">
            <span class="topic-icon">💬</span>
            <div class="topic-title">${starter.title}</div>
            <div class="topic-description">${starter.preview}</div>
        </div>
    `).join('');
    
    document.querySelectorAll('.topic-card').forEach(card => {
        card.addEventListener('click', () => {
            const starterId = card.dataset.starterId;
            startChat(starterId);
        });
    });
}

async function refreshConversationStarters() {
    const button = document.getElementById('refreshStartersBtn');
    const statusEl = document.getElementById('startersStatus');
    button.disabled = true;
    statusEl.textContent = 'Refreshing conversation starters...';
    
    try {
        const response = await fetch('/api/conversation_starters/refresh', {
            method: 'POST'
        });
        if (response.status === 429) {
            const data = await response.json();
            const seconds = data.detail?.retry_after_seconds ?? 0;
            const minutes = Math.ceil(seconds / 60);
            statusEl.textContent = `Please wait about ${minutes} minute(s) before refreshing again.`;
            statusEl.style.color = '#e53e3e';
            return;
        }
        if (!response.ok) {
            throw new Error('Failed to refresh conversation starters');
        }
        statusEl.style.color = '#38a169';
        statusEl.textContent = 'New conversation starters ready!';
        await loadConversationStarters();
    } catch (error) {
        console.error('Refresh error:', error);
        statusEl.style.color = '#e53e3e';
        statusEl.textContent = 'Refresh failed. Please try again shortly.';
    } finally {
        button.disabled = false;
    }
}

// Validate language selection
function validateLanguages() {
    const primary = document.getElementById('primaryLanguage').value;
    const secondary = document.getElementById('secondaryLanguage').value;
    
    if (!primary) {
        alert('Please select the language you are learning.');
        document.getElementById('primaryLanguage').focus();
        return false;
    }
    
    if (!secondary) {
        alert('Please select the language you speak.');
        document.getElementById('secondaryLanguage').focus();
        return false;
    }
    
    if (primary === secondary) {
        alert('Please select different languages for learning and speaking.');
        return false;
    }
    
    return true;
}

// Start chat with selected starter
function startChat(starterId = null) {
    if (!validateLanguages()) {
        return;
    }
    
    const primary = document.getElementById('primaryLanguage').value;
    const secondary = document.getElementById('secondaryLanguage').value;
    
    // Save preferences
    saveLanguagePreferences(primary, secondary);
    
    // Build chat URL
    const params = new URLSearchParams({
        primary,
        secondary
    });
    
    if (starterId) {
        params.set('starter', starterId);
    }
    
    // Navigate to chat page
    window.location.href = `/chat?${params.toString()}`;
}

// Initialize page
document.addEventListener('DOMContentLoaded', () => {
    // Load saved preferences
    const saved = loadLanguagePreferences();
    const urlParams = getUrlParams();
    
    // Set dropdowns to saved or URL values
    if (urlParams.primary) {
        document.getElementById('primaryLanguage').value = urlParams.primary;
    } else if (saved && saved.primary) {
        document.getElementById('primaryLanguage').value = saved.primary;
    }
    
    if (urlParams.secondary) {
        document.getElementById('secondaryLanguage').value = urlParams.secondary;
    } else if (saved && saved.secondary) {
        document.getElementById('secondaryLanguage').value = saved.secondary;
    }
    
    // Load conversation starters
    loadConversationStarters();
    
    // Free discussion button
    document.getElementById('freeDiscussionBtn').addEventListener('click', () => {
        startChat(null);
    });
    
    document.getElementById('refreshStartersBtn').addEventListener('click', () => {
        refreshConversationStarters();
    });
    
    // Allow Enter key to start chat
    document.querySelectorAll('.language-dropdown').forEach(dropdown => {
        dropdown.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                startChat(null);
            }
        });
    });
});
