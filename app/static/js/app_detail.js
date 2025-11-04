// WebSocket connection and live updates
let socket;
let userEventsCount = 0;
let systemEventsCount = 0;
let allValidationResults = []; // Store all validation results for download
let currentFilteredResults = null; // If filters are applied, hold filtered subset

// Get status CSS class based on validation status
function getStatusClass(status) {
    if (status === 'Valid') return 'status-valid';
    if (status === 'Invalid/Wrong datatype/value') return 'status-invalid';
    if (status === 'Payload value is Empty') return 'status-empty';
    if (status === 'Extra key present in the log') return 'status-extra';
    if (status === 'Payload not present in the log') return 'status-notpresent';
    if (status === 'Extra event (not in sheet)') return 'status-extra-event';
    if (status === 'Payload from extra event') return 'status-payload-from-extra';
    return '';
}

// Convert Unix timestamp (milliseconds) to readable format
function formatTimestamp(timestamp) {
    // Check if timestamp is Unix milliseconds (13 digits)
    if (typeof timestamp === 'number' && timestamp > 1000000000000) {
        const date = new Date(timestamp);
        return date.toLocaleString();
    }
    // Check if it's a string Unix timestamp
    else if (typeof timestamp === 'string' && timestamp.length === 13 && !isNaN(timestamp)) {
        const date = new Date(parseInt(timestamp));
        return date.toLocaleString();
    }
    // Otherwise assume it's already formatted or ISO string
    else {
        const date = new Date(timestamp);
        return date.toLocaleString();
    }
}

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
            // Increment total log count for Load More button
            totalLogs++;
            updateLoadMoreButton();
        }
    });
}

// Update connection status badge
function updateConnectionStatus(text, type) {
    const badge = document.getElementById('connectionStatus');
    if (!badge) return;
    badge.textContent = text;
    badge.className = `badge bg-${type}`;
}

// Check if event payload has eventId === 0
function isUserEvent(log) {
    try {
        // First check in validation_results if available
        if (log.validation_results && Array.isArray(log.validation_results)) {
            for (let result of log.validation_results) {
                if (result.key && result.key.toLowerCase() === 'eventid') {
                    const value = result.value;
                    return value === 0 || value === '0';
                }
            }
        }
        
    // Fallback: check in payload
    let payload = log.payload;
        if (typeof payload === 'string') {
            try { payload = JSON.parse(payload); } catch(e) { /* ignore */ }
        }
        
        if (payload && ('eventId' in payload || 'eventid' in payload)) {
            return (payload.eventId === 0 || payload.eventId === '0') || (payload.eventid === 0 || payload.eventid === '0');
        }
        
        // Default to user event if eventId not found
        return true;
    } catch (e) {
        console.error('Error checking user event:', e);
        return true;
    }
}

// Get eventId from payload
function getEventId(log) {
    try {
        // First check in validation_results
        if (log.validation_results && Array.isArray(log.validation_results)) {
            for (let result of log.validation_results) {
                if (result.key && result.key.toLowerCase() === 'eventid') {
                    return result.value;
                }
            }
        }
        
    // Fallback: check in payload
    let payload = log.payload;
        if (typeof payload === 'string') {
            try { payload = JSON.parse(payload); } catch(e) { /* ignore */ }
        }
        if (!payload) return 'N/A';
        return payload.eventId || payload.eventid || 'N/A';
    } catch (e) {
        return 'N/A';
    }
}

// Helper function to fill checkbox container with checkboxes
function fillCheckboxContainer(container, values, searchInputId = null) {
    if (!container) return;
    container.innerHTML = '';
    
    const sortedValues = Array.from(values).sort();
    
    sortedValues.forEach(value => {
        const checkDiv = document.createElement('div');
        checkDiv.className = 'form-check';
        
        const checkboxId = `${container.id}-${value.replace(/[^a-zA-Z0-9]/g, '_')}`;
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'form-check-input filter-checkbox';
        checkbox.id = checkboxId;
        checkbox.value = value;
        
        const label = document.createElement('label');
        label.className = 'form-check-label';
        label.htmlFor = checkboxId;
        label.textContent = value;
        
        checkDiv.appendChild(checkbox);
        checkDiv.appendChild(label);
        container.appendChild(checkDiv);
    });
}

