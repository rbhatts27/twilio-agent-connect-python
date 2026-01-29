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

// Currently selected conversation/profile for data panels
let selectedConversationId = null;
let selectedProfileId = null;

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

    // Handle demo status events
    if (event.event_type === 'demo_status') {
        updateDemoProgress(event);
        appendToActivityLog(event);
        return;
    }

    // Handle voice transcript events (just add to activity log)
    if (event.event_type === 'voice_transcript') {
        appendToActivityLog(event);
        return;
    }

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

    // Auto-select first conversation with profile (but don't keep refreshing)
    if (!selectedConversationId && conversation.profile_id) {
        // Auto-select first conversation that has a profile
        selectConversation(convId, conversation.profile_id);
        const card = document.getElementById(`card-${convId}`);
        if (card) card.style.outline = '2px solid #e94560';
    }
    // Note: Data panels only refresh on manual click or Refresh button, not on every event
}

function createConversationCard(convId) {
    // Remove empty state if present
    const emptyState = document.getElementById('noConversationsMsg');
    if (emptyState) {
        emptyState.style.display = 'none';
    }

    const card = document.createElement('div');
    card.className = 'conversation-item';
    card.id = `card-${convId}`;
    card.style.cssText = 'background: #1a1a2e; border-radius: 6px; padding: 0.75rem; margin-bottom: 0.5rem; cursor: pointer; border-left: 3px solid #0f3460;';

    // Add click handler to select conversation and load communications
    card.addEventListener('click', () => {
        const conversation = conversations.get(convId);
        selectConversation(convId, conversation?.profile_id);

        // Highlight selected card
        document.querySelectorAll('.conversation-item').forEach(c => {
            c.style.borderLeftColor = '#0f3460';
        });
        card.style.borderLeftColor = '#e94560';
    });

    conversationsGrid.appendChild(card);
    updateConversationCount();
}

function clearConversations() {
    conversations.clear();
    conversationsGrid.innerHTML = `
        <div class="text-center py-4 text-muted" id="noConversationsMsg">
            <div style="font-size: 2rem; opacity: 0.3;">💬</div>
            <p class="mb-1 small">No conversations yet</p>
            <small>Run demo to create conversations</small>
        </div>
    `;
    updateConversationCount();
    // Clear data panels
    document.getElementById('profileContent').innerHTML = '<div class="empty-state">No profile selected</div>';
    document.getElementById('observationsContent').innerHTML = '<div class="empty-state">No observations loaded</div>';
    document.getElementById('conversationContent').innerHTML = '<div class="empty-state">Click a conversation to view communications</div>';
    selectedConversationId = null;
    selectedProfileId = null;
}
window.clearConversations = clearConversations;

function updateCardContent(convId) {
    const conversation = conversations.get(convId);
    const card = document.getElementById(`card-${convId}`);

    if (!card) return;

    // Update card styling based on channel
    if (conversation.channels.has('voice')) {
        card.style.borderLeftColor = '#198754';
    } else if (conversation.channels.has('sms')) {
        card.style.borderLeftColor = '#0d6efd';
    }

    // Shorten conversation ID for display
    const shortId = convId.length > 20 ? convId.slice(0, 8) + '...' + convId.slice(-8) : convId;

    // Build channel badges
    let channelBadges = '';
    for (const ch of conversation.channels) {
        const bgClass = ch === 'voice' ? 'bg-success' : 'bg-primary';
        channelBadges += `<span class="badge ${bgClass} text-uppercase" style="font-size: 0.65rem;">${ch}</span> `;
    }

    // Event count
    const eventCount = conversation.events.length;

    card.innerHTML = `
        <div class="d-flex justify-content-between align-items-center">
            <div>
                <div class="font-monospace small" style="color: #8892b0;" title="${convId}">${shortId}</div>
                <small class="text-muted">${eventCount} events</small>
            </div>
            <div>${channelBadges}</div>
        </div>
    `;
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
                             onclick="event.stopPropagation(); openImageModal('${escapeHtml(media.url)}')"
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
                             onclick="openImageModal('${escapeHtml(media.url)}')"
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
        'anchor_switched': 'Anchor',
        'demo_status': 'Demo',
        'voice_transcript': 'Transcript'
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
        'anchor_switched': '🎯',
        'demo_status': '🎬',
        'voice_transcript': '🗣️'
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
        'anchor_switched': 'bg-warning text-dark',
        'demo_status': 'bg-danger',
        'voice_transcript': 'bg-success'
    };
    return classes[eventType] || 'bg-secondary';
}

function updateConversationCount() {
    conversationCount.textContent = conversations.size;
}

// =============================================================================
// Profile & Conversation Data Panels
// =============================================================================

/**
 * Select a conversation to view its profile and conversation data.
 */
