// Chat page functionality

// Chat state management
const chatState = {
    messages_primary: [],
    messages_secondary: [],
    messages_tutor: [],
    conversationId: null,
    primaryLang: 'es', // I'm learning Language
    secondaryLang: 'en', // I speak Language
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
const languageCheckbox = document.getElementById('languageCheckbox');
const currentLangSpan = document.getElementById('currentLang');
const targetLangSpan = document.getElementById('targetLang');

// Tutor pane elements
const tutorPane = document.getElementById('tutorPane');
const tutorPaneToggle = document.getElementById('tutorPaneToggle');
const closeTutorPane = document.getElementById('closeTutorPane');
const tutorMessagesContainer = document.getElementById('tutorMessagesContainer');
const tutorChatForm = document.getElementById('tutorChatForm');
const tutorMessageInput = document.getElementById('tutorMessageInput');
const tutorSendButton = document.getElementById('tutorSendButton');

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
    
    // For assistant messages, parse markdown; for user messages, use plain text
    if (role === 'assistant') {
        bubbleDiv.innerHTML = marked.parse(text);
    } else {
        bubbleDiv.textContent = text;
    }
    
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
    
    // Update checkbox state and label styling
    languageCheckbox.checked = !isDisplayingPrimary;
    
    // Highlight current display language
    if (isDisplayingPrimary) {
        currentLangSpan.classList.add('active');
        targetLangSpan.classList.remove('active');
    } else {
        currentLangSpan.classList.remove('active');
        targetLangSpan.classList.add('active');
    }
}

// Update mode indicator
function updateModeDisplay() {
    // Tutor mode button removed - function kept for compatibility
}

// Send message to API
async function sendMessageToAPI(userText) {
    try {
        const messagesPayload = [];
        // Prepare messages based on display language
        if (chatState.displayLang === chatState.primaryLang) {
            chatState.messages_primary.forEach(msg => {
                messagesPayload.push({
                    role: msg.role,
                    text: msg.text
                });
            });
        } else {
            chatState.messages_secondary.forEach(msg => {
                messagesPayload.push({
                    role: msg.role,
                    text: msg.text
                });
            });
        }

        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                conversation_id: chatState.conversationId,
                messages: messagesPayload,
                language: chatState.displayLang,
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
    console.log('handleSubmit called');
    // Log current display language
    console.log('Current display language:', chatState.displayLang);
    console.log('Primary language:', chatState.primaryLang);
    console.log('Secondary language:', chatState.secondaryLang);
    e.preventDefault();
    
    const userMessage = messageInput.value.trim();
    if (!userMessage) return;
    
    // Add user message to UI
    addMessageToUI(userMessage, 'user');
    
    if (chatState.displayLang === chatState.primaryLang) {
        // Store message in state
        chatState.messages_primary.push({
            role: 'user',
            text: userMessage,
            originalLang: chatState.primaryLang,
            timestamp: new Date()
        });
    } else {
        // Store message in state
        chatState.messages_secondary.push({
            role: 'user',
            text: userMessage,
            originalLang: chatState.secondaryLang,
            timestamp: new Date()
        });
    }
    
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
        
        if (chatState.displayLang === chatState.primaryLang) {

            chatState.messages_primary.push({
                role: 'assistant',
                text: response.assistant_text,
                timestamp: new Date()
            });
        } else {
            chatState.messages_secondary.push({
                role: 'assistant',
                text: response.assistant_text,
                timestamp: new Date()
            });
        }
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

// Translate messages to display language
async function translateMessages() {
    // Here displayLang is already toggled
    console.log('translateMessages called');
    console.log('current display language:', chatState.displayLang);
    if (chatState.displayLang === chatState.primaryLang && chatState.messages_secondary.length === 0) {
        return;
    }
    if (chatState.displayLang === chatState.secondaryLang && chatState.messages_primary.length === 0) {
        return;
    }
    
    // Show loading indicator
    messagesContainer.style.opacity = '0.6';
    messagesContainer.style.pointerEvents = 'none';

    if (chatState.messages_primary.length === chatState.messages_secondary.length || 
        ( chatState.displayLang === chatState.primaryLang && 
            chatState.messages_primary.length > chatState.messages_secondary.length ) ||
        ( chatState.displayLang === chatState.secondaryLang && 
            chatState.messages_secondary.length > chatState.messages_primary.length )    
    ) {
        // No need to translate if message counts are equal or there are already more messages in displayLang, just re-render
        rerenderMessages();
        messagesContainer.style.opacity = '1';
        messagesContainer.style.pointerEvents = 'auto';
        return;
    }
    try {
        let msgToTranslate = [];
        let source_lang = '';
        let target_lang = '';
        if (chatState.displayLang === chatState.primaryLang) {
            // Translate from secondary to primary
            const idx = chatState.messages_primary.length;
            msgToTranslate = chatState.messages_secondary.slice(idx);
            source_lang = chatState.secondaryLang;
            target_lang = chatState.primaryLang;
        }
        else {
            // Translate from primary to secondary
            const idx = chatState.messages_secondary.length;
            msgToTranslate = chatState.messages_primary.slice(idx);
            source_lang = chatState.primaryLang;
            target_lang = chatState.secondaryLang;
        }
        // Collect all message texts
        const textsToTranslate = msgToTranslate.map(msg => msg.text);
        
        // Call translation API
        const response = await fetch('/api/translate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: textsToTranslate,
                source_lang: source_lang,
                target_lang: target_lang
            })
        });
        
        if (!response.ok) {
            throw new Error('Translation failed');
        }
        
        const data = await response.json();
        const translatedTexts = data.translated_text;

        // Check if all messages were translated
        if (translatedTexts.length !== msgToTranslate.length) {
            throw new Error('Translation API returned mismatched number of messages');
        }
        
        // Update messages with translated text
        for (let i = 0; i < translatedTexts.length; i++) {
            if (chatState.displayLang === chatState.primaryLang) {
                chatState.messages_primary.push({
                    role: msgToTranslate[i].role,
                    text: translatedTexts[i],
                    timestamp: msgToTranslate[i].timestamp
                });
            }
            else {
                chatState.messages_secondary.push({
                    role: msgToTranslate[i].role,
                    text: translatedTexts[i],
                    timestamp: msgToTranslate[i].timestamp
                });
            }
        }
        
        // Re-render all messages
        rerenderMessages();
    } catch (error) {
        console.error('Translation error:', error);
        // ADD SOME ERROR HANDLING HERE
    } finally {
        // Remove loading state
        messagesContainer.style.opacity = '1';
        messagesContainer.style.pointerEvents = 'auto';
    }
}

