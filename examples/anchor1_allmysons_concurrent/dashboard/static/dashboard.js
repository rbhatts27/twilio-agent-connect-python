/**
 * Anchor 1 Demo Dashboard - Concurrent Cross-Channel Visualization
 *
 * This dashboard demonstrates Server-Sent Events (SSE) for real-time updates
 * with special handling for concurrent channel activity (voice + SMS).
 */

// =============================================================================
// State Management
// =============================================================================

let eventSource = null;
let conversations = new Map();
let totalEventCount = 0;

// Track active channels per conversation
let activeChannels = new Map(); // conversation_id -> Set of active channels

// DOM elements
const conversationsGrid = document.getElementById('conversationsGrid');
const activityLog = document.getElementById('activityLog');
const conversationCount = document.getElementById('conversationCount');
const connectionStatus = document.getElementById('connectionStatus');
const eventCount = document.getElementById('eventCount');
const voiceDot = document.getElementById('voiceDot');
const smsDot = document.getElementById('smsDot');

// =============================================================================
// Initialization
// =============================================================================

function init() {
    connectEventSource();
}

// =============================================================================
// Server-Sent Events (SSE) Connection
// =============================================================================

function connectEventSource() {
    if (eventSource) {
        eventSource.close();
    }

    eventSource = new EventSource('/events');

    eventSource.onopen = () => {
        updateConnectionStatus(true);
        console.log('SSE connection established');
    };

    eventSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleEvent(data);
        } catch (error) {
            console.error('Failed to parse event data:', error);
        }
    };

    eventSource.onerror = (error) => {
        console.error('SSE error:', error);
        updateConnectionStatus(false);
        setTimeout(() => {
            console.log('Attempting to reconnect...');
            connectEventSource();
        }, 5000);
    };
}

function updateConnectionStatus(connected) {
    if (connected) {
        connectionStatus.textContent = 'Connected';
        connectionStatus.className = 'badge rounded-pill bg-success';
    } else {
        connectionStatus.textContent = 'Disconnected';
        connectionStatus.className = 'badge rounded-pill bg-danger';
    }
}

// =============================================================================
// Event Processing
// =============================================================================

function handleEvent(event) {
    console.log('Received event:', event);
    totalEventCount++;
    eventCount.textContent = `${totalEventCount} events`;

    // Update channel indicators
    updateChannelIndicators(event);

    // Update conversation card if conversation_id is present
    if (event.conversation_id) {
        updateConversationCard(event);
    }

    // Add to activity timeline
    appendToActivityLog(event);
}

function updateChannelIndicators(event) {
    if (event.channel === 'voice') {
        voiceDot.classList.add('active');
        setTimeout(() => voiceDot.classList.remove('active'), 2000);
    } else if (event.channel === 'sms') {
        smsDot.classList.add('active');
        setTimeout(() => smsDot.classList.remove('active'), 2000);
    }
}

// =============================================================================
// Conversation Cards Management
// =============================================================================

function updateConversationCard(event) {
    const convId = event.conversation_id;

    // Get or create conversation data
    if (!conversations.has(convId)) {
        conversations.set(convId, {
            conversation_id: convId,
            channels: new Set(),
            profile_id: event.profile_id,
            events: [],
            isConcurrent: false
        });
        activeChannels.set(convId, new Set());
        createConversationCard(convId);
    }

    const conversation = conversations.get(convId);
    const channels = activeChannels.get(convId);

    // Track channels used
    if (event.channel) {
        conversation.channels.add(event.channel);
        channels.add(event.channel);
    }

    // Detect concurrent channel usage
    if (conversation.channels.size > 1) {
        conversation.isConcurrent = true;
    }

    // Update profile_id if we get it
    if (event.profile_id && !conversation.profile_id) {
        conversation.profile_id = event.profile_id;
    }

    conversation.events.push(event);

    // Update card content
    updateCardContent(convId);
}

