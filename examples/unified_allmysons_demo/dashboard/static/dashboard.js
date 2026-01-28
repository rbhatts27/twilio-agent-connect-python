/**
 * Unified All My Sons Demo Dashboard
 *
 * Features:
 * - Anchor scenario selection dropdown
 * - Real-time SSE event streaming
 * - Enhanced SMS activity log showing message text and image thumbnails
 * - Concurrent channel visualization
 */

// =============================================================================
// State Management
// =============================================================================

let eventSource = null;
let conversations = new Map();
let totalEventCount = 0;
let currentAnchor = null;

// Track active channels per conversation
let activeChannels = new Map();

// DOM elements
const conversationsGrid = document.getElementById('conversationsGrid');
const activityLog = document.getElementById('activityLog');
const conversationCount = document.getElementById('conversationCount');
const connectionStatus = document.getElementById('connectionStatus');
const eventCount = document.getElementById('eventCount');
const voiceDot = document.getElementById('voiceDot');
const smsDot = document.getElementById('smsDot');
const anchorSelector = document.getElementById('anchorSelector');
const scenarioTitle = document.getElementById('scenarioTitle');
const scenarioSteps = document.getElementById('scenarioSteps');
const anchorBadge = document.getElementById('anchorBadge');

// =============================================================================
// Initialization
// =============================================================================

function init() {
    loadActiveAnchor();
    connectEventSource();
}

// =============================================================================
// Anchor Management
// =============================================================================

async function loadActiveAnchor() {
    try {
        const response = await fetch('/api/active-anchor');
        const data = await response.json();
        currentAnchor = data;
        updateScenarioDisplay(data);
        anchorSelector.value = data.anchor_id;
    } catch (error) {
        console.error('Failed to load active anchor:', error);
    }
}

async function switchAnchor(anchorId) {
    try {
        const response = await fetch('/api/select-anchor', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ anchor_id: anchorId })
        });

        if (response.ok) {
            const data = await response.json();
            currentAnchor = data;
            updateScenarioDisplay(data);
        } else {
            const error = await response.json();
            console.error('Failed to switch anchor:', error);
            // Revert selector
            if (currentAnchor) {
                anchorSelector.value = currentAnchor.anchor_id;
            }
        }
    } catch (error) {
        console.error('Error switching anchor:', error);
    }
}

function updateScenarioDisplay(anchor) {
    scenarioTitle.textContent = anchor.scenario_title;
    anchorBadge.textContent = anchor.name;

    // Check if this is a stub (anchors 2-6)
    const isStub = anchor.anchor_id !== 'anchor1';
    if (isStub) {
        anchorBadge.className = 'badge stub-badge';
    } else {
        anchorBadge.className = 'badge anchor-badge';
    }

    // Build scenario steps
    let stepsHtml = '';
    if (anchor.scenario_steps) {
        for (const step of anchor.scenario_steps) {
            stepsHtml += `
                <div class="scenario-step">
                    <span class="step-number">${step.number}</span>
                    <small>${escapeHtml(step.text)}</small>
                </div>
            `;
        }
    }
    scenarioSteps.innerHTML = stepsHtml;
}

