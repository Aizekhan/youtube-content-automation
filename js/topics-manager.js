/**
 * Topics Queue Manager
 * Sprint 1 - Task 1.7
 * FINAL TEST: 2026-02-22 21:15
 */

// Lambda Function URLs
const LAMBDA_URLS = {
    LIST: 'https://o7oswstatxulqezia6fvli4iny0uizlg.lambda-url.eu-central-1.on.aws/',
    ADD: 'https://vmipd7m6v63qqn5nud6xg3huum0poewo.lambda-url.eu-central-1.on.aws/',
    GET_NEXT: 'https://rk7q7vapiwyrb5ydvzfqvnxyta0bytjr.lambda-url.eu-central-1.on.aws/',
    UPDATE_STATUS: 'https://zwjkxakffcgnqyfm74xq5uxwvy0cckpe.lambda-url.eu-central-1.on.aws/',
    BULK_ADD: 'https://24khhggitezt5uwhx7z53hdyzm0yizht.lambda-url.eu-central-1.on.aws/'
};

// Global state
let currentUserId = null;
let currentChannelId = null;
let allTopics = [];
let editingTopicId = null;

/**
 * Initialize on page load
 */
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Topics Manager initialized');

    // Check authentication using AuthManager
    const authManager = new AuthManager();
    const isAuthenticated = await authManager.initialize();

    if (!isAuthenticated) {
        showToast('Please log in first', 'error');
        setTimeout(() => window.location.href = 'login.html', 2000);
        return;
    }

    // Get user_id from AuthManager
    currentUserId = authManager.getUserId();
    if (!currentUserId) {
        showToast('Failed to get user ID', 'error');
        setTimeout(() => window.location.href = 'login.html', 2000);
        return;
    }

    // Load channels for dropdown
    await loadChannels();

    // Add topic count updater for bulk textarea
    const bulkTextarea = document.getElementById('bulkTopicsList');
    if (bulkTextarea) {
        bulkTextarea.addEventListener('input', updateBulkTopicCount);
    }
});

/**
 * Load channels list for dropdown
 */
async function loadChannels() {
    try {
        // Get channels from ChannelConfigs (using Function URL)
        const response = await fetch('https://ywsop7xk36ir7r3a66fqcphdy40esadg.lambda-url.eu-central-1.on.aws/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: currentUserId })
        });

        const data = await response.json();

        // Lambda returns array directly, not {success, channels}
        const channels = Array.isArray(data) ? data : (data.channels || []);

        if (channels && channels.length > 0) {
            const channelSelect = document.getElementById('channelSelect');
            channelSelect.innerHTML = '<option value="">Select Channel...</option>';

            channels.forEach(channel => {
                const option = document.createElement('option');
                option.value = channel.channel_id;
                option.textContent = channel.channel_name || channel.channel_id;
                channelSelect.appendChild(option);
            });

            // Auto-select first channel if only one
            if (channels.length === 1) {
                channelSelect.value = channels[0].channel_id;
                currentChannelId = channels[0].channel_id;
                await loadTopics();
            }
        } else {
            console.warn('No channels found for user:', currentUserId);
            showToast('No channels found', 'error');
        }
    } catch (error) {
        console.error('Error loading channels:', error);
        showToast('Failed to load channels', 'error');
    }
}

/**
 * Load topics from Lambda
 */
