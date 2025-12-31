// Chat page functionality

// Chat state management
const chatState = {
    messages: [],
    conversationId: null,
    primaryLang: 'es',
    secondaryLang: 'en',
    displayLang: 'es',
    mode: 'chat', // 'chat' or 'tutor'
    topicId: null
};

// Get URL parameters
function getUrlParams() {
    const params = new URLSearchParams(window.location.search);
    return {
        conversationId: params.get('c'),
        topic: params.get('topic'),
        mode: params.get('mode') || 'chat',
        primary: params.get('primary') || 'es',
        secondary: params.get('secondary') || 'en',
        display: params.get('display')
    };
}

// Update URL without reloading page
function updateUrl(params) {
    const url = new URLSearchParams();
    if (params.conversationId) url.set('c', params.conversationId);
    if (params.topic) url.set('topic', params.topic);
    if (params.mode && params.mode !== 'chat') url.set('mode', params.mode);
    if (params.primary) url.set('primary', params.primary);
    if (params.secondary) url.set('secondary', params.secondary);
    if (params.display && params.display !== params.primary) url.set('display', params.display);
    
    const newUrl = `${window.location.pathname}?${url.toString()}`;
    window.history.replaceState({}, '', newUrl);
}

// DOM elements
const messagesContainer = document.getElementById('messagesContainer');
const chatForm = document.getElementById('chatForm');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const statusIndicator = document.getElementById('statusIndicator');
const homeButton = document.getElementById('homeButton');
const languageToggle = document.getElementById('languageToggle');
const tutorModeButton = document.getElementById('tutorModeButton');
const currentLangSpan = document.getElementById('currentLang');
const targetLangSpan = document.getElementById('targetLang');

// Format time for messages
function formatTime(date) {
    return date.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit' 
    });
}

// Create message bubble element
function createMessageBubble(text, role, timestamp = new Date()) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const bubbleDiv = document.createElement('div');
    bubbleDiv.className = 'message-bubble';
    bubbleDiv.textContent = text;
    
    const timeDiv = document.createElement('div');
    timeDiv.className = 'message-time';
    timeDiv.textContent = formatTime(timestamp);
    
    bubbleDiv.appendChild(timeDiv);
    messageDiv.appendChild(bubbleDiv);
    
    return messageDiv;
}

// Add message to UI
function addMessageToUI(text, role) {
    // Remove welcome message if it exists
    const welcomeMessage = messagesContainer.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.remove();
    }
    
    const messageBubble = createMessageBubble(text, role);
    messagesContainer.appendChild(messageBubble);
    
    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    return messageBubble;
}

// Add typing indicator
function showTypingIndicator() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant loading';
    messageDiv.id = 'typingIndicator';
    
    const bubbleDiv = document.createElement('div');
    bubbleDiv.className = 'message-bubble';
    
    const typingDiv = document.createElement('div');
    typingDiv.className = 'typing-indicator';
    typingDiv.innerHTML = '<span></span><span></span><span></span>';
    
    bubbleDiv.appendChild(typingDiv);
    messageDiv.appendChild(bubbleDiv);
    messagesContainer.appendChild(messageDiv);
    
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Remove typing indicator
function removeTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) {
        indicator.remove();
    }
}

// Update language toggle button display
function updateLanguageToggleDisplay() {
    const isDisplayingPrimary = chatState.displayLang === chatState.primaryLang;
    currentLangSpan.textContent = chatState.primaryLang.toUpperCase();
    targetLangSpan.textContent = chatState.secondaryLang.toUpperCase();
    
    // Highlight current display language
    if (isDisplayingPrimary) {
        currentLangSpan.style.fontWeight = 'bold';
        targetLangSpan.style.fontWeight = 'normal';
    } else {
        currentLangSpan.style.fontWeight = 'normal';
        targetLangSpan.style.fontWeight = 'bold';
    }
}

// Update mode indicator
function updateModeDisplay() {
    if (chatState.mode === 'tutor') {
        tutorModeButton.classList.add('active');
        tutorModeButton.title = 'Exit Tutor Mode';
    } else {
        tutorModeButton.classList.remove('active');
        tutorModeButton.title = 'Enter Tutor Mode';
    }
}

// Send message to API
async function sendMessageToAPI(userText) {
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                conversation_id: chatState.conversationId,
                user_text: userText,
                user_lang: chatState.primaryLang,
                display_lang: chatState.displayLang,
                mode: chatState.mode
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to send message');
        }
        
        const data = await response.json();
        
        // Update conversation ID if new
        if (data.conversation_id && !chatState.conversationId) {
            chatState.conversationId = data.conversation_id;
            updateUrl({
                conversationId: data.conversation_id,
                topic: chatState.topicId,
                mode: chatState.mode,
                primary: chatState.primaryLang,
                secondary: chatState.secondaryLang,
                display: chatState.displayLang
            });
        }
        
        return data;
        
    } catch (error) {
        console.error('Error sending message:', error);
        throw error;
    }
}