// Re-render all messages in the UI
function rerenderMessages() {
    console.log('rerenderMessages called');
    let hasMessages = false;
    // Clear message container but keep welcome message logic
    if (chatState.displayLang === chatState.primaryLang) {
        hasMessages = chatState.messages_primary.length > 0;
    } else {
        hasMessages = chatState.messages_secondary.length > 0;
    }
    messagesContainer.innerHTML = '';
    
    if (!hasMessages) {
        const welcomeDiv = document.createElement('div');
        welcomeDiv.className = 'welcome-message';
        if (chatState.mode === 'tutor') {
            welcomeDiv.innerHTML = `
                <p>💡 <strong>Tutor Mode</strong></p>
                <p>I'm here to answer your questions about words, grammar, and phrases. What would you like to know?</p>
            `;
        } else {
            welcomeDiv.innerHTML = `
                <p>👋 Welcome! I'm your language tutor. Start chatting to practice your language skills.</p>
            `;
        }
        messagesContainer.appendChild(welcomeDiv);
        return;
    }
    
    // Render each message
    if (chatState.displayLang === chatState.primaryLang) {

        chatState.messages_primary.forEach(msg => {
            const text = msg.text;
            const timestamp = msg.timestamp ? new Date(msg.timestamp) : new Date();
            const messageBubble = createMessageBubble(text, msg.role, timestamp);
            messagesContainer.appendChild(messageBubble);
        });
    } else {

        chatState.messages_secondary.forEach(msg => {
            const text = msg.text;
            const timestamp = msg.timestamp ? new Date(msg.timestamp) : new Date();
            const messageBubble = createMessageBubble(text, msg.role, timestamp);
            messagesContainer.appendChild(messageBubble);
        });
    }
    
    // Maintain scroll position (scroll to bottom)
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Handle language toggle
async function handleLanguageToggle() {
    console.log('handleLanguageToggle called');
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
    
    // Translate and re-render all messages
    await translateMessages();
}

// Toggle tutor pane visibility
function toggleTutorPane() {
    const isActive = tutorPane.classList.toggle('active');
    tutorPaneToggle.classList.toggle('active', isActive);
    
    if (isActive) {
        tutorMessageInput.focus();
    } else {
        messageInput.focus();
    }
}

// Close tutor pane
function closeTutorPaneHandler() {
    tutorPane.classList.remove('active');
    tutorPaneToggle.classList.remove('active');
    messageInput.focus();
}

// Add message to tutor UI
function addTutorMessage(text, role) {
    // Remove welcome message if it exists
    const welcomeMessage = tutorMessagesContainer.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.remove();
    }
    
    const messageBubble = createMessageBubble(text, role);
    tutorMessagesContainer.appendChild(messageBubble);
    
    // Scroll to bottom
    tutorMessagesContainer.scrollTop = tutorMessagesContainer.scrollHeight;
    
    return messageBubble;
}