function selectConversation(convId, profileId) {
    selectedConversationId = convId;
    selectedProfileId = profileId;

    // Load data for the selected conversation
    if (profileId) {
        loadProfileData(profileId);
        loadMemoryData(profileId);
    } else {
        document.getElementById('profileContent').innerHTML =
            '<div class="empty-state">No profile ID associated with this conversation</div>';
        document.getElementById('observationsContent').innerHTML =
            '<div class="empty-state">No profile for memory lookup</div>';
    }

    if (convId) {
        loadConversationData(convId);
    }
}

/**
 * Load profile data (traits) from Memora API.
 */
async function loadProfileData(profileId) {
    const container = document.getElementById('profileContent');
    container.innerHTML = '<div class="empty-state">Loading profile...</div>';

    try {
        const response = await fetch(`/api/profile/${encodeURIComponent(profileId)}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        if (data.error) {
            container.innerHTML = `<div class="empty-state">Error: ${escapeHtml(data.error)}</div>`;
            return;
        }

        let html = `<div class="trait-item"><span class="trait-name">Profile ID</span><br><span class="trait-value font-monospace" style="font-size: 0.7rem;">${escapeHtml(data.id || profileId)}</span></div>`;

        // Display traits
        if (data.traits && Object.keys(data.traits).length > 0) {
            for (const [group, traits] of Object.entries(data.traits)) {
                html += `<div style="color: #e94560; font-size: 0.7rem; margin-top: 0.5rem; text-transform: uppercase;">${escapeHtml(group)}</div>`;
                if (typeof traits === 'object' && traits !== null) {
                    for (const [key, value] of Object.entries(traits)) {
                        const displayValue = typeof value === 'object' ? JSON.stringify(value) : String(value);
                        html += `<div class="trait-item"><span class="trait-name">${escapeHtml(key)}</span><br><span class="trait-value">${escapeHtml(displayValue)}</span></div>`;
                    }
                }
            }
        } else {
            html += '<div class="empty-state">No traits found</div>';
        }

        container.innerHTML = html;

    } catch (error) {
        console.error('Error loading profile:', error);
        container.innerHTML = `<div class="empty-state">Failed to load profile: ${escapeHtml(error.message)}</div>`;
    }
}

/**
 * Load memory data (observations, summaries) from Memora API.
 */
async function loadMemoryData(profileId) {
    const container = document.getElementById('observationsContent');
    container.innerHTML = '<div class="empty-state">Loading memory...</div>';

    try {
        const response = await fetch(`/api/profile/${encodeURIComponent(profileId)}/memory`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        if (data.error) {
            container.innerHTML = `<div class="empty-state">Error: ${escapeHtml(data.error)}</div>`;
            return;
        }

        let html = '';

        // Display observations
        if (data.observations && data.observations.length > 0) {
            html += '<div style="color: #e94560; font-size: 0.7rem; margin-bottom: 0.5rem;">OBSERVATIONS</div>';
            for (const obs of data.observations.slice(0, 10)) {
                html += `
                    <div class="observation-item">
                        <div class="observation-content">"${escapeHtml(obs.content)}"</div>
                        <div class="observation-meta">${obs.source || 'unknown'} • ${formatDate(obs.created_at)}</div>
                    </div>
                `;
            }
        }

        // Display summaries
        if (data.summaries && data.summaries.length > 0) {
            html += '<div style="color: #e94560; font-size: 0.7rem; margin-top: 0.75rem; margin-bottom: 0.5rem;">SUMMARIES</div>';
            for (const summary of data.summaries.slice(0, 5)) {
                html += `
                    <div class="observation-item">
                        <div class="observation-content">"${escapeHtml(summary.content)}"</div>
                        <div class="observation-meta">${formatDate(summary.created_at)}</div>
                    </div>
                `;
            }
        }

        // Display session count
        if (data.sessions && data.sessions.length > 0) {
            html += `<div style="color: #8892b0; font-size: 0.7rem; margin-top: 0.75rem;">${data.sessions.length} past session(s)</div>`;
        }

        if (!html) {
            html = '<div class="empty-state">No memory data found for this profile</div>';
        }

        container.innerHTML = html;

    } catch (error) {
        console.error('Error loading memory:', error);
        container.innerHTML = `<div class="empty-state">Failed to load memory: ${escapeHtml(error.message)}</div>`;
    }
}

/**
 * Load conversation data (participants, communications) from Maestro API.
 */
async function loadConversationData(convId) {
    const container = document.getElementById('conversationContent');
    container.innerHTML = '<div class="empty-state">Loading conversation...</div>';

    try {
        const response = await fetch(`/api/conversation/${encodeURIComponent(convId)}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        if (data.error) {
            container.innerHTML = `<div class="empty-state">Error: ${escapeHtml(data.error)}</div>`;
            return;
        }

        let html = '';

        // Display participants
        if (data.participants && data.participants.length > 0) {
            html += '<div style="color: #e94560; font-size: 0.7rem; margin-bottom: 0.5rem;">PARTICIPANTS</div>';
            for (const p of data.participants) {
                const addresses = (p.addresses || []).map(a => `${a.channel}: ${a.address}`).join(', ');
                html += `
                    <div class="trait-item">
                        <span class="trait-name">${escapeHtml(p.type || 'unknown')}</span>
                        <br><span class="trait-value" style="font-size: 0.75rem;">${escapeHtml(addresses || p.id)}</span>
                    </div>
                `;
            }
        }

        // Display communications
        if (data.communications && data.communications.length > 0) {
            html += '<div style="color: #e94560; font-size: 0.7rem; margin-top: 0.75rem; margin-bottom: 0.5rem;">COMMUNICATIONS</div>';
            for (const comm of data.communications.slice(-15)) {
                const authorType = comm.author_type || 'unknown';
                const channelBadge = comm.channel ? `<span class="badge bg-${comm.channel === 'voice' ? 'success' : 'primary'}" style="font-size: 0.6rem;">${comm.channel}</span>` : '';
                html += `
                    <div class="comm-item">
                        <div class="comm-author">${escapeHtml(authorType)} ${channelBadge}</div>
                        <div class="comm-content">${escapeHtml(comm.content || '(no content)')}</div>
                        <div class="comm-channel">${formatDate(comm.created_at)}</div>
                    </div>
                `;
            }
        } else {
            html += '<div class="empty-state">No communications yet</div>';
        }

        container.innerHTML = html;

    } catch (error) {
        console.error('Error loading conversation:', error);
        container.innerHTML = `<div class="empty-state">Failed to load conversation: ${escapeHtml(error.message)}</div>`;
    }
}

/**
 * Refresh profile data for the selected profile.
 */
function refreshProfileData() {
    if (selectedProfileId) {
        loadProfileData(selectedProfileId);
    }
}
window.refreshProfileData = refreshProfileData;

/**
 * Refresh memory data for the selected profile.
 */
function refreshMemoryData() {
    if (selectedProfileId) {
        loadMemoryData(selectedProfileId);
    }
}
window.refreshMemoryData = refreshMemoryData;

/**
 * Refresh conversation data for the selected conversation.
 */
function refreshConversationData() {
    if (selectedConversationId) {
        loadConversationData(selectedConversationId);
    }
}
window.refreshConversationData = refreshConversationData;

/**
 * Format a date string for display.
 */
function formatDate(dateStr) {
    if (!dateStr) return '';
    try {
        const date = new Date(dateStr);
        return date.toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (e) {
        return dateStr;
    }
}

// =============================================================================
// Image Modal for SMS Attachments
// =============================================================================

/**
 * Open the image modal to view a full-size SMS attachment.
 */
function openImageModal(imageUrl) {
    const modal = document.getElementById('imageModal');
    const modalImage = document.getElementById('modalImage');
    modalImage.src = imageUrl;
    modal.classList.add('active');
}
window.openImageModal = openImageModal;

/**
 * Close the image modal.
 */
function closeImageModal() {
    const modal = document.getElementById('imageModal');
    modal.classList.remove('active');
}
window.closeImageModal = closeImageModal;

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeImageModal();
    }
});

