// Check health endpoint on page load
async function checkHealth() {
    const statusDiv = document.getElementById('status');
    
    try {
        const response = await fetch('/health');
        const data = await response.json();
        
        if (data.ok) {
            statusDiv.className = 'status success';
            statusDiv.innerHTML = `
                <p><strong>✓ Application is running!</strong></p>
                <p>Health check: OK</p>
                <p>Milestone A complete: Project skeleton deployed</p>
            `;
        } else {
            throw new Error('Health check returned false');
        }
    } catch (error) {
        statusDiv.className = 'status error';
        statusDiv.innerHTML = `
            <p><strong>✗ Error</strong></p>
            <p>Failed to connect to backend: ${error.message}</p>
        `;
    }
}

// Run health check when page loads
document.addEventListener('DOMContentLoaded', checkHealth);