// Handle form submission
async function handleSubmit(e) {
    e.preventDefault();
    
    const userMessage = messageInput.value.trim();
    if (!userMessage) return;
    
    // Add user message to UI
    addMessageToUI(userMessage, 'user');
    
    // Store message in state
    chatState.messages.push({
        role: 'user',
        text: userMessage,
        timestamp: new Date()
    });
    
    // Clear input
    messageInput.value = '';
    
    // Disable input while processing
    messageInput.disabled = true;
    sendButton.disabled = true;
    
    // Show typing indicator
    showTypingIndicator();
    
    try {
        // Send to API
        const response = await sendMessageToAPI(userMessage);
        
        removeTypingIndicator();
        
        // Add assistant response
        addMessageToUI(response.assistant_text, 'assistant');
        
        chatState.messages.push({
            role: 'assistant',
            text: response.assistant_text,
            timestamp: new Date()
        });
        
    } catch (error) {
        removeTypingIndicator();
        
        // Show error message
        const errorMsg = 'Sorry, I encountered an error. Please try again.';
        addMessageToUI(errorMsg, 'assistant');
    } finally {
        // Re-enable input
        messageInput.disabled = false;
        sendButton.disabled = false;
        messageInput.focus();
    }
}

// Handle language toggle
function handleLanguageToggle() {
    // Toggle between primary and secondary language
    if (chatState.displayLang === chatState.primaryLang) {
        chatState.displayLang = chatState.secondaryLang;
    } else {
        chatState.displayLang = chatState.primaryLang;
    }
    
    updateLanguageToggleDisplay();
    updateUrl({
        conversationId: chatState.conversationId,
        topic: chatState.topicId,
        mode: chatState.mode,
        primary: chatState.primaryLang,
        secondary: chatState.secondaryLang,
        display: chatState.displayLang
    });
    
    // TODO: In Milestone D, this will re-fetch and translate all messages
    console.log(`Display language toggled to: ${chatState.displayLang}`);
}

// Handle tutor mode toggle
function handleTutorMode() {
    if (chatState.mode === 'tutor') {
        // Exit tutor mode - go back to chat mode
        chatState.mode = 'chat';
        // Could reload conversation or just update mode
    } else {
        // Enter tutor mode - start fresh conversation
        if (confirm('Start a new conversation in Tutor Mode? You can ask questions about vocabulary and grammar.')) {
            chatState.mode = 'tutor';
            chatState.conversationId = null; // Start fresh
            chatState.messages = [];
            
            // Clear UI
            messagesContainer.innerHTML = `
                <div class="welcome-message">
                    <p>💡 <strong>Tutor Mode</strong></p>
                    <p>I'm here to answer your questions about words, grammar, and phrases. What would you like to know?</p>
                </div>
            `;
        } else {
            return; // User cancelled
        }
    }
    
    updateModeDisplay();
    updateUrl({
        conversationId: chatState.conversationId,
        topic: null, // Clear topic in tutor mode
        mode: chatState.mode,
        primary: chatState.primaryLang,
        secondary: chatState.secondaryLang,
        display: chatState.displayLang
    });
}

// Handle home button
function handleHomeButton() {
    window.location.href = '/';
}

// Auto-send topic message if topic was selected
async function handleTopicMessage(topicId) {
    if (!topicId) return;
    
    // Map topic IDs to starter messages
    const topicMessages = {
        travel: "I'd like to talk about travel and experiences.",
        food: "I'd like to discuss food and cuisine.",
        hobbies: "I'd like to talk about hobbies and interests.",
        work: "I'd like to discuss work and careers.",
        culture: "I'd like to explore culture and traditions."
    };
    
    const message = topicMessages[topicId] || `Let's talk about ${topicId}.`;
    
    // Wait a moment for UI to settle
    setTimeout(() => {
        messageInput.value = message;
        chatForm.dispatchEvent(new Event('submit'));
    }, 500);
}

// Check health endpoint on page load
async function checkHealth() {
    try {
        const response = await fetch('/health');
        const data = await response.json();
        
        if (data.ok) {
            statusIndicator.querySelector('.status-text').textContent = 'Ready';
            statusIndicator.querySelector('.status-dot').style.background = '#4caf50';
        }
    } catch (error) {
        statusIndicator.querySelector('.status-text').textContent = 'Offline';
        statusIndicator.querySelector('.status-dot').style.background = '#f44336';
        console.error('Health check failed:', error);
    }
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    // Get URL parameters
    const params = getUrlParams();
    
    // Initialize state from URL
    chatState.conversationId = params.conversationId;
    chatState.topicId = params.topic;
    chatState.mode = params.mode;
    chatState.primaryLang = params.primary;
    chatState.secondaryLang = params.secondary;
    chatState.displayLang = params.display || params.primary;
    
    // Update UI based on state
    updateLanguageToggleDisplay();
    updateModeDisplay();
    
    // Update welcome message for tutor mode
    if (chatState.mode === 'tutor') {
        const welcomeMsg = messagesContainer.querySelector('.welcome-message');
        if (welcomeMsg) {
            welcomeMsg.innerHTML = `
                <p>💡 <strong>Tutor Mode</strong></p>
                <p>I'm here to answer your questions about words, grammar, and phrases. What would you like to know?</p>
            `;
        }
    }
    
    // Check backend health
    checkHealth();
    
    // Set up event listeners
    chatForm.addEventListener('submit', handleSubmit);
    homeButton.addEventListener('click', handleHomeButton);
    languageToggle.addEventListener('click', handleLanguageToggle);
    tutorModeButton.addEventListener('click', handleTutorMode);
    
    // Focus input
    messageInput.focus();
    
    // Auto-send topic message if present
    if (params.topic) {
        handleTopicMessage(params.topic);
    }
    
    // TODO: In Milestone F, load conversation history from localStorage or API
});
