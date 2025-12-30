// Chat state management
const chatState = {
    messages: [],
    conversationId: null
};

// DOM elements
const messagesContainer = document.getElementById('messagesContainer');
const chatForm = document.getElementById('chatForm');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const statusIndicator = document.getElementById('statusIndicator');

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

// Handle form submission
async function handleSubmit(e) {
    e.preventDefault();
    
    const userMessage = messageInput.value.trim();
    if (!userMessage) return;
    
    // Add user message to UI
    addMessageToUI(userMessage, 'user');
    
    // Store message in local state
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
    
    // Simulate assistant response (stubbed for now - will be replaced in B2)
    setTimeout(() => {
        removeTypingIndicator();
        
        // Stub response - will be replaced with actual API call in Milestone B2
        const assistantMessage = "This is a stubbed response. The actual tutor will be connected in the next milestone!";
        
        addMessageToUI(assistantMessage, 'assistant');
        
        chatState.messages.push({
            role: 'assistant',
            text: assistantMessage,
            timestamp: new Date()
        });
        
        // Re-enable input
        messageInput.disabled = false;
        sendButton.disabled = false;
        messageInput.focus();
    }, 1500);
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
    checkHealth();
    chatForm.addEventListener('submit', handleSubmit);
    messageInput.focus();
});
