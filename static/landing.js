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

// Fetch topics from API
async function loadTopics(lang = 'en') {
    const topicsContainer = document.getElementById('topicsContainer');
    
    try {
        const response = await fetch(`/api/topics?lang=${lang}`);
        
        if (!response.ok) {
            throw new Error('Failed to load topics');
        }
        
        const topics = await response.json();
        renderTopics(topics);
        
    } catch (error) {
        console.error('Error loading topics:', error);
        topicsContainer.innerHTML = `
            <div class="error-message">
                <p><strong>Oops!</strong> Failed to load topics.</p>
                <button onclick="loadTopics('${lang}')">Try Again</button>
            </div>
        `;
    }
}

// Render topics to the page
function renderTopics(topics) {
    const topicsContainer = document.getElementById('topicsContainer');
    
    if (!topics || topics.length === 0) {
        topicsContainer.innerHTML = `
            <div class="error-message">
                <p>No topics available at the moment.</p>
            </div>
        `;
        return;
    }
    
    topicsContainer.innerHTML = topics.map(topic => `
        <div class="topic-card" data-topic-id="${topic.id}">
            <span class="topic-icon">${topic.icon || '💬'}</span>
            <div class="topic-title">${topic.title}</div>
            <div class="topic-description">${topic.description}</div>
        </div>
    `).join('');
    
    // Add click handlers to topic cards
    document.querySelectorAll('.topic-card').forEach(card => {
        card.addEventListener('click', () => {
            const topicId = card.dataset.topicId;
            startChat(topicId);
        });
    });
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

// Start chat with topic
function startChat(topicId = null) {
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
    
    if (topicId) {
        params.set('topic', topicId);
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
    
    // Load topics
    const primaryLang = document.getElementById('primaryLanguage').value || 'en';
    loadTopics(primaryLang);
    
    // Update topics when primary language changes
    document.getElementById('primaryLanguage').addEventListener('change', (e) => {
        const lang = e.target.value || 'en';
        loadTopics(lang);
    });
    
    // Free discussion button
    document.getElementById('freeDiscussionBtn').addEventListener('click', () => {
        startChat(null);
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