// =============================================================================
// One-Click Demo
// =============================================================================

let demoActive = false;
let demoStartTime = null;
let transcriptTimer = null;

/**
 * Run the one-click demo: Maria calls and then sends SMS.
 */
async function runDemo() {
    const btn = document.getElementById('runDemoBtn');
    const stopBtn = document.getElementById('stopDemoBtn');
    const progress = document.getElementById('demoProgress');
    const progressBar = document.getElementById('demoProgressBar');
    const statusText = document.getElementById('demoStatusText');

    if (demoActive) {
        return;
    }

    demoActive = true;
    demoStartTime = Date.now();
    btn.disabled = true;
    btn.textContent = '⏳ Running...';
    stopBtn.style.display = 'inline-block';
    progress.style.display = 'block';
    progressBar.style.width = '0%';
    progressBar.classList.remove('bg-danger');
    statusText.textContent = 'Starting demo...';

    try {
        const response = await fetch('/api/maria/demo', { method: 'POST' });
        const data = await response.json();

        if (!data.success) {
            statusText.textContent = `Error: ${data.error}`;
            progressBar.classList.add('bg-danger');
            endDemo();
            btn.textContent = '▶️ Start Demo';
        }
    } catch (error) {
        statusText.textContent = `Error: ${error.message}`;
        progressBar.classList.add('bg-danger');
        endDemo();
        btn.textContent = '▶️ Start Demo';
    }
}
window.runDemo = runDemo;