function createConversationCard(convId) {
    const conversation = conversations.get(convId);

    // Remove empty state if present
    const emptyState = conversationsGrid.querySelector('.text-center');
    if (emptyState) {
        conversationsGrid.innerHTML = '';
    }

    const card = document.createElement('div');
    card.className = 'card conversation-card';
    card.id = `card-${convId}`;

    conversationsGrid.prepend(card);
    updateConversationCount();
}

function updateCardContent(convId) {
    const conversation = conversations.get(convId);
    const card = document.getElementById(`card-${convId}`);

    if (!card) return;

    // Update card styling for concurrent channels
    card.className = 'card conversation-card';
    if (conversation.isConcurrent) {
        card.classList.add('concurrent');
    } else if (conversation.channels.has('voice')) {
        card.classList.add('border-start-voice');
    } else if (conversation.channels.has('sms')) {
        card.classList.add('border-start-sms');
    }

    // Shorten conversation ID
    const shortId = convId.length > 15 ? '...' + convId.slice(-10) : convId;

    // Build channel badges
    let channelBadges = '';
    if (conversation.isConcurrent) {
        channelBadges = '<span class="badge concurrent-badge me-1">CONCURRENT</span>';
    }
    for (const ch of conversation.channels) {
        const bgClass = ch === 'voice' ? 'bg-success' : 'bg-primary';
        channelBadges += `<span class="badge ${bgClass} text-uppercase me-1">${ch}</span>`;
    }

    // Build profile information
    let profileInfo = '';
    if (conversation.profile_id) {
        const shortProfileId = conversation.profile_id.length > 10
            ? '...' + conversation.profile_id.slice(-8)
            : conversation.profile_id;
        profileInfo = `
            <div class="alert alert-dark py-2 mb-3" style="font-size: 0.8rem; background: #0f3460; border: none;">
                <span class="text-muted">Profile:</span>
                <span class="font-monospace" title="${conversation.profile_id}">${shortProfileId}</span>
            </div>
        `;
    }

    // Build event list with timeline styling
    const eventListHtml = conversation.events.slice(-10).map(event => {
        let messagePreview = '';
        if (event.message && ['user_message', 'ai_response', 'memory', 'concurrent_channel'].includes(event.event_type)) {
            const truncated = event.message.length > 60 ? event.message.slice(0, 60) + '...' : event.message;
            messagePreview = `<div class="text-muted small mt-1">${escapeHtml(truncated)}</div>`;
        }

        const icon = getEventIcon(event.event_type);
        const badgeClass = getEventBadgeClass(event.event_type);
        const channelClass = event.channel || 'system';

        return `
            <div class="timeline-event">
                <div class="timeline-dot ${channelClass}"></div>
                <div class="event-item ${event.event_type} py-2 px-3">
                    <div class="d-flex align-items-start gap-2">
                        <span style="font-size: 1.1rem;">${icon}</span>
                        <div class="flex-grow-1">
                            <span class="badge ${badgeClass}" style="font-size: 0.6rem;">
                                ${getEventLabel(event.event_type)}
                            </span>
                            ${event.channel ? `<span class="badge bg-dark ms-1" style="font-size: 0.55rem;">${event.channel.toUpperCase()}</span>` : ''}
                            ${messagePreview}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    card.innerHTML = `
        <div class="card-body">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <div>
                    <span class="text-muted small">Conversation: </span>
                    <span class="font-monospace small text-muted" title="${convId}">${shortId}</span>
                </div>
                <div>${channelBadges}</div>
            </div>
            ${profileInfo}
            <div class="timeline-container">
                <div class="timeline-line"></div>
                ${eventListHtml}
            </div>
        </div>
    `;

    // Auto-scroll to latest event
    const timeline = card.querySelector('.timeline-container');
    if (timeline) {
        timeline.scrollTop = timeline.scrollHeight;
    }
}

// =============================================================================
// Activity Log Management
// =============================================================================

function appendToActivityLog(event) {
    // Remove empty state if present
    const emptyState = activityLog.querySelector('.text-center');
    if (emptyState) {
        activityLog.innerHTML = '';
    }

    const timestamp = formatTimestamp(event.timestamp);
    const channel = event.channel || 'system';

    // Determine if this is a concurrent channel event
    const isConcurrent = event.event_type === 'concurrent_channel' || event.event_type === 'cross_channel';

    const logEntry = document.createElement('div');
    logEntry.className = `card log-entry mb-2 border-start border-start-${isConcurrent ? 'concurrent' : channel}`;

    const icon = getEventIcon(event.event_type);
    const bgClass = channel === 'sms' ? 'bg-primary' :
                    channel === 'voice' ? 'bg-success' :
                    isConcurrent ? 'bg-danger' : 'bg-secondary';

    logEntry.innerHTML = `
        <div class="card-body py-2 px-3">
            <div class="d-flex align-items-start gap-2">
                <span style="font-size: 1rem;">${icon}</span>
                <div class="flex-grow-1">
                    <div class="d-flex align-items-center gap-2 mb-1">
                        <span class="font-monospace small text-muted">${timestamp}</span>
                        <span class="badge ${bgClass} text-uppercase" style="font-size: 0.6rem;">
                            ${channel}
                        </span>
                        ${isConcurrent ? '<span class="badge concurrent-badge" style="font-size: 0.55rem;">CONCURRENT</span>' : ''}
                    </div>
                    <small class="text-light">${escapeHtml(event.message)}</small>
                </div>
            </div>
        </div>
    `;

    activityLog.appendChild(logEntry);
    activityLog.scrollTop = activityLog.scrollHeight;
}

// =============================================================================
// Utility Functions
// =============================================================================

function formatTimestamp(timestamp) {
    try {
        const date = new Date(timestamp);
        return date.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
    } catch (error) {
        return timestamp;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getEventLabel(eventType) {
    const labels = {
        'user_message': 'User',
        'memory': 'Memory',
        'ai_processing': 'Processing',
        'ai_response': 'AI Response',
        'handoff': 'Handoff',
        'error': 'Error',
        'conversation_started': 'Started',
        'call_started': 'Call Started',
        'websocket_connected': 'Connected',
        'call_setup': 'Setup',
        'concurrent_channel': 'Concurrent',
        'cross_channel': 'Cross-Channel',
        'voice_active': 'Voice Active',
        'voice_ended': 'Voice Ended',
        'photo_analysis': 'Photo',
        'quote_generated': 'Quote'
    };
    return labels[eventType] || eventType;
}

function getEventIcon(eventType) {
    const icons = {
        'user_message': '👤',
        'memory': '🧠',
        'ai_processing': '⚙️',
        'ai_response': '🤖',
        'handoff': '👥',
        'error': '❌',
        'conversation_started': '💬',
        'call_started': '📞',
        'websocket_connected': '🔌',
        'call_setup': '📞',
        'concurrent_channel': '🔀',
        'cross_channel': '🔗',
        'voice_active': '🎙️',
        'voice_ended': '📵',
        'photo_analysis': '📸',
        'quote_generated': '💰'
    };
    return icons[eventType] || '📌';
}

function getEventBadgeClass(eventType) {
    const classes = {
        'user_message': 'bg-info',
        'memory': 'bg-warning text-dark',
        'ai_processing': 'bg-secondary',
        'ai_response': 'bg-success',
        'handoff': 'bg-danger',
        'error': 'bg-danger',
        'conversation_started': 'bg-primary',
        'call_started': 'bg-success',
        'websocket_connected': 'bg-primary',
        'call_setup': 'bg-info',
        'concurrent_channel': 'bg-danger',
        'cross_channel': 'bg-danger',
        'voice_active': 'bg-success',
        'voice_ended': 'bg-secondary',
        'photo_analysis': 'bg-purple',
        'quote_generated': 'bg-warning text-dark'
    };
    return classes[eventType] || 'bg-secondary';
}

function updateConversationCount() {
    conversationCount.textContent = conversations.size;
}

// =============================================================================
// Initialize on page load
// =============================================================================

init();
