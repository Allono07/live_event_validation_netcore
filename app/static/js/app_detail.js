// WebSocket connection and live updates
let socket;

// Initialize WebSocket connection
function initSocket() {
    socket = io();
    
    socket.on('connect', function() {
        console.log('Connected to validation server');
        updateConnectionStatus('Connected', 'success');
        
        // Join the room for this app
        socket.emit('join', { app_id: APP_ID });
    });
    
    socket.on('disconnect', function() {
        console.log('Disconnected from server');
        updateConnectionStatus('Disconnected', 'danger');
    });
    
    socket.on('joined', function(data) {
        console.log('Joined room:', data.app_id);
    });
    
    socket.on('validation_update', function(data) {
        console.log('Validation update:', data);
        if (data.app_id === APP_ID) {
            addLogToTable(data.log);
            updateStats();
        }
    });
}

// Update connection status badge
function updateConnectionStatus(text, type) {
    const badge = document.getElementById('connectionStatus');
    badge.textContent = text;
    badge.className = `badge bg-${type}`;
}

// Add new log entry to table
function addLogToTable(log) {
    const table = document.getElementById('logsTable');
    const row = document.createElement('tr');
    row.className = 'new-log';
    
    const timestamp = new Date(log.timestamp).toLocaleString();
    const status = log.is_valid ? 'PASSED' : 'FAILED';
    const statusClass = log.is_valid ? 'log-passed' : 'log-failed';
    const message = log.validation_message || 'Validation completed';
    
    row.innerHTML = `
        <td>${timestamp}</td>
        <td>${log.event_name}</td>
        <td class="${statusClass}">${status}</td>
        <td>${message}</td>
    `;
    
    // Insert at the top
    table.insertBefore(row, table.firstChild);
    
    // Keep only last 50 entries
    while (table.children.length > 50) {
        table.removeChild(table.lastChild);
    }
}

// Fetch and update stats
function updateStats() {
    fetch(`/app/${APP_ID}/stats`)
        .then(response => response.json())
        .then(data => {
            document.getElementById('totalLogs').textContent = data.total;
            document.getElementById('passedLogs').textContent = data.passed;
            document.getElementById('failedLogs').textContent = data.failed;
            document.getElementById('successRate').textContent = data.success_rate + '%';
        })
        .catch(error => console.error('Error fetching stats:', error));
}

// Load initial logs
function loadInitialLogs() {
    fetch(`/app/${APP_ID}/logs?limit=20`)
        .then(response => response.json())
        .then(data => {
            const table = document.getElementById('logsTable');
            table.innerHTML = '';
            
            data.logs.forEach(log => {
                addLogToTable(log);
            });
        })
        .catch(error => console.error('Error loading logs:', error));
}

// Copy API endpoint to clipboard
function copyToClipboard() {
    const endpoint = document.getElementById('apiEndpoint').textContent;
    navigator.clipboard.writeText(endpoint).then(() => {
        alert('API endpoint copied to clipboard!');
    }).catch(err => {
        console.error('Failed to copy:', err);
    });
}

// Copy App ID to clipboard
function copyAppId() {
    navigator.clipboard.writeText(APP_ID).then(() => {
        alert('App ID copied to clipboard!');
    }).catch(err => {
        console.error('Failed to copy:', err);
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initSocket();
    updateStats();
    loadInitialLogs();
    
    // Refresh stats every 5 seconds
    setInterval(updateStats, 5000);
});