/**
 * Update demo progress from SSE event.
 */
function updateDemoProgress(event) {
    const progress = document.getElementById('demoProgress');
    const progressBar = document.getElementById('demoProgressBar');
    const statusText = document.getElementById('demoStatusText');
    const btn = document.getElementById('runDemoBtn');

    if (!event.metadata) return;

    const { status, progress: pct } = event.metadata;

    progress.style.display = 'block';
    progressBar.style.width = `${pct}%`;
    statusText.textContent = event.message;

    if (status === 'completed' || status === 'error') {
        endDemo();
        if (status === 'completed') {
            progressBar.classList.remove('bg-danger');
            btn.textContent = '✅ Complete';
            setTimeout(() => {
                btn.textContent = '▶️ Start Demo';
            }, 3000);
        } else {
            progressBar.classList.add('bg-danger');
            btn.textContent = '❌ Failed';
            setTimeout(() => {
                btn.textContent = '▶️ Start Demo';
            }, 3000);
        }
    }
}

/**
 * End the demo and reset state.
 */
function endDemo() {
    demoActive = false;
    const btn = document.getElementById('runDemoBtn');
    const stopBtn = document.getElementById('stopDemoBtn');

    btn.disabled = false;
    stopBtn.style.display = 'none';
}

/**
 * Stop the demo by calling the server to end connections.
 */
async function stopDemo() {
    const btn = document.getElementById('runDemoBtn');
    const stopBtn = document.getElementById('stopDemoBtn');
    const progress = document.getElementById('demoProgress');
    const progressBar = document.getElementById('demoProgressBar');
    const statusText = document.getElementById('demoStatusText');

    try {
        stopBtn.textContent = '⏳ Stopping...';
        stopBtn.disabled = true;

        const response = await fetch('/api/maria/stop', { method: 'POST' });
        const data = await response.json();

        if (data.success) {
            statusText.textContent = '⏹️ Demo stopped';
            progressBar.style.width = '100%';
        }
    } catch (error) {
        console.error('Error stopping demo:', error);
    }

    // Reset UI
    endDemo();
    btn.textContent = '▶️ Start Demo';
    stopBtn.textContent = '⏹️ Stop';
    stopBtn.disabled = false;

    // Hide progress after a moment
    setTimeout(() => {
        progress.style.display = 'none';
    }, 2000);
}
window.stopDemo = stopDemo;

// =============================================================================
// Maria Agent Controls (Manual)
// =============================================================================

/**
 * Trigger Maria to call the support line.
 */
async function mariaCall() {
    const btn = document.getElementById('mariaCallBtn');
    const status = document.getElementById('mariaStatus');

    btn.disabled = true;
    btn.innerHTML = '📞 Calling...';
    status.style.display = 'block';
    status.textContent = 'Initiating call...';

    try {
        const response = await fetch('/api/maria/call', { method: 'POST' });
        const data = await response.json();

        if (data.success) {
            status.innerHTML = `<span class="text-success">✓ Call initiated!</span> SID: ${data.call_sid.slice(0, 15)}...`;
            btn.innerHTML = '📞 Call Active';
            setTimeout(() => {
                btn.innerHTML = '📞 Call';
                btn.disabled = false;
            }, 30000);
        } else {
            status.innerHTML = `<span class="text-danger">✗ ${data.error}</span>`;
            btn.innerHTML = '📞 Call';
            btn.disabled = false;
        }
    } catch (error) {
        status.innerHTML = `<span class="text-danger">✗ ${error.message}</span>`;
        btn.innerHTML = '📞 Call';
        btn.disabled = false;
    }
}
window.mariaCall = mariaCall;

/**
 * Trigger Maria to send an SMS with a photo.
 */
async function mariaSms(photoType = 'living room') {
    const btn = document.getElementById('mariaSmsBtn');
    const status = document.getElementById('mariaStatus');

    btn.disabled = true;
    btn.innerHTML = '📱 Sending...';
    status.style.display = 'block';
    status.textContent = `Sending ${photoType} photo...`;

    try {
        const response = await fetch('/api/maria/sms', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ photo_type: photoType })
        });
        const data = await response.json();

        if (data.success) {
            status.innerHTML = `<span class="text-success">✓ SMS sent!</span> ${photoType} photo • SID: ${data.message_sid.slice(0, 15)}...`;
        } else {
            status.innerHTML = `<span class="text-danger">✗ ${data.error}</span>`;
        }
    } catch (error) {
        status.innerHTML = `<span class="text-danger">✗ ${error.message}</span>`;
    }

    btn.innerHTML = '📱 SMS + Photo';
    btn.disabled = false;
}
window.mariaSms = mariaSms;

// =============================================================================
// Initialize on page load
// =============================================================================

init();