// Helper function to attach search listener to a container
function attachEventSearchListener(searchInput, container) {
    if (!searchInput || !container) return;
    
    searchInput.addEventListener('input', function() {
        const q = this.value.trim().toLowerCase();
        const checkboxes = container.querySelectorAll('.form-check');
        
        checkboxes.forEach(checkDiv => {
            const label = checkDiv.querySelector('label');
            if (label) {
                const text = label.textContent.toLowerCase();
                checkDiv.style.display = text.includes(q) ? '' : 'none';
            }
        });
    });
}

// Populate filter dropdowns with distinct values from allValidationResults AND database
function populateFilterOptions() {
    // Collect distinct values from in-memory results
    const evSet = new Set();
    const fieldSet = new Set();
    const expectedSet = new Set();
    const receivedSet = new Set();
    const statusSet = new Set();

    allValidationResults.forEach(r => {
        if (r.eventName) evSet.add(r.eventName);
        if (r.key) fieldSet.add(r.key);
        if (r.expectedType) expectedSet.add(r.expectedType);
        if (r.receivedType) receivedSet.add(r.receivedType);
        if (r.validationStatus) statusSet.add(r.validationStatus);
    });

    // Also fetch all event names from database
    fetch(`/app/${APP_ID}/event-names`)
        .then(response => response.json())
        .then(data => {
            if (data.event_names) {
                data.event_names.forEach(name => evSet.add(name));
            }
            
            // Populate dropdowns with merged data
            fillCheckboxContainer(
                document.getElementById('filterEventContainer'),
                evSet
            );
            fillCheckboxContainer(
                document.getElementById('filterFieldContainer'),
                fieldSet
            );
            fillCheckboxContainer(
                document.getElementById('filterExpectedContainer'),
                expectedSet
            );
            fillCheckboxContainer(
                document.getElementById('filterReceivedContainer'),
                receivedSet
            );
            fillCheckboxContainer(
                document.getElementById('filterStatusContainer'),
                statusSet
            );
            
            // Attach search listener to event search input
            attachEventSearchListener(
                document.getElementById('filterEventSearch'),
                document.getElementById('filterEventContainer')
            );
        })
        .catch(error => console.error('Error fetching event names:', error));
}