// Expose switchAnchor globally for the HTML onchange handler
window.switchAnchor = switchAnchor;

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

    // Handle anchor selection events
    if (event.event_type === 'anchor_selected' || event.event_type === 'anchor_switched') {
        appendToActivityLog(event);
        return;
    }

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

        // Enhanced SMS content display
        if (event.event_type === 'sms_received' || event.event_type === 'sms_with_media') {
            messagePreview = buildSmsContentPreview(event);
        } else if (event.message && ['user_message', 'ai_response', 'memory', 'concurrent_channel'].includes(event.event_type)) {
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
// Enhanced SMS Content Display
// =============================================================================

/**
 * Build an enhanced SMS content preview with message text and image thumbnails.
 */
function buildSmsContentPreview(event) {
    let html = '<div class="sms-content-block">';

    // From number
    if (event.from_number) {
        html += `<div class="sms-from-number">From: ${escapeHtml(event.from_number)}</div>`;
    }

    // Message body
    if (event.sms_body) {
        html += `<div class="sms-body-text">"${escapeHtml(event.sms_body)}"</div>`;
    }

    // Media attachments
    if (event.media_attachments && event.media_attachments.length > 0) {
        html += '<div class="media-gallery">';
        for (const media of event.media_attachments) {
            const isImage = media.content_type && media.content_type.startsWith('image/');
            const filename = media.filename || `attachment_${media.index + 1}`;

            if (isImage && media.url) {
                html += `
                    <div class="media-thumbnail">
                        <img src="${escapeHtml(media.url)}" alt="${escapeHtml(filename)}"
                             onerror="this.style.display='none'; this.nextElementSibling.style.display='inline';">
                        <span class="media-icon" style="display:none;">📷</span>
                        <span class="media-name">${escapeHtml(filename)}</span>
                    </div>
                `;
            } else {
                html += `
                    <div class="media-thumbnail">
                        <span class="media-icon">📎</span>
                        <span class="media-name">${escapeHtml(filename)}</span>
                    </div>
                `;
            }
        }
        html += '</div>';
    }

    html += '</div>';
    return html;
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

    // Determine if this is an anchor selection event
    const isAnchorEvent = event.event_type === 'anchor_selected' || event.event_type === 'anchor_switched';

    const logEntry = document.createElement('div');
    logEntry.className = `card log-entry mb-2 border-start border-start-${isConcurrent ? 'concurrent' : channel}`;

    const icon = getEventIcon(event.event_type);
    const bgClass = channel === 'sms' ? 'bg-primary' :
                    channel === 'voice' ? 'bg-success' :
                    isConcurrent ? 'bg-danger' :
                    isAnchorEvent ? 'bg-warning text-dark' : 'bg-secondary';

    // Build the main content
    let mainContent = `<small class="text-light">${escapeHtml(event.message)}</small>`;

    // Enhanced SMS content in activity log
    if (event.event_type === 'sms_received' || event.event_type === 'sms_with_media') {
        mainContent = buildActivityLogSmsContent(event);
    }

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
                    ${mainContent}
                </div>
            </div>
        </div>
    `;

    activityLog.appendChild(logEntry);
    activityLog.scrollTop = activityLog.scrollHeight;
}

/**
 * Build enhanced SMS content for the activity log timeline.
 * Shows message text and image thumbnails.
 */
function buildActivityLogSmsContent(event) {
    let html = '';

    // SMS label with from number
    const fromLabel = event.from_number ? ` from ${escapeHtml(event.from_number)}` : '';
    html += `<small class="text-light d-block mb-1">SMS${fromLabel}</small>`;

    // Message body
    if (event.sms_body) {
        html += `<div class="sms-body-text" style="margin: 0.25rem 0;">Message: "${escapeHtml(event.sms_body)}"</div>`;
    }

    // Media attachments with thumbnails
    if (event.media_attachments && event.media_attachments.length > 0) {
        html += '<div class="media-gallery" style="margin-top: 0.25rem;">';
        for (const media of event.media_attachments) {
            const isImage = media.content_type && media.content_type.startsWith('image/');
            const filename = media.filename || `attachment_${media.index + 1}`;

            if (isImage && media.url) {
                html += `
                    <div class="media-thumbnail">
                        <img src="${escapeHtml(media.url)}" alt="${escapeHtml(filename)}"
                             onerror="this.style.display='none'; this.nextElementSibling.style.display='inline';">
                        <span class="media-icon" style="display:none;">📷</span>
                        <span class="media-name">${escapeHtml(filename)}</span>
                    </div>
                `;
            } else {
                html += `
                    <div class="media-thumbnail">
                        <span class="media-icon">📷</span>
                        <span class="media-name">${escapeHtml(filename)}</span>
                    </div>
                `;
            }
        }
        html += '</div>';
    }

    return html;
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
        'quote_generated': 'Quote',
        'sms_received': 'SMS Received',
        'sms_with_media': 'SMS + Media',
        'anchor_selected': 'Anchor',
        'anchor_switched': 'Anchor'
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
        'quote_generated': '💰',
        'sms_received': '📱',
        'sms_with_media': '📷',
        'anchor_selected': '🎯',
        'anchor_switched': '🎯'
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
        'quote_generated': 'bg-warning text-dark',
        'sms_received': 'bg-primary',
        'sms_with_media': 'bg-info',
        'anchor_selected': 'bg-warning text-dark',
        'anchor_switched': 'bg-warning text-dark'
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