// Show typing indicator in tutor pane
function showTutorTypingIndicator() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant loading';
    messageDiv.id = 'tutorTypingIndicator';
    
    const bubbleDiv = document.createElement('div');
    bubbleDiv.className = 'message-bubble';
    
    const typingIndicator = document.createElement('div');
    typingIndicator.className = 'typing-indicator';
    typingIndicator.innerHTML = '<span></span><span></span><span></span>';
    
    bubbleDiv.appendChild(typingIndicator);
    messageDiv.appendChild(bubbleDiv);
    tutorMessagesContainer.appendChild(messageDiv);
    
    tutorMessagesContainer.scrollTop = tutorMessagesContainer.scrollHeight;
}

// Remove typing indicator from tutor pane
function removeTutorTypingIndicator() {
    const indicator = document.getElementById('tutorTypingIndicator');
    if (indicator) {
        indicator.remove();
    }
}

// Handle tutor chat submission
async function handleTutorSubmit(e) {
    e.preventDefault();
    
    const tutorMessage = tutorMessageInput.value.trim();
    if (!tutorMessage) return;
    
    // Add user message to tutor UI
    addTutorMessage(tutorMessage, 'user');
    
    // Clear input
    tutorMessageInput.value = '';
    
    // Disable input while processing
    tutorMessageInput.disabled = true;
    tutorSendButton.disabled = true;
    
    // Show typing indicator
    showTutorTypingIndicator();
    
    try {
        // Send to API with mode='tutor'
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                conversation_id: chatState.conversationId,
                user_text: tutorMessage,
                primary_lang: chatState.primaryLang,
                secondary_lang: chatState.secondaryLang,
                display_lang: chatState.displayLang,
                mode: 'tutor'
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to send message');
        }
        
        const data = await response.json();
        
        removeTutorTypingIndicator();
        
        // Add tutor response
        addTutorMessage(data.assistant_text, 'assistant');
        
    } catch (error) {
        removeTutorTypingIndicator();
        
        // Show error message
        const errorMsg = 'Sorry, I encountered an error. Please try again.';
        addTutorMessage(errorMsg, 'assistant');
    } finally {
        // Re-enable input
        tutorMessageInput.disabled = false;
        tutorSendButton.disabled = false;
        tutorMessageInput.focus();
    }
}