async function loadTopics() {
    const channelSelect = document.getElementById('channelSelect');
    const selectedChannel = channelSelect.value;

    if (!selectedChannel) {
        document.getElementById('emptyState').style.display = 'block';
        document.getElementById('topicsTable').style.display = 'none';
        return;
    }

    currentChannelId = selectedChannel;

    const statusFilter = document.getElementById('statusFilter').value;
    const sortBy = document.getElementById('sortBy').value;

    // Show loading
    document.getElementById('loadingState').style.display = 'block';
    document.getElementById('emptyState').style.display = 'none';
    document.getElementById('topicsTable').style.display = 'none';

    try {
        const payload = {
            user_id: currentUserId,
            channel_id: currentChannelId,
            status: statusFilter === 'all' ? null : statusFilter,
            limit: 100
        };

        const response = await fetch(LAMBDA_URLS.LIST, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (data.success && data.topics) {
            allTopics = data.topics;

            // Apply sorting
            if (sortBy === 'priority') {
                allTopics.sort((a, b) => b.priority - a.priority);
            } else if (sortBy === 'created') {
                allTopics.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
            } else if (sortBy === 'updated') {
                allTopics.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
            }

            renderTopics();
        } else {
            document.getElementById('loadingState').style.display = 'none';
            document.getElementById('emptyState').style.display = 'block';
        }
    } catch (error) {
        console.error('Error loading topics:', error);
        showToast('Failed to load topics', 'error');
        document.getElementById('loadingState').style.display = 'none';
        document.getElementById('emptyState').style.display = 'block';
    }
}

/**
 * Render topics table
 */
function renderTopics() {
    const tbody = document.getElementById('topicsTableBody');
    tbody.innerHTML = '';

    document.getElementById('loadingState').style.display = 'none';

    if (allTopics.length === 0) {
        document.getElementById('emptyState').style.display = 'block';
        document.getElementById('topicsTable').style.display = 'none';
        return;
    }

    document.getElementById('emptyState').style.display = 'none';
    document.getElementById('topicsTable').style.display = 'table';

    allTopics.forEach(topic => {
        const row = document.createElement('tr');

        // Topic Text
        const topicTextCell = document.createElement('td');
        topicTextCell.className = 'topic-text-cell';

        // Add series badge if topic is part of a series
        if (topic.series_id && topic.episode_number) {
            const seriesBadge = `<span class="badge bg-info me-2" style="font-size: 11px;">🎬 EP${topic.episode_number}</span>`;
            topicTextCell.innerHTML = seriesBadge + topic.topic_text;
        } else {
            topicTextCell.textContent = topic.topic_text;
        }

        topicTextCell.title = topic.topic_text;
        row.appendChild(topicTextCell);

        // Status
        const statusCell = document.createElement('td');
        statusCell.innerHTML = `<span class="status-badge status-${topic.status}">${topic.status.replace('_', ' ')}</span>`;
        row.appendChild(statusCell);

        // Priority
        const priorityCell = document.createElement('td');
        const priorityClass = topic.priority >= 200 ? 'priority-high' : (topic.priority >= 100 ? 'priority-medium' : 'priority-low');
        priorityCell.innerHTML = `<span class="priority-badge ${priorityClass}">${topic.priority}</span>`;
        row.appendChild(priorityCell);

        // Source
        const sourceCell = document.createElement('td');
        sourceCell.textContent = topic.source || 'manual';
        row.appendChild(sourceCell);

        // Created At
        const createdCell = document.createElement('td');
        createdCell.textContent = formatDate(topic.created_at);
        row.appendChild(createdCell);

        // Actions
        const actionsCell = document.createElement('td');

        // Add Series Dashboard button if topic is part of a series
        const seriesDashboardBtn = topic.series_id ?
            `<button class="btn-icon btn-primary" onclick="openSeriesDashboard('${topic.series_id}', '${topic.channel_id || currentChannelId}')" title="Series Dashboard" style="background: #8b5cf6; color: white;">
                <i class="bi bi-bar-chart-fill"></i>
            </button>` : '';

        actionsCell.innerHTML = `
            <div class="action-btns">
                ${seriesDashboardBtn}
                <button class="btn-icon" onclick="viewTopic('${topic.topic_id}')" title="View Details">
                    <i class="bi bi-eye"></i>
                </button>
                <button class="btn-icon" onclick="changeStatus('${topic.topic_id}', '${topic.status}')" title="Change Status">
                    <i class="bi bi-arrow-repeat"></i>
                </button>
                <button class="btn-icon" onclick="deleteTopic('${topic.topic_id}')" title="Delete">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        `;
        row.appendChild(actionsCell);

        tbody.appendChild(row);
    });
}

/**
 * Open Add Topic Modal
 */
function openAddTopicModal() {
    if (!currentChannelId) {
        showToast('Please select a channel first', 'error');
        return;
    }

    editingTopicId = null;
    document.getElementById('modalTitle').textContent = 'Add New Topic';
    document.getElementById('topicForm').reset();
    document.getElementById('topicPriority').value = 100;
    document.getElementById('toneSuggestion').value = 'dark';
    document.getElementById('topicModal').classList.add('active');
}

/**
 * Close Topic Modal
 */
function closeTopicModal() {
    document.getElementById('topicModal').classList.remove('active');
    editingTopicId = null;
}

/**
 * Save Topic (Add or Update)
 */
async function saveTopic(event) {
    event.preventDefault();

    const topicText = document.getElementById('topicText').value.trim();
    const context = document.getElementById('topicContext').value.trim();
    const toneSuggestion = document.getElementById('toneSuggestion').value;
    const priority = parseInt(document.getElementById('topicPriority').value);
    const keyElementsRaw = document.getElementById('keyElements').value.trim();

    const keyElements = keyElementsRaw ? keyElementsRaw.split(',').map(el => el.trim()).filter(el => el.length > 0) : [];

    const payload = {
        user_id: currentUserId,
        channel_id: currentChannelId,
        topic_text: topicText,
        topic_description: {
            context: context,
            tone_suggestion: toneSuggestion,
            key_elements: keyElements
        },
        priority: priority
    };

    try {
        const response = await fetch(LAMBDA_URLS.ADD, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (data.success) {
            showToast('Topic added successfully!', 'success');
            closeTopicModal();
            await loadTopics();
        } else {
            showToast(data.error || 'Failed to add topic', 'error');
        }
    } catch (error) {
        console.error('Error saving topic:', error);
        showToast('Failed to save topic', 'error');
    }
}

/**
 * View Topic Details
 */
function viewTopic(topicId) {
    const topic = allTopics.find(t => t.topic_id === topicId);
    if (!topic) return;

    // Populate modal fields
    document.getElementById('viewTopicText').textContent = topic.topic_text;
    document.getElementById('viewTopicContext').textContent = topic.topic_description?.context || 'No context provided';
    document.getElementById('viewTopicCreated').textContent = formatDate(topic.created_at);
    document.getElementById('viewTopicUpdated').textContent = formatDate(topic.updated_at);

    // Status badge
    const statusBadge = document.getElementById('viewTopicStatus');
    statusBadge.textContent = topic.status.replace('_', ' ');
    statusBadge.className = `status-badge status-${topic.status}`;

    // Priority badge
    const priorityBadge = document.getElementById('viewTopicPriority');
    const priorityClass = topic.priority >= 200 ? 'priority-high' : (topic.priority >= 100 ? 'priority-medium' : 'priority-low');
    priorityBadge.textContent = topic.priority;
    priorityBadge.className = `priority-badge ${priorityClass}`;

    // Show modal
    document.getElementById('viewTopicModal').classList.add('active');
}

/**
 * Close View Topic Modal
 */
function closeViewTopicModal() {
    document.getElementById('viewTopicModal').classList.remove('active');
}

// Global variable for status change
let pendingStatusChange = null;

/**
 * Change Topic Status
 */
function changeStatus(topicId, currentStatus) {
    const topic = allTopics.find(t => t.topic_id === topicId);
    if (!topic) return;

    // Valid transitions based on state machine
    const validTransitions = {
        'draft': ['approved', 'deleted'],
        'approved': ['queued', 'deleted'],
        'queued': ['in_progress', 'deleted'],
        'in_progress': ['published', 'failed', 'deleted'],
        'published': ['archived', 'deleted'],
        'failed': ['queued', 'deleted'],
        'archived': ['deleted']
    };

    const allowedStatuses = validTransitions[currentStatus] || [];

    if (allowedStatuses.length === 0) {
        showToast('No valid status transitions available', 'error');
        return;
    }

    // Set current topic ID for later
    pendingStatusChange = { topicId, currentStatus };

    // Show current status
    document.getElementById('currentStatusText').textContent = currentStatus.replace('_', ' ');

    // Generate status buttons
    const container = document.getElementById('statusButtonsContainer');
    container.innerHTML = '';

    // Status button configs with icons and colors
    const statusConfigs = {
        'approved': { icon: 'bi-check-circle', color: '#10b981', label: 'Approve' },
        'queued': { icon: 'bi-list-check', color: '#3b82f6', label: 'Queue' },
        'in_progress': { icon: 'bi-arrow-clockwise', color: '#f59e0b', label: 'In Progress' },
        'published': { icon: 'bi-check-all', color: '#8b5cf6', label: 'Published' },
        'failed': { icon: 'bi-x-circle', color: '#ef4444', label: 'Mark Failed' },
        'archived': { icon: 'bi-archive', color: '#64748b', label: 'Archive' },
        'deleted': { icon: 'bi-trash', color: '#ef4444', label: 'Delete' }
    };

    allowedStatuses.forEach(status => {
        const config = statusConfigs[status] || { icon: 'bi-circle', color: '#94a3b8', label: status };
        const button = document.createElement('button');
        button.className = 'btn btn-secondary';
        button.style.justifyContent = 'flex-start';
        button.style.background = `linear-gradient(135deg, ${config.color}22 0%, ${config.color}11 100%)`;
        button.style.borderColor = `${config.color}44`;
        button.style.color = config.color;
        button.innerHTML = `<i class="bi ${config.icon}"></i> ${config.label}`;
        button.onclick = () => executeStatusChange(status);
        container.appendChild(button);
    });

    // Show modal
    document.getElementById('changeStatusModal').classList.add('active');
}

/**
 * Execute status change
 */
async function executeStatusChange(newStatus) {
    if (!pendingStatusChange) return;

    const { topicId } = pendingStatusChange;

    closeChangeStatusModal();

    try {
        const payload = {
            user_id: currentUserId,
            channel_id: currentChannelId,
            topic_id: topicId,
            new_status: newStatus
        };

        const response = await fetch(LAMBDA_URLS.UPDATE_STATUS, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (data.success) {
            showToast(`Status updated to ${newStatus.replace('_', ' ')}`, 'success');
            await loadTopics();
        } else {
            showToast(data.error || 'Failed to update status', 'error');
        }
    } catch (error) {
        console.error('Error updating status:', error);
        showToast('Failed to update status', 'error');
    }

    pendingStatusChange = null;
}

/**
 * Close Change Status Modal
 */
function closeChangeStatusModal() {
    document.getElementById('changeStatusModal').classList.remove('active');
    pendingStatusChange = null;
}

// Global variable for delete confirmation
let pendingDeleteTopicId = null;

/**
 * Delete Topic
 */
function deleteTopic(topicId) {
    const topic = allTopics.find(t => t.topic_id === topicId);
    if (!topic) return;

    // Set pending delete
    pendingDeleteTopicId = topicId;

    // Show topic text in modal
    document.getElementById('deleteTopicText').textContent = `"${topic.topic_text}"`;

    // Show modal
    document.getElementById('deleteConfirmModal').classList.add('active');
}

/**
 * Confirm and execute delete
 */
async function confirmDelete() {
    if (!pendingDeleteTopicId) return;

    const topicId = pendingDeleteTopicId;
    closeDeleteConfirmModal();

    try {
        const payload = {
            user_id: currentUserId,
            channel_id: currentChannelId,
            topic_id: topicId,
            new_status: 'deleted'
        };

        const response = await fetch(LAMBDA_URLS.UPDATE_STATUS, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (data.success) {
            showToast('Topic deleted', 'success');
            await loadTopics();
        } else {
            showToast(data.error || 'Failed to delete topic', 'error');
        }
    } catch (error) {
        console.error('Error deleting topic:', error);
        showToast('Failed to delete topic', 'error');
    }

    pendingDeleteTopicId = null;
}

/**
 * Close Delete Confirmation Modal
 */
function closeDeleteConfirmModal() {
    document.getElementById('deleteConfirmModal').classList.remove('active');
    pendingDeleteTopicId = null;
}

/**
 * Show toast notification
 */
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toastMessage');
    const toastIcon = document.getElementById('toastIcon');

    toast.className = `toast toast-${type} active`;
    toastMessage.textContent = message;

    if (type === 'success') {
        toastIcon.className = 'bi bi-check-circle';
    } else {
        toastIcon.className = 'bi bi-exclamation-circle';
    }

    setTimeout(() => {
        toast.classList.remove('active');
    }, 3000);
}

/**
 * Open Bulk Add Modal
 */
function openBulkAddModal() {
    if (!currentChannelId) {
        showToast('Please select a channel first', 'error');
        return;
    }

    document.getElementById('bulkForm').reset();
    document.getElementById('bulkPriority').value = 100;
    document.getElementById('bulkStatus').value = 'draft';
    document.getElementById('bulkTone').value = 'dark';
    document.getElementById('bulkSeason').value = 1;
    document.getElementById('bulkAutoDetect').value = 'true';
    document.getElementById('topicCount').textContent = '0';
    document.getElementById('bulkModal').classList.add('active');
}

/**
 * Close Bulk Modal
 */
function closeBulkModal() {
    document.getElementById('bulkModal').classList.remove('active');
}

/**
 * Update topic count as user types
 */
function updateBulkTopicCount() {
    const textarea = document.getElementById('bulkTopicsList');
    const countSpan = document.getElementById('topicCount');

    const text = textarea.value.trim();
    if (!text) {
        countSpan.textContent = '0';
        return;
    }

    const lines = text.split('\n').filter(line => line.trim().length > 0);
    countSpan.textContent = lines.length;

    // Warn if over 500
    if (lines.length > 500) {
        countSpan.style.color = '#ef4444';
        countSpan.textContent = `${lines.length} (max 500!)`;
    } else {
        countSpan.style.color = '#10b981';
    }
}

/**
 * Save Bulk Topics
 */
async function saveBulkTopics(event) {
    event.preventDefault();

    const topicsText = document.getElementById('bulkTopicsList').value.trim();
    const seriesId = document.getElementById('bulkSeriesId').value.trim();
    const season = parseInt(document.getElementById('bulkSeason').value);
    const priority = parseInt(document.getElementById('bulkPriority').value);
    const status = document.getElementById('bulkStatus').value;
    const toneSuggestion = document.getElementById('bulkTone').value;
    const autoDetect = document.getElementById('bulkAutoDetect').value === 'true';
    const keyElementsRaw = document.getElementById('bulkKeyElements').value.trim();

    // Parse topics
    const topics = topicsText.split('\n').filter(line => line.trim().length > 0);

    if (topics.length === 0) {
        showToast('Please enter at least one topic', 'error');
        return;
    }

    if (topics.length > 500) {
        showToast('Maximum 500 topics allowed per bulk add', 'error');
        return;
    }

    const keyElements = keyElementsRaw ? keyElementsRaw.split(',').map(el => el.trim()).filter(el => el.length > 0) : [];

    const payload = {
        user_id: currentUserId,
        channel_id: currentChannelId,
        topics: topics,
        default_priority: priority,
        default_status: status,
        series_id: seriesId || undefined,
        season: season,
        auto_detect_episode: autoDetect,
        tone_suggestion: toneSuggestion,
        key_elements: keyElements
    };

    try {
        showToast('Adding topics in bulk...', 'success');

        const response = await fetch(LAMBDA_URLS.BULK_ADD, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (data.success) {
            const message = `Successfully added ${data.topics_added} topics` +
                (data.series_id ? ` (Series: ${data.series_id}, Episodes: ${data.episodes_detected || 0})` : '');
            showToast(message, 'success');
            closeBulkModal();
            await loadTopics();
        } else {
            showToast(data.error || 'Failed to add topics', 'error');
        }
    } catch (error) {
        console.error('Error saving bulk topics:', error);
        showToast('Failed to save bulk topics', 'error');
    }
}

/**
 * Format date
 */
function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now - date;

    // Less than 1 minute
    if (diff < 60000) return 'Just now';

    // Less than 1 hour
    if (diff < 3600000) {
        const minutes = Math.floor(diff / 60000);
        return `${minutes}m ago`;
    }

    // Less than 24 hours
    if (diff < 86400000) {
        const hours = Math.floor(diff / 3600000);
        return `${hours}h ago`;
    }

    // Less than 7 days
    if (diff < 604800000) {
        const days = Math.floor(diff / 86400000);
        return `${days}d ago`;
    }

    // Full date
    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
    });
}

// Deployment trigger: 20260222-212835

/**
 * Open Series Dashboard
 */
function openSeriesDashboard(seriesId, channelId) {
    window.open(`series-manager.html?series_id=${seriesId}&channel_id=${channelId}`, '_blank');
}