// Add new log entry to appropriate table
function addLogToTable(log) {
    const isUser = isUserEvent(log);
    const tableId = isUser ? 'userLogsTable' : 'systemLogsTable';
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const timestamp = formatTimestamp(log.created_at || log.timestamp);
    
    if (isUser && log.validation_results && Array.isArray(log.validation_results)) {
        // User events - render a header row (timestamp + event name) and then field rows
        // Build a fragment so header appears above the field rows
        const frag = document.createDocumentFragment();
        const header = document.createElement('tr');
        header.className = 'event-header';
        header.innerHTML = `
            <td colspan="2"><strong>${timestamp} \u00A0 ${log.event_name || ''}</strong></td>
            <td colspan="5"></td>
        `;
        frag.appendChild(header);

        // Add each field row into the fragment (in the order provided)
        log.validation_results.forEach((result, index) => {
            const row = document.createElement('tr');
            row.className = 'event-field-row';
            const statusClass = getStatusClass(result.validationStatus);
            // Column structure must match header: Timestamp | Event Name | Field Name | Value | Expected Type | Received Type | Status
            // First empty cell is Timestamp column (already shown in header)
            // Second empty cell is Event Name column (already shown in header)
            row.innerHTML = `
                <td></td>
                <td></td>
                <td>${result.key || 'N/A'}</td>
                <td>${result.value !== null && result.value !== undefined ? result.value : 'null'}</td>
                <td>${result.expectedType || 'N/A'}</td>
                <td>${result.receivedType || 'N/A'}</td>
                <td class="${statusClass}">${result.validationStatus || 'Unknown'}</td>
            `;
            // For first field row, append event name as hidden text node (won't affect layout, searchable by Cmd+F)
            if (index === 0) {
                const hiddenSpan = document.createElement('span');
                hiddenSpan.style.cssText = 'position: absolute; left: -9999px; width: 1px; height: 1px; overflow: hidden;';
                hiddenSpan.textContent = log.event_name || '';
                row.appendChild(hiddenSpan);
            }
            frag.appendChild(row);

            // Store validation result for download and filtering
            allValidationResults.unshift({
                timestamp: timestamp,
                eventName: log.event_name || '',
                key: result.key,
                value: result.value,
                expectedType: result.expectedType,
                receivedType: result.receivedType,
                validationStatus: result.validationStatus,
                comment: result.comment || ''
            });
        });

        // Prepend the fragment so the header + rows appear at top in correct order
        table.insertBefore(frag, table.firstChild);

        userEventsCount++;
        const userBadge = document.getElementById('userEventsCount');
        if (userBadge) userBadge.textContent = userEventsCount;

        // Refresh filter option lists
        populateFilterOptions();
    } else if (!isUser) {
        // System events table (no validation)
        const row = document.createElement('tr');
        row.className = 'new-log';
        
        const eventId = getEventId(log);
        const details = log.validation_message || 'System event (not validated)';
        
        row.innerHTML = `
            <td>${timestamp}</td>
            <td>${log.event_name || ''}</td>
            <td><span class="badge bg-secondary">${eventId}</span></td>
            <td>${details}</td>
        `;
        
        table.insertBefore(row, table.firstChild);
        
        systemEventsCount++;
        const sysBadge = document.getElementById('systemEventsCount');
        if (sysBadge) sysBadge.textContent = systemEventsCount;
    }
    
    // Keep only last 200 entries per table (since we now have multiple rows per event)
    while (table.children.length > 200) {
        table.removeChild(table.lastChild);
    }
    
    // Keep only last 1000 validation results in memory
    if (allValidationResults.length > 1000) {
        allValidationResults = allValidationResults.slice(0, 1000);
    }
}

// Fetch and update stats
function updateStats() {
    fetch(`/app/${APP_ID}/stats`)
        .then(response => response.json())
        .then(data => {
            const total = data.total || 0;
            // backend returns 'valid' and 'invalid'
            const passed = data.valid || 0;
            const failed = data.invalid || 0;
            document.getElementById('totalLogs').textContent = total;
            document.getElementById('passedLogs').textContent = passed;
            document.getElementById('failedLogs').textContent = failed;
            const successRate = total > 0 ? Math.round((passed / total) * 100) : 0;
            document.getElementById('successRate').textContent = successRate + '%';
        })
        .catch(error => console.error('Error fetching stats:', error));
}

// Load initial logs
// Pagination state
let currentPage = 1;
let totalLogs = 0;
const logsPerPage = 50;

function loadInitialLogs() {
    currentPage = 1;
    fetch(`/app/${APP_ID}/logs?page=1&limit=${logsPerPage}`)
        .then(response => response.json())
        .then(data => {
            const userTable = document.getElementById('userLogsTable');
            const systemTable = document.getElementById('systemLogsTable');
            if (!userTable || !systemTable) return;
            userTable.innerHTML = '';
            systemTable.innerHTML = '';
            userEventsCount = 0;
            systemEventsCount = 0;
            allValidationResults = [];
            
            totalLogs = data.total || 0;
            
            // Sort logs oldest -> newest so that when we prepend each event the newest ends up on top
            data.logs.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));

            data.logs.forEach(log => {
                addLogToTable(log);
            });
            
            // Update Load More button visibility
            updateLoadMoreButton();
            
            // Populate filter options from loaded logs
            populateFilterOptions();
        })
        .catch(error => console.error('Error loading logs:', error));
}

