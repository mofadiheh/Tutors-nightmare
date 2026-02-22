// Landing page functionality

let currentUser = null;
let startersCache = [];

function getUrlParams() {
    const params = new URLSearchParams(window.location.search);
    return {
        primary: params.get('primary') || '',
        secondary: params.get('secondary') || 'en'
    };
}

function getNextPath() {
    const query = window.location.search || '';
    return `${window.location.pathname}${query}`;
}

function redirectToAuth() {
    const next = encodeURIComponent(getNextPath());
    window.location.href = `/auth?next=${next}`;
}

function saveLanguagePreferences(primary, secondary) {
    localStorage.setItem('languagePrefs', JSON.stringify({
        primary,
        secondary,
        timestamp: Date.now()
    }));
}

function loadLanguagePreferences() {
    const saved = localStorage.getItem('languagePrefs');
    if (!saved) {
        return null;
    }

    try {
        return JSON.parse(saved);
    } catch (_error) {
        return null;
    }
}

async function fetchCurrentUser() {
    const response = await fetch('/api/me');
    if (response.status === 401) {
        redirectToAuth();
        return null;
    }
    if (!response.ok) {
        throw new Error('Failed to fetch profile');
    }
    currentUser = await response.json();
    return currentUser;
}

async function persistProfilePreferences(primary, secondary) {
    try {
        await fetch('/api/me', {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                preferred_primary_lang: primary,
                preferred_secondary_lang: secondary
            })
        });
    } catch (error) {
        console.warn('Failed to persist profile preferences:', error);
    }
}

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
        if (response.status === 401) {
            redirectToAuth();
            return;
        }
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

    topicsContainer.innerHTML = starters.map((starter) => `
        <div class="topic-card" data-starter-id="${starter.id}">
            <span class="topic-icon">💬</span>
            <div class="topic-title">${starter.title}</div>
            <div class="topic-description">${starter.preview}</div>
        </div>
    `).join('');

    document.querySelectorAll('.topic-card').forEach((card) => {
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
        if (response.status === 401) {
            redirectToAuth();
            return;
        }
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

async function startChat(starterId = null) {
    if (!validateLanguages()) {
        return;
    }

    const primary = document.getElementById('primaryLanguage').value;
    const secondary = document.getElementById('secondaryLanguage').value;

    saveLanguagePreferences(primary, secondary);
    await persistProfilePreferences(primary, secondary);

    const params = new URLSearchParams({
        primary,
        secondary,
        display: secondary
    });

    if (starterId) {
        params.set('starter', starterId);
    }

    window.location.href = `/chat?${params.toString()}`;
}

async function handleLogout() {
    try {
        await fetch('/api/auth/logout', { method: 'POST' });
    } finally {
        window.location.href = '/auth';
    }
}

function applyInitialLanguageDefaults(user) {
    const saved = loadLanguagePreferences();
    const urlParams = getUrlParams();

    const primary = urlParams.primary || (saved && saved.primary) || user.preferred_primary_lang || '';
    const secondary = urlParams.secondary || (saved && saved.secondary) || user.preferred_secondary_lang || 'en';

    document.getElementById('primaryLanguage').value = primary;
    document.getElementById('secondaryLanguage').value = secondary;
}

// Initialize page
document.addEventListener('DOMContentLoaded', async () => {
    const user = await fetchCurrentUser();
    if (!user) {
        return;
    }

    try {
        applyInitialLanguageDefaults(user);
        await loadConversationStarters();

        const freeDiscussionBtn = document.getElementById('freeDiscussionBtn');
        if (freeDiscussionBtn) {
            freeDiscussionBtn.addEventListener('click', () => {
                startChat(null);
            });
        }

        const refreshBtn = document.getElementById('refreshStartersBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                refreshConversationStarters();
            });
        }

        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', handleLogout);
        }

        document.querySelectorAll('.language-dropdown').forEach((dropdown) => {
            dropdown.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    startChat(null);
                }
            });
        });
    } catch (error) {
        console.error('Failed to initialize landing page:', error);
    }
});