// Handle tutor mode toggle
function handleTutorMode() {
    if (chatState.mode === 'tutor') {
        // Exit tutor mode - go back to chat mode
        chatState.mode = 'chat';
        chatState.conversationId = null; // Start fresh chat
        chatState.messages = [];
        
        // Reset UI to regular chat welcome
        messagesContainer.innerHTML = `
            <div class="welcome-message">
                <p>👋 Welcome! I'm your language tutor. Start chatting to practice your language skills.</p>
            </div>
        `;
    } else {
        // Enter tutor mode - start fresh conversation immediately
        chatState.mode = 'tutor';
        chatState.conversationId = null; // Start fresh
        chatState.messages = [];
        
        // Clear UI and show tutor welcome
        messagesContainer.innerHTML = `
            <div class="welcome-message">
                <p>💡 <strong>AI Tutor</strong></p>
                <p>I am AI tutor, tell me your questions about the conversation.</p>
            </div>
        `;
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
    
    // Save the state change
    saveConversationToStorage();
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
document.addEventListener('DOMContentLoaded', async () => {
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
                <p>💡 <strong>AI Tutor</strong></p>
                <p>I am AI tutor, tell me your questions about the conversation.</p>
            `;
        }
    }
    
    // Check backend health
    checkHealth();
    
    // Set up event listeners
    chatForm.addEventListener('submit', handleSubmit);
    homeButton.addEventListener('click', handleHomeButton);
    languageCheckbox.addEventListener('change', handleLanguageToggle);
    
    // Tutor pane event listeners
    tutorPaneToggle.addEventListener('click', toggleTutorPane);
    closeTutorPane.addEventListener('click', closeTutorPaneHandler);
    tutorChatForm.addEventListener('submit', handleTutorSubmit);
    
    // Focus input
    messageInput.focus();
    
    // Load conversation from database if conversation ID exists (Milestone H3)
    if (params.conversationId) {
        await loadConversationFromDatabase(params.conversationId);
    }
    
    // Auto-send topic message if present (only if no messages loaded)
    if (params.topic && chatState.messages.length === 0) {
        handleTopicMessage(params.topic);
    }
});

// LocalStorage Functions (Milestone D3 & F2)
function saveConversationToStorage() {
    console.log('saveConversationToStorage called');
    if (!chatState.conversationId) return;
    
    const conversationData = {
        conversationId: chatState.conversationId,
        primaryLang: chatState.primaryLang,
        secondaryLang: chatState.secondaryLang,
        displayLang: chatState.displayLang,
        mode: chatState.mode,
        topicId: chatState.topicId,
        messages: chatState.messages,
        lastUpdated: new Date().toISOString()
    };
    
    try {
        localStorage.setItem(`conversation_${chatState.conversationId}`, JSON.stringify(conversationData));
        // Also save language preferences
        localStorage.setItem('languagePreferences', JSON.stringify({
            primary: chatState.primaryLang,
            secondary: chatState.secondaryLang
        }));
    } catch (error) {
        console.error('Failed to save to localStorage:', error);
    }
}

// Load conversation from database (Milestone H3)
async function loadConversationFromDatabase(conversationId) {
    try {
        const response = await fetch(`/api/conversations/${conversationId}`);
        
        if (!response.ok) {
            if (response.status === 404) {
                console.warn('Conversation not found');
                // Redirect to home if conversation doesn't exist
                window.location.href = '/?error=conversation_not_found';
                return false;
            }
            throw new Error('Failed to load conversation');
        }
        
        const data = await response.json();
        
        // Update chat state with conversation data
        chatState.primaryLang = data.primary_lang;
        chatState.secondaryLang = data.secondary_lang;
        chatState.mode = data.mode;
        
        // Load messages
        chatState.messages = data.messages.map(msg => ({
            role: msg.role,
            text: msg.text,
            originalLang: msg.original_lang,
            timestamp: new Date(msg.timestamp),
            displayText: msg.text // Will be translated if needed
        }));
        
        // Re-render messages
        rerenderMessages();
        
        // Update UI based on loaded state
        updateLanguageToggleDisplay();
        updateModeDisplay();
        
        return true;
        
    } catch (error) {
        console.error('Error loading conversation:', error);
        return false;
    }
}

function loadConversationFromStorage() {
    const params = getUrlParams();
    
    // Try to load conversation if ID is in URL
    if (params.conversationId) {
        try {
            const stored = localStorage.getItem(`conversation_${params.conversationId}`);
            if (stored) {
                const data = JSON.parse(stored);
                chatState.messages = data.messages || [];
                
                // Re-render messages
                if (chatState.messages.length > 0) {
                    rerenderMessages();
                }
            }
        } catch (error) {
            console.error('Failed to load from localStorage:', error);
        }
    }
    
    // Load language preferences if available
    try {
        const prefs = localStorage.getItem('languagePreferences');
        if (prefs && !params.primary) {
            const { primary, secondary } = JSON.parse(prefs);
            chatState.primaryLang = primary;
            chatState.secondaryLang = secondary;
            if (!params.display) {
                chatState.displayLang = primary;
            }
            updateLanguageToggleDisplay();
        }
    } catch (error) {
        console.error('Failed to load preferences:', error);
    }
}

// Insights Modal Functions (Milestone E2)
function openInsightsModal() {
    insightsModal.classList.add('show');
    updateInsightsContent();
}

function closeInsightsModal() {
    insightsModal.classList.remove('show');
}

function updateInsightsContent() {
    const vocabularyList = document.getElementById('vocabularyList');
    const patternsList = document.getElementById('patternsList');
    const progressStats = document.getElementById('progressStats');
    
    if (chatState.messages.length === 0) {
        // Show placeholder messages
        vocabularyList.innerHTML = '<p class="placeholder-text">Continue chatting to discover new vocabulary!</p>';
        patternsList.innerHTML = '<p class="placeholder-text">Keep practicing to identify common sentence structures!</p>';
        progressStats.innerHTML = '<p class="placeholder-text">Your learning stats will appear here as you chat more.</p>';
    } else {
        // Show stubbed insights based on conversation
        const messageCount = chatState.messages.length;
        const userMessages = chatState.messages.filter(m => m.role === 'user').length;
        
        vocabularyList.innerHTML = `
            <p class="placeholder-text">📚 Vocabulary insights coming in Phase 2!</p>
            <p class="placeholder-text" style="margin-top: 10px; font-size: 0.9em;">
                (Will analyze your ${userMessages} messages for key words and phrases)
            </p>
        `;
        
        patternsList.innerHTML = `
            <p class="placeholder-text">🔍 Sentence pattern analysis coming in Phase 2!</p>
            <p class="placeholder-text" style="margin-top: 10px; font-size: 0.9em;">
                (Will identify common grammatical structures you're using)
            </p>
        `;
        
        progressStats.innerHTML = `
            <div style="text-align: center;">
                <p style="margin: 0; font-size: 2em; color: #667eea; font-weight: bold;">${messageCount}</p>
                <p style="margin: 5px 0 0 0; color: #6c757d;">Total Messages</p>
                <p style="margin: 15px 0 0 0; font-size: 1.5em; color: #764ba2; font-weight: bold;">${userMessages}</p>
                <p style="margin: 5px 0 0 0; color: #6c757d;">Your Messages</p>
            </div>
        `;
    }
}