function loadMoreLogs() {
    currentPage++;
    fetch(`/app/${APP_ID}/logs?page=${currentPage}&limit=${logsPerPage}`)
        .then(response => response.json())
        .then(data => {
            // Sort logs oldest -> newest
            data.logs.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));

            data.logs.forEach(log => {
                addLogToTable(log);
            });
            
            // Update Load More button visibility
            updateLoadMoreButton();
            
            // Refresh filter options
            populateFilterOptions();
        })
        .catch(error => console.error('Error loading more logs:', error));
}

function updateLoadMoreButton() {
    const btn = document.getElementById('loadMoreBtn');
    if (!btn) return;
    
    // Show button only if there are more logs to load
    const logsLoaded = currentPage * logsPerPage;
    if (logsLoaded < totalLogs) {
        btn.style.display = 'block';
    } else {
        btn.style.display = 'none';
    }
}

// Download validation results
function downloadResults() {
    if (allValidationResults.length === 0) {
        alert('No validation results to download');
        return;
    }
    const payloadResults = currentFilteredResults || allValidationResults;

    fetch(`/app/${APP_ID}/download-report`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            results: payloadResults
        })
    })
    .then(response => response.blob())
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `validation_results_${APP_ID}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
    })
    .catch(error => {
        console.error('Error downloading results:', error);
        alert('Error downloading results');
    });
}

// Calculate which events have 100% valid payload fields
function calculateFullyValidEvents() {
    const eventGroups = {};
    
    allValidationResults.forEach(result => {
        if (!result.eventName) return;
        if (!eventGroups[result.eventName]) {
            eventGroups[result.eventName] = [];
        }
        eventGroups[result.eventName].push(result);
    });
    
    const fullyValid = [];
    Object.keys(eventGroups).forEach(eventName => {
        const results = eventGroups[eventName];
        const allValid = results.every(r => r.validationStatus === 'Valid');
        if (allValid && results.length > 0) {
            fullyValid.push(eventName);
        }
    });
    
    return fullyValid;
}

// Update event coverage info
function updateCoverage() {
    fetch(`/app/${APP_ID}/coverage`)
        .then(response => response.json())
        .then(data => {
            // Update coverage counts
            document.getElementById('coveredCount').textContent = data.captured || 0;
            document.getElementById('missingCount').textContent = data.missing || 0;
            document.getElementById('totalSheetCount').textContent = data.total || 0;
            
            // Re-fetch total logs count to update Load More button visibility
            fetch(`/app/${APP_ID}/logs?page=1&limit=1`)
                .then(response => response.json())
                .then(logsData => {
                    totalLogs = logsData.total || 0;
                    updateLoadMoreButton();
                })
                .catch(err => console.error('Error fetching total logs:', err));
            
            // Update missing events list
            const missingList = document.getElementById('missingEventsList');
            if (missingList) {
                if (data.missing_events && data.missing_events.length > 0) {
                    missingList.innerHTML = data.missing_events
                        .map(e => `<li><small>${e}</small></li>`)
                        .join('');
                } else {
                    missingList.innerHTML = '<li><small class="text-success">All events captured!</small></li>';
                }
            }
            
            // Update fully valid events
            const fullyValid = calculateFullyValidEvents();
            const fullyValidList = document.getElementById('fullyValidEventsList');
            if (fullyValidList) {
                if (fullyValid.length > 0) {
                    fullyValidList.innerHTML = fullyValid
                        .map(e => `<span class="badge bg-success me-1 mb-1">${e}</span>`)
                        .join('');
                } else {
                    fullyValidList.innerHTML = '<small class="text-muted">No fully valid events yet</small>';
                }
            }
        })
        .catch(error => console.error('Error updating coverage:', error));
}

// Apply filters based on per-column selects/inputs placed in the table header
function applyFilters() {
    // Get all checked event checkboxes
    const eventContainer = document.getElementById('filterEventContainer');
    const selectedEvents = new Set();
    if (eventContainer) {
        const checked = eventContainer.querySelectorAll('input[type="checkbox"]:checked');
        checked.forEach(cb => selectedEvents.add(cb.value));
    }

    // Get all checked field checkboxes
    const fieldContainer = document.getElementById('filterFieldContainer');
    const selectedFields = new Set();
    if (fieldContainer) {
        const checked = fieldContainer.querySelectorAll('input[type="checkbox"]:checked');
        checked.forEach(cb => selectedFields.add(cb.value));
    }

    // Get all checked expected type checkboxes
    const expectedContainer = document.getElementById('filterExpectedContainer');
    const selectedExpected = new Set();
    if (expectedContainer) {
        const checked = expectedContainer.querySelectorAll('input[type="checkbox"]:checked');
        checked.forEach(cb => selectedExpected.add(cb.value));
    }

    // Get all checked received type checkboxes
    const receivedContainer = document.getElementById('filterReceivedContainer');
    const selectedReceived = new Set();
    if (receivedContainer) {
        const checked = receivedContainer.querySelectorAll('input[type="checkbox"]:checked');
        checked.forEach(cb => selectedReceived.add(cb.value));
    }

    // Get all checked status checkboxes
    const statusContainer = document.getElementById('filterStatusContainer');
    const selectedStatus = new Set();
    if (statusContainer) {
        const checked = statusContainer.querySelectorAll('input[type="checkbox"]:checked');
        checked.forEach(cb => selectedStatus.add(cb.value));
    }

    // Get value search input
    const valueInput = document.getElementById('filterValueInput');
    const valueQ = valueInput && valueInput.value ? valueInput.value.trim().toLowerCase() : '';

    // Filter results: OR logic within each column, AND between columns
    currentFilteredResults = allValidationResults.filter(r => {
        // Event name: if selections exist, must match one of them
        if (selectedEvents.size > 0 && !selectedEvents.has(r.eventName)) return false;
        // Field name: if selections exist, must match one of them
        if (selectedFields.size > 0 && !selectedFields.has(r.key)) return false;
        // Expected type: if selections exist, must match one of them
        if (selectedExpected.size > 0 && !selectedExpected.has(r.expectedType)) return false;
        // Received type: if selections exist, must match one of them
        if (selectedReceived.size > 0 && !selectedReceived.has(r.receivedType)) return false;
        // Status: if selections exist, must match one of them
        if (selectedStatus.size > 0 && !selectedStatus.has(r.validationStatus)) return false;
        // Value search: if entered, value must include it
        if (valueQ && !((r.value || '').toString().toLowerCase().includes(valueQ))) return false;
        return true;
    });

    // Re-render user table using currentFilteredResults
    const userTable = document.getElementById('userLogsTable');
    if (!userTable) return;
    userTable.innerHTML = '';

    const groups = {};
    currentFilteredResults.forEach(r => {
        // Group by event name AND timestamp for separate headers
        const groupKey = `${r.eventName}|${r.timestamp}`;
        if (!groups[groupKey]) groups[groupKey] = [];
        groups[groupKey].push(r);
    });

    // Sort groups by timestamp (newest first)
    const sortedKeys = Object.keys(groups).sort((a, b) => {
        const tsA = a.split('|')[1] ? new Date(a.split('|')[1]) : new Date(0);
        const tsB = b.split('|')[1] ? new Date(b.split('|')[1]) : new Date(0);
        return tsB - tsA;
    });

    sortedKeys.forEach(groupKey => {
        const [eventName, timestamp] = groupKey.split('|');
        const header = document.createElement('tr');
        header.className = 'event-header';
        header.innerHTML = `<td colspan="1"><strong>${timestamp} \u00A0 ${eventName}</strong></td><td colspan="6"></td>`;
        userTable.appendChild(header);

        groups[groupKey].forEach(result => {
            const row = document.createElement('tr');
            row.className = 'event-field-row';
            const statusClass = getStatusClass(result.validationStatus);
            row.innerHTML = `
                <td></td>
                <td></td>
                <td>${result.key || 'N/A'}</td>
                <td>${result.value !== null && result.value !== undefined ? result.value : 'null'}</td>
                <td>${result.expectedType || 'N/A'}</td>
                <td>${result.receivedType || 'N/A'}</td>
                <td class="${statusClass}">${result.validationStatus || 'Unknown'}</td>
            `;
            userTable.appendChild(row);
        });
    });
}

function clearFilters() {
    currentFilteredResults = null;
    // reload initial logs to rebuild table
    loadInitialLogs();
    // clear inputs
    ['filterEventSelect','filterEventSearch','filterFieldSelect','filterValueInput','filterExpectedSelect','filterReceivedSelect','filterStatusSelect'].forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        if (el.tagName === 'SELECT') {
            // reset to default (first option has value '')
            el.value = '';
        } else {
            el.value = '';
        }
    });
}

// Download valid events report
function downloadValidEvents() {
    if (allValidationResults.length === 0) {
        alert('No validation results to download');
        return;
    }
    
    fetch(`/app/${APP_ID}/download-valid-events`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            results: allValidationResults
        })
    })
    .then(response => response.blob())
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `valid_events_report_${APP_ID}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
    })
    .catch(error => {
        console.error('Error downloading valid events:', error);
        alert('Error downloading valid events');
    });
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
    updateCoverage();
    
    // Refresh stats every 5 seconds
    setInterval(updateStats, 5000);
    
    // Update coverage every 10 seconds
    setInterval(updateCoverage, 10000);
    
    // Add download button handlers
    const dlBtn = document.getElementById('downloadResults');
    if (dlBtn) dlBtn.addEventListener('click', downloadResults);
    const dlValidBtn = document.getElementById('downloadValidEvents');
    if (dlValidBtn) dlValidBtn.addEventListener('click', downloadValidEvents);
    // Delete all logs handler
    const delBtn = document.getElementById('deleteAllLogs');
    if (delBtn) delBtn.addEventListener('click', function() {
        if (!confirm('Delete ALL stored logs for this app? This cannot be undone.')) return;
        fetch(`/app/${APP_ID}/delete-logs`, { method: 'POST' })
            .then(resp => resp.json())
            .then(data => {
                if (data && data.success) {
                    alert('Deleted ' + data.deleted + ' logs');
                    // Clear UI
                    document.getElementById('userLogsTable').innerHTML = '';
                    document.getElementById('systemLogsTable').innerHTML = '';
                    allValidationResults = [];
                    currentFilteredResults = null;
                    userEventsCount = 0; systemEventsCount = 0;
                    if (document.getElementById('userEventsCount')) document.getElementById('userEventsCount').textContent = '0';
                    if (document.getElementById('systemEventsCount')) document.getElementById('systemEventsCount').textContent = '0';
                    updateStats();
                } else {
                    alert('Error deleting logs: ' + (data.error || 'unknown'));
                }
            }).catch(err => {
                console.error('Delete logs error', err);
                alert('Error deleting logs');
            });
    });

    // Filter controls (if present)
    const applyBtn = document.getElementById('applyFiltersBtn');
    if (applyBtn) applyBtn.addEventListener('click', applyFilters);
    const clearBtn = document.getElementById('clearFiltersBtn');
    if (clearBtn) clearBtn.addEventListener('click', clearFilters);
    
    // Pagination: Load More button
    const loadMoreBtn = document.getElementById('loadMoreBtn');
    if (loadMoreBtn) loadMoreBtn.addEventListener('click', loadMoreLogs);
});
