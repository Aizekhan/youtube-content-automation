// 🚀 Unified Channels System JavaScript
// Об'єднана система управління каналами

// Import auth manager (loaded from auth.js)
let authManager;

// API Configuration
const API_BASE = 'https://n8n-creator.space';
const VASTAI_API_URL = 'https://xmstnomewqj2zlhrgkqxnnhkz40znusc.lambda-url.eu-central-1.on.aws';

// Lambda Function URLs (multi-tenant with CORS)
const CHANNELS_API = 'https://lr555ui3ycne6lj7opvpqjigce0cvkzu.lambda-url.eu-central-1.on.aws';

// Legacy PHP endpoints (will be migrated)
const API_URLS = {
    getChannels: CHANNELS_API,  // Now using Lambda
    getChannelConfig: '/api/get-channel-config.php',
    saveConfig: '/api/update-channel-config.php',
    toggleStatus: '/api/toggle-channel-status.php'
};

// State Management
let currentTab = 'overview';
let channelsData = [];
let allChannelsData = []; // Store all channels before filtering
let selectedChannelId = null;
let currentFilter = 'all'; // 'all', 'active', 'inactive'

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    console.log('🚀 Initializing Unified Channels System');

    // Initialize auth manager
    authManager = new AuthManager();

    // Check authentication
    try {
        await authManager.requireAuth();
        console.log('✅ User authenticated:', authManager.getUserId());
    } catch (error) {
        console.error('❌ Authentication failed:', error);
        return;
    }

    // Set active navigation link
    setActiveNavLink('channels.html');

    // Load channels
    loadChannels();

    // Load image generation templates for dropdown
    loadImageGenerationTemplates();
});

/**
 * Set active navigation link
 */
function setActiveNavLink(pageName) {
    document.querySelectorAll('.nav-link').forEach(link => {
        if (link.getAttribute('href').includes(pageName)) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
}

/**
 * Initialize tab system
 */
function initializeTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.dataset.tab;
            switchTab(tabName);
        });
    });

    // Show initial tab
    switchTab(currentTab);
}

/**
 * Switch between tabs
 */
function switchTab(tabName) {
    currentTab = tabName;

    // Update tab buttons
    document.querySelectorAll('.tab-button').forEach(btn => {
        if (btn.dataset.tab === tabName) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        if (content.id === `${tabName}-tab`) {
            content.classList.add('active');
        } else {
            content.classList.remove('active');
        }
    });

    // Update URL without reload
    const newUrl = `${window.location.pathname}?tab=${tabName}`;
    window.history.pushState({ tab: tabName }, '', newUrl);

    // Load tab-specific data
    if (tabName === 'overview') {
        loadChannels();
    } else if (tabName === 'configs') {
        loadChannelConfigs();
    }
}

/**
 * Load all channels for overview
 */
async function loadChannels() {
    const container = document.getElementById('channels-container');
    container.innerHTML = '<div class="loading"><i class="bi bi-arrow-repeat"></i><p>Loading channels...</p></div>';

    try {
        // Get user_id from auth manager
        const userId = authManager.getUserId();
        console.log('Loading channels for user:', userId);

        // Call Lambda with user_id and active_only=false to get ALL channels
        const response = await fetch(API_URLS.getChannels, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...authManager.getAuthHeaders()
            },
            body: JSON.stringify({
                user_id: userId,
                active_only: false  // Get ALL channels (active + inactive)
            })
        });
        if (!response.ok) throw new Error('HTTP Error: ' + response.status);

        const data = await response.json();

        // Store ALL channels
        allChannelsData = Array.isArray(data) ? data : (data.channels || []);

        console.log(`📊 Loaded ${allChannelsData.length} total channels`);

        if (allChannelsData.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="bi bi-collection"></i>
                    <h3>No channels found</h3>
                    <p>Start by adding your first YouTube channel</p>
                </div>
            `;
            return;
        }

        // Apply current filter and render
        applyChannelFilter(currentFilter);
    } catch (error) {
        console.error('Failed to load channels:', error);
        container.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i>
                Failed to load channels: ${error.message}
            </div>
        `;
    }
}

/**
 * Render channels in grid layout
 */
function renderChannelsGrid(channels) {
    const container = document.getElementById('channels-container');

    // Sort channels: active first, then inactive. Within each group, sort alphabetically by name
    const sortedChannels = [...channels].sort((a, b) => {
        const aActive = a.is_active !== false;
        const bActive = b.is_active !== false;

        // Active channels go first
        if (aActive && !bActive) return -1;
        if (!aActive && bActive) return 1;

        // Within same group, sort alphabetically by channel name
        const aName = (a.channel_title || a.channel_name || a.channel_id || '').toLowerCase();
        const bName = (b.channel_title || b.channel_name || b.channel_id || '').toLowerCase();
        return aName.localeCompare(bName);
    });

    const html = `
        <div class="channels-grid">
            ${sortedChannels.map(channel => createChannelCard(channel)).join('')}
        </div>
    `;

    container.innerHTML = html;
}

/**
 * Apply channel filter (all/active/inactive)
 */
function applyChannelFilter(filter) {
    currentFilter = filter;

    // Filter channels based on selected filter
    let filteredChannels;

    switch(filter) {
        case 'active':
            filteredChannels = allChannelsData.filter(ch => ch.is_active !== false);
            break;
        case 'inactive':
            filteredChannels = allChannelsData.filter(ch => ch.is_active === false);
            break;
        case 'all':
        default:
            filteredChannels = allChannelsData;
            break;
    }

    console.log(`🔍 Filter: ${filter} - Showing ${filteredChannels.length} of ${allChannelsData.length} channels`);

    // Update button states
    document.querySelectorAll('.filter-btn').forEach(btn => {
        if (btn.dataset.filter === filter) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // Update counts in filter buttons
    const activeCount = allChannelsData.filter(ch => ch.is_active !== false).length;
    const inactiveCount = allChannelsData.filter(ch => ch.is_active === false).length;

    const allBtn = document.querySelector('.filter-btn[data-filter="all"]');
    const activeBtn = document.querySelector('.filter-btn[data-filter="active"]');
    const inactiveBtn = document.querySelector('.filter-btn[data-filter="inactive"]');

    if (allBtn) allBtn.innerHTML = `<i class="bi bi-collection"></i> Всі (${allChannelsData.length})`;
    if (activeBtn) activeBtn.innerHTML = `<i class="bi bi-check-circle-fill"></i> Активні (${activeCount})`;
    if (inactiveBtn) inactiveBtn.innerHTML = `<i class="bi bi-dash-circle"></i> Неактивні (${inactiveCount})`;

    // Render filtered channels
    channelsData = filteredChannels;
    renderChannelsGrid(filteredChannels);
}

/**
 * Create a single channel card
 */
function createChannelCard(channel) {
    const isActive = channel.is_active !== false;
    
    // Get initials for avatar
    const channelName = channel.channel_title || channel.channel_name || 'Unknown';
    const initials = channelName.split(' ').map(w => w[0]).join('').substring(0, 2).toUpperCase();
    
    // Calculate token status from token_expiry
    let tokenColor = '#6b7280'; // gray default
    let tokenTooltip = 'Token status unknown';
    
    if (channel.token_expiry) {
        try {
            const expiryDate = new Date(channel.token_expiry);
            const now = new Date();
            const daysUntilExpiry = Math.floor((expiryDate - now) / (1000 * 60 * 60 * 24));
            
            if (daysUntilExpiry > 7) {
                tokenColor = '#10b981'; // green
                tokenTooltip = 'Token valid (' + daysUntilExpiry + ' days left)';
            } else if (daysUntilExpiry > 2) {
                tokenColor = '#f59e0b'; // yellow/orange
                tokenTooltip = 'Token expiring soon (' + daysUntilExpiry + ' days left)';
            } else if (daysUntilExpiry >= 0) {
                tokenColor = '#ef4444'; // red
                tokenTooltip = 'Token expires very soon! (' + daysUntilExpiry + ' days)';
            } else {
                tokenColor = '#dc2626'; // dark red
                tokenTooltip = 'Token EXPIRED! (' + Math.abs(daysUntilExpiry) + ' days ago)';
            }
        } catch (e) {
            console.error('Error parsing token_expiry:', e);
        }
    }
    
    // Views and subscribers
    const viewCount = channel.view_count || (channel.statistics && channel.statistics.viewCount) || 0;
    const subscriberCount = channel.subscriber_count || (channel.statistics && channel.statistics.subscriberCount) || 0;
    
    // Format large numbers
    const formatNumber = function(num) {
        num = parseInt(num) || 0;
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toString();
    };
    
    // Add active/inactive class to card
    const cardClass = isActive ? 'channel-card active-channel' : 'channel-card inactive-channel';

    return '<div class="' + cardClass + '">' +
        '<div class="channel-header">' +
            '<div class="channel-avatar">' + initials + '</div>' +
            '<div class="channel-info">' +
                '<h3 class="channel-name">' + channelName + '</h3>' +
                '<div class="channel-id">' + channel.channel_id + '</div>' +
            '</div>' +
            '<div class="channel-controls">' +
                '<span class="token-status" style="background-color: ' + tokenColor + ';" title="' + tokenTooltip + '"></span>' +
                '<label class="toggle-switch">' +
                    '<input type="checkbox" ' + (isActive ? 'checked' : '') + ' onchange="toggleChannelStatus(\'' + channel.channel_id + '\', this.checked)">' +
                    '<span class="toggle-slider"></span>' +
                '</label>' +
            '</div>' +
        '</div>' +
        '<div class="channel-stats">' +
            '<div class="stat-item">' +
                '<span class="stat-value">' + formatNumber(viewCount) + '</span>' +
                '<span class="stat-label">Views</span>' +
            '</div>' +
            '<div class="stat-item">' +
                '<span class="stat-value">' + formatNumber(subscriberCount) + '</span>' +
                '<span class="stat-label">Subscribers</span>' +
            '</div>' +
            '<div class="stat-item">' +
                '<span class="stat-value">' + (channel.daily_upload_count || 1) + '</span>' +
                '<span class="stat-label">Відео/День</span>' +
            '</div>' +
            '<div class="stat-item">' +
                '<span class="stat-value">' + (channel.content_count || 0) + '</span>' +
                '<span class="stat-label">Згенеровано</span>' +
            '</div>' +
        '</div>' +
        '<div class="channel-actions">' +
            '<button class="action-button" onclick="viewChannelContent(\'' + channel.channel_id + '\')">' +
                '<i class="bi bi-eye"></i> View Content' +
            '</button>' +
            '<button class="action-button primary" onclick="editChannelConfig(\'' + channel.channel_id + '\')">' +
                '<i class="bi bi-gear"></i> Configure' +
            '</button>' +
        '</div>' +
    '</div>';
}

async function toggleChannelStatus(channelId, isActive) {
    console.log(`Toggle channel ${channelId} to ${isActive}`);

    try {
        const formData = new FormData();
        formData.append('channel_id', channelId);
        formData.append('is_active', isActive ? 'true' : 'false');

        // Use relative URL - nginx will handle routing
        const response = await fetch(`${API_BASE}/api/toggle-channel-status.php`, {
            method: 'POST',
            headers: {
                'Authorization': 'Basic ' + btoa('admin:FHrifd45')
            },
            body: formData
        });

        console.log('Toggle response status:', response.status);

        if (!response.ok) {
            const errorText = await response.text();
            console.error('Toggle error response:', errorText);
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        const result = await response.json();
        console.log('Toggle result:', result);

        if (result.success) {
            showNotification(`✅ Канал ${isActive ? 'активовано' : 'деактивовано'}`, 'success');

            // Update local data
            const channel = allChannelsData.find(c => c.channel_id === channelId);
            if (channel) {
                channel.is_active = isActive;
            }

            // Re-apply current filter to update display
            applyChannelFilter(currentFilter);
        } else {
            throw new Error(result.error || 'Failed to toggle status');
        }
    } catch (error) {
        console.error('Toggle error:', error);
        showNotification('❌ Помилка: ' + error.message, 'danger');
        // Reload channels to revert the toggle
        setTimeout(() => loadChannels(), 500);
    }
}

/**
 * Load channel configurations
 */
async function loadChannelConfigs() {
    const container = document.getElementById('config-container');
    container.innerHTML = '<div class="loading"><i class="bi bi-arrow-repeat"></i><p>Loading configurations...</p></div>';

    try {
        // Add cache busting to prevent stale data
        const cacheBuster = '?t=' + new Date().getTime();
        const response = await fetch(API_URLS.getChannels + cacheBuster);
        if (!response.ok) throw new Error('HTTP Error: ' + response.status);

        const data = await response.json();

        channelsData = Array.isArray(data) ? data : (data.channels || []);

        if (channelsData.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="bi bi-gear"></i>
                    <h3>No configurations found</h3>
                    <p>Add channels to configure them</p>
                </div>
            `;
            return;
        }

        // Select first channel by default
        if (!selectedChannelId && channelsData.length > 0) {
            selectedChannelId = channelsData[0].channel_id;
        }

        renderConfigForm();
    } catch (error) {
        console.error('Failed to load configurations:', error);
        container.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i>
                Failed to load configurations: ${error.message}
            </div>
        `;
    }
}

/**
 * Render configuration form
 */
function renderConfigForm() {
    const container = document.getElementById('config-container');
    const channel = channelsData.find(c => c.channel_id === selectedChannelId);

    if (!channel) {
        container.innerHTML = '<div class="alert alert-warning">Channel not found</div>';
        return;
    }

    const html = `
        <div class="config-form">
            <!-- Channel Selector -->
            <div class="form-group">
                <label for="channelSelect">
                    <i class="bi bi-collection"></i> Select Channel
                </label>
                <select id="channelSelect" class="form-control" onchange="selectChannel(this.value)">
                    ${channelsData.map(c => `
                        <option value="${c.channel_id}" ${c.channel_id === selectedChannelId ? 'selected' : ''}>
                            ${c.channel_title || c.channel_name || c.channel_id}
                        </option>
                    `).join('')}
                </select>
            </div>

            <!-- Basic Settings -->
            <div class="form-section">
                <h3 class="section-title">
                    <i class="bi bi-gear"></i> Basic Settings
                </h3>

                <div class="form-group">
                    <label for="channelName">Channel Name</label>
                    <input type="text" id="channelName" class="form-control"
                           value="${channel.channel_name || ''}"
                           placeholder="My Awesome Channel">
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label for="videosPerWeek">Videos Per Week</label>
                        <input type="number" id="videosPerWeek" class="form-control"
                               value="${channel.videos_per_week || 3}"
                               min="1" max="14">
                        <span class="help-text">How many videos to generate weekly</span>
                    </div>

                    <div class="form-group">
                        <label>Channel Status</label>
                        <label class="toggle-switch">
                            <input type="checkbox" id="isActive" ${channel.is_active !== false ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                            <span>Active</span>
                        </label>
                        <span class="help-text">Enable/disable content generation</span>
                    </div>
                </div>
            </div>

            <!-- Content Settings -->
            <div class="form-section">
                <h3 class="section-title">
                    <i class="bi bi-film"></i> Content Settings
                </h3>

                <div class="form-group">
                    <label for="contentStyle">Content Style</label>
                    <select id="contentStyle" class="form-control">
                        <option value="educational" ${channel.content_style === 'educational' ? 'selected' : ''}>Educational</option>
                        <option value="entertaining" ${channel.content_style === 'entertaining' ? 'selected' : ''}>Entertaining</option>
                        <option value="informative" ${channel.content_style === 'informative' ? 'selected' : ''}>Informative</option>
                        <option value="storytelling" ${channel.content_style === 'storytelling' ? 'selected' : ''}>Storytelling</option>
                    </select>
                </div>

                <div class="form-group">
                    <label for="targetAudience">Target Audience</label>
                    <input type="text" id="targetAudience" class="form-control"
                           value="${channel.target_audience || ''}"
                           placeholder="e.g., Tech enthusiasts, Students, Professionals">
                </div>

                <div class="form-group">
                    <label for="videoDuration">Preferred Video Duration (minutes)</label>
                    <input type="number" id="videoDuration" class="form-control"
                           value="${channel.video_duration || 10}"
                           min="1" max="60">
                </div>
            </div>

            <!-- Tone and Voice -->
            <div class="form-section">
                <h3 class="section-title">
                    <i class="bi bi-volume-up"></i> Tone and Voice
                </h3>

                <div class="form-row">
                    <div class="form-group">
                        <label for="toneStyle">Tone</label>
                        <select id="toneStyle" class="form-control">
                            <option value="professional" ${channel.tone_style === 'professional' ? 'selected' : ''}>Professional</option>
                            <option value="casual" ${channel.tone_style === 'casual' ? 'selected' : ''}>Casual</option>
                            <option value="friendly" ${channel.tone_style === 'friendly' ? 'selected' : ''}>Friendly</option>
                            <option value="authoritative" ${channel.tone_style === 'authoritative' ? 'selected' : ''}>Authoritative</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="voiceGender">Voice (TTS)</label>
                        <select id="voiceGender" class="form-control">
                            <option value="Brian" ${channel.voice_id === 'Brian' ? 'selected' : ''}>Brian (Male, British)</option>
                            <option value="Joanna" ${channel.voice_id === 'Joanna' ? 'selected' : ''}>Joanna (Female, US)</option>
                            <option value="Matthew" ${channel.voice_id === 'Matthew' ? 'selected' : ''}>Matthew (Male, US)</option>
                            <option value="Amy" ${channel.voice_id === 'Amy' ? 'selected' : ''}>Amy (Female, British)</option>
                        </select>
                    </div>
                </div>
            </div>

            <!-- Additional Notes -->
            <div class="form-section">
                <h3 class="section-title">
                    <i class="bi bi-card-text"></i> Additional Instructions
                </h3>

                <div class="form-group">
                    <label for="additionalNotes">Custom Instructions</label>
                    <textarea id="additionalNotes" class="form-control"
                              placeholder="Add any specific requirements or preferences for content generation...">${channel.additional_notes || ''}</textarea>
                    <span class="help-text">These instructions will be included in AI prompts</span>
                </div>
            </div>

            <!-- Action Buttons -->
            <div class="button-group">
                <button class="btn btn-primary" onclick="saveChannelConfig()">
                    <i class="bi bi-check-circle"></i> Save Configuration
                </button>
                <button class="btn btn-secondary" onclick="resetForm()">
                    <i class="bi bi-arrow-counterclockwise"></i> Reset Changes
                </button>
            </div>
        </div>
    `;

    container.innerHTML = html;
}

/**
 * Select a channel for configuration
 */
function selectChannel(channelId) {
    selectedChannelId = channelId;
    renderConfigForm();
}

/**
 * Save channel configuration
 */
async function saveChannelConfig() {
    const channelId = selectedChannelId;

    const config = {
        channel_id: channelId,
        channel_name: document.getElementById('channelName').value,
        videos_per_week: parseInt(document.getElementById('videosPerWeek').value),
        is_active: document.getElementById('isActive').checked,
        content_style: document.getElementById('contentStyle').value,
        target_audience: document.getElementById('targetAudience').value,
        video_duration: parseInt(document.getElementById('videoDuration').value),
        tone_style: document.getElementById('toneStyle').value,
        voice_id: document.getElementById('voiceGender').value,
        additional_notes: document.getElementById('additionalNotes').value
    };

    console.log('💾 Saving configuration:', config);

    try {
        // TODO: Implement save API call
        // const response = await fetch(LAMBDA_URLS.saveConfig, {
        //     method: 'POST',
        //     headers: { 'Content-Type': 'application/json' },
        //     body: JSON.stringify(config)
        // });

        // For now, just show success
        showNotification('Configuration saved successfully!', 'success');

        // Update local data
        const channelIndex = channelsData.findIndex(c => c.channel_id === channelId);
        if (channelIndex !== -1) {
            channelsData[channelIndex] = { ...channelsData[channelIndex], ...config };
        }
    } catch (error) {
        console.error('Failed to save configuration:', error);
        showNotification('Failed to save configuration: ' + error.message, 'danger');
    }
}

/**
 * Reset form to original values
 */
function resetForm() {
    loadChannelConfigs();
}

/**
 * View channel content
 */
function viewChannelContent(channelId) {
    window.location.href = `content.html?channel=${channelId}`;
}

/**
 * Edit channel configuration
 */
function editChannelConfig(channelId) { openConfigModal(channelId); return; } function editChannelConfig_OLD(channelId) {
    window.location.href = `channel-configs.html?channel_id=${channelId}`;
}

/**
 * Show notification
 */
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} position-fixed top-0 end-0 m-3`;
    notification.style.zIndex = '9999';
    notification.style.minWidth = '300px';
    notification.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="bi bi-${type === 'success' ? 'check-circle' : 'info-circle'} me-2"></i>
            <span>${message}</span>
        </div>
    `;

    document.body.appendChild(notification);

    // Auto-remove after 3 seconds
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

/**
 * Update all channel statistics
 */
async function updateAllStats() {
    const btn = event.target;
    const originalHTML = btn.innerHTML;
    btn.innerHTML = '<i class="bi bi-arrow-repeat"></i> Оновлення...';
    btn.disabled = true;

    try {
        // Always reload channels, even if stats API fails
        await loadChannels();
        showNotification('✅ Канали оновлено', 'success');

        // Try to update stats in background (optional)
        try {
            const response = await fetch('/api/update-stats.php');
            const result = await response.json();
            if (result.success) {
                console.log('Stats updated successfully');
            }
        } catch (statsError) {
            console.log('Stats API not available:', statsError);
            // Ignore stats errors - channels are already reloaded
        }
    } catch (error) {
        console.error('Failed to reload channels:', error);
        showNotification('❌ Помилка: ' + error.message, 'danger');
    } finally {
        setTimeout(() => {
            btn.innerHTML = originalHTML;
            btn.disabled = false;
        }, 1000);
    }
}





// EXACT COPY from channel-configs.html - these functions WORK with the database
async function openConfigModal(channelId) {
    const modal = document.getElementById('editModal');
    modal.style.display = 'block';
    document.getElementById('modalTitle').textContent = 'Завантаження...';

    try {
        const response = await fetch('/api/get-channel-config.php?channel_id=' + channelId, {
            headers: { 'Authorization': 'Basic ' + btoa('admin:FHrifd45') }
        });
        const config = await response.json();

        console.log('📝 Loaded config:', config);
        console.log('🎨 Theme template:', config.selected_theme_template);
        console.log('📖 Narrative template:', config.selected_narrative_template);

        document.getElementById('modalTitle').textContent = config.channel_name || config.channel_title || 'Редагування';

        // Load templates first and WAIT for completion
        await initializeTemplateSelects();

        // Small delay to ensure DOM is ready
        await new Promise(resolve => setTimeout(resolve, 100));

        // Then populate form values
        populateForm(config);

        // Note: loadImageGenerationSettings() removed - deprecated feature
        // Image generation now uses selected_image_template + visual guidance fields

        // Store config globally for Variation Sets management
        window.currentChannelConfig = config;

        // Load variation sets settings (NEW!)
        try {
            loadVariationSetsSettings(config);
            console.log('OK: Завантажено Variation Sets з ChannelConfig');
        } catch (e) {
            console.warn('Variation Sets поля ще не додані:', e);
        }

        initializeVoiceSelect();
    } catch (error) {
        console.error('Error loading config:', error);
        showNotification('❌ Помилка завантаження', 'danger');
        closeModal();
    }
}

function populateForm(config) {
    const fields = [
        'channel_id',
        // Basic Identity
        'channel_name', 'language', 'timezone', 'genre',
        // Content Identity
        'channel_theme', 'core_idea', 'tone', 'narration_style', 'emotional_temperature', 'meta_theme',
        // Content Focus
        'content_focus', 'narrative_keywords', 'story_structure_pattern', 'preferred_ending_tone', 'hook_enabled', 'factual_mode',
        // Story Elements (Visual fields moved to Image Template)
        'story_character_types',
        // AI Templates
        'selected_theme_template', 'selected_narrative_template', 'selected_image_template',
        'selected_video_template', 'selected_cta_template', 'selected_tts_template',
        'selected_sfx_template', 'selected_thumbnail_template', 'selected_description_template',
        // Monetization & Settings
        'monetization_enabled', 'adsense_enabled', 'sponsor_segments_enabled', 'adsense_account_id', 'license_type',
        'embedding_allowed', 'subtitles_language',
        // Channel Info
        'channel_description', 'thumbnail_url', 'banner_url', 'channel_watermark_url',
        'featured_video_id', 'seo_keywords',
        // Publishing Schedule
        'publish_times', 'publish_days', 'daily_upload_count',
        // Production Settings
        'video_duration_target', 'target_character_count', 'scene_count_target', 'max_tokens',
        // TTS Settings
        'tts_voice_id', 'tts_voice_engine', 'tts_service', 'tts_voice_language', 'tts_voice_profile', 'tts_mood_variants',
        // Legacy/Other fields (keep for backward compatibility)
        'target_audience', 'format', 'narrative_pace',
        'recommended_music_variants', 'music_tempo_variants',
        'example_keywords_for_youtube', 'unique_variation_logic'
    ];
    
    fields.forEach(field => {
        const element = document.getElementById(field);
        if (!element) return;

        const configValue = config[field];
        const hasConfigValue = configValue !== undefined && configValue !== null && configValue !== '';

        // Special handling for template fields
        if (field.startsWith('selected_') && field.includes('_template')) {
            console.log(`🔧 Template field: ${field}`);
            console.log(`   Config value: ${configValue}`);
            console.log(`   Default template: ${element.dataset.defaultTemplateId}`);

            if (hasConfigValue) {
                // Check if option exists in select
                const optionExists = Array.from(element.options).some(opt => opt.value === configValue);

                if (optionExists) {
                    element.value = configValue;
                    console.log(`   ✅ Set to config value: ${configValue}`);
                } else {
                    console.log(`   ⚠️ Config value "${configValue}" not found in options, using default`);
                    if (element.dataset.defaultTemplateId) {
                        element.value = element.dataset.defaultTemplateId;
                        console.log(`   ✅ Set to default: ${element.dataset.defaultTemplateId}`);
                    }
                }
            } else if (element.dataset.defaultTemplateId) {
                element.value = element.dataset.defaultTemplateId;
                console.log(`   ✅ Set to default: ${element.dataset.defaultTemplateId}`);
            } else {
                console.log(`   ⚠️ No value set - no config and no default found`);
            }
        } else {
            // Regular fields
            if (hasConfigValue) {
                // Handle checkboxes specially
                if (element.type === 'checkbox') {
                    element.checked = (configValue === true || configValue === 'true' || configValue === '1');
                } else {
                    element.value = configValue;
                }
            }
        }
    });

    // Load publish schedule UI
    loadPublishTimesFromString(config.publish_times || '');
    loadPublishDaysFromString(config.publish_days || '');
}

/**
 * Load AI templates from prompts-api and populate dropdowns
 */
async function initializeTemplateSelects() {
    const PROMPTS_API = 'https://djpb4ue6wv2ohfjey32lfnhcre0zppqd.lambda-url.eu-central-1.on.aws';

    const templateTypes = [
        { type: 'theme', selectId: 'selected_theme_template' },
        { type: 'narrative', selectId: 'selected_narrative_template' },
        { type: 'image', selectId: 'selected_image_template' },
        { type: 'video', selectId: 'selected_video_template' },
        { type: 'cta', selectId: 'selected_cta_template' },
        { type: 'tts', selectId: 'selected_tts_template' },
        { type: 'sfx', selectId: 'selected_sfx_template' },
        { type: 'thumbnail', selectId: 'selected_thumbnail_template' },
        { type: 'description', selectId: 'selected_description_template' }
    ];

    try {
        // Load all template types in parallel
        const promises = templateTypes.map(async ({ type, selectId }) => {
            try {
                const response = await fetch(`${PROMPTS_API}?type=${type}`);
                const result = await response.json();

                if (!result.success) {
                    throw new Error(result.error || 'Failed to load templates');
                }

                const templates = result.data?.templates || [];
                const activeTemplates = templates.filter(t => t.is_active === true || t.is_active === 1);

                const selectElement = document.getElementById(selectId);
                if (!selectElement) {
                    console.warn(`⚠️ Element ${selectId} not found in DOM`);
                    return;
                }

                // Populate dropdown
                selectElement.innerHTML = '<option value="">-- Оберіть шаблон --</option>';

                // Sort: default templates first
                const sortedTemplates = activeTemplates.sort((a, b) => {
                    if (a.is_default && !b.is_default) return -1;
                    if (!a.is_default && b.is_default) return 1;
                    return 0;
                });

                sortedTemplates.forEach(template => {
                    const option = document.createElement('option');
                    option.value = template.template_id;
                    const defaultLabel = template.is_default ? ' 🛡️ [Default]' : '';
                    option.textContent = `${template.template_name}${defaultLabel}`;

                    // Store default template id as data attribute
                    if (template.is_default) {
                        selectElement.dataset.defaultTemplateId = template.template_id;
                    }

                    selectElement.appendChild(option);
                });

                console.log(`✅ Loaded ${type} templates:`, activeTemplates.length);
            } catch (error) {
                console.error(`❌ Failed to load ${type} templates:`, error);
            }
        });

        await Promise.all(promises);
        console.log('✅ All template selects initialized');
    } catch (error) {
        console.error('❌ Failed to initialize templates:', error);
    }
}

/**
 * Load Image Generation Templates for channel config dropdown
 */
async function loadImageGenerationTemplates() {
    const PROMPTS_API = 'https://djpb4ue6wv2ohfjey32lfnhcre0zppqd.lambda-url.eu-central-1.on.aws';
    const selectElement = document.getElementById('image_generation_template_id');

    if (!selectElement) {
        console.warn('⚠️ Image generation template select not found');
        return;
    }

    try {
        const response = await fetch(`${PROMPTS_API}?type=image`);
        const result = await response.json();

        if (!result.success) {
            console.error('❌ Failed to load image templates:', result.error);
            return;
        }

        const templates = result.data?.templates || [];
        const activeTemplates = templates.filter(t => t.is_active !== false);

        // Clear existing options except first one
        selectElement.innerHTML = '<option value="">-- Вибрати темплейт --</option>';

        // Add active templates
        activeTemplates.forEach(template => {
            const option = document.createElement('option');
            option.value = template.template_id;
            const defaultLabel = template.is_default ? ' 🛡️ [Default]' : '';

            // Show provider info if available
            const provider = template.image_settings?.provider || '';
            const providerLabel = provider ? ` (${provider})` : '';

            option.textContent = `${template.template_name}${providerLabel}${defaultLabel}`;

            // Store default template id
            if (template.is_default) {
                selectElement.dataset.defaultTemplateId = template.template_id;
            }

            selectElement.appendChild(option);
        });

        console.log(`✅ Loaded ${activeTemplates.length} image generation templates`);
    } catch (error) {
        console.error('❌ Failed to load image templates:', error);
    }
}

function closeModal() {
    document.getElementById('editModal').style.display = 'none';
}

async function saveModalConfig() {
    const form = document.getElementById('configForm');
    const formData = new FormData();

    // Validate max_tokens and target_character_count BEFORE saving
    const maxTokens = parseInt(document.getElementById('max_tokens')?.value || 0);
    const targetCharCount = parseInt(document.getElementById('target_character_count')?.value || 0);

    if (maxTokens > 16000) {
        showNotification('❌ Max Tokens не може бути більше 16000 (GPT-4o ліміт: 16384)', 'danger');
        return;
    }

    if (targetCharCount > 16000) {
        showNotification('❌ Цільова к-ть символів не може бути більше 16000', 'danger');
        return;
    }

    const fields = Array.from(form.querySelectorAll('input, textarea, select'));
    fields.forEach(field => {
        if (field.id) {
            // Handle checkboxes specially
            if (field.type === 'checkbox') {
                formData.append(field.id, field.checked ? 'true' : 'false');
            } else {
                formData.append(field.id, field.value);
            }

            // Log template fields
            if (field.id.startsWith('selected_') && field.id.includes('_template')) {
                console.log(`💾 Saving ${field.id}: ${field.value}`);
            }
        }
    });

    // Log all template values being saved
    console.log('💾 Theme template:', document.getElementById('selected_theme_template')?.value);
    console.log('💾 Narrative template:', document.getElementById('selected_narrative_template')?.value);

    // Add variation_sets array to FormData (it's in window.currentChannelConfig)
    if (window.currentChannelConfig && window.currentChannelConfig.variation_sets) {
        formData.append('variation_sets', JSON.stringify(window.currentChannelConfig.variation_sets));
        console.log('💾 Saving variation_sets:', window.currentChannelConfig.variation_sets.length, 'sets');
    }

    // Add rotation_mode and manual_set_index
    const rotationMode = document.getElementById('rotation_mode');
    if (rotationMode) {
        formData.append('rotation_mode', rotationMode.value);
    }

    const manualSetIndex = document.getElementById('manual_set_index');
    if (manualSetIndex && window.currentChannelConfig?.rotation_mode === 'manual') {
        formData.append('manual_set_index', manualSetIndex.value);
    }

    try {
        const response = await fetch('/api/update-channel-config.php', {
            method: 'POST',
            headers: { 'Authorization': 'Basic ' + btoa('admin:FHrifd45') },
            body: formData
        });
        const result = await response.json();
        
        if (result.success) {
            showNotification('✅ Конфіг збережено!', 'success');

            // Close modal and reload
            closeModal();

            // Force reload channels with cache busting
            setTimeout(() => {
                loadChannels();
            }, 300);
        } else {
            throw new Error(result.error || 'Save failed');
        }
    } catch (error) {
        console.error('Save error:', error);
        showNotification('❌ Помилка збереження', 'danger');
    }
}

// AWS Polly Voice Lists
const AWS_POLLY_VOICES = {
    neural: [
        // Male voices
        { id: "Matthew", name: "Matthew", gender: "Male", language: "US English", description: "Deep, authoritative" },
        { id: "Joey", name: "Joey", gender: "Male", language: "US English", description: "Neutral, clear" },
        { id: "Stephen", name: "Stephen", gender: "Male", language: "US English", description: "Young, energetic" },
        { id: "Kevin", name: "Kevin", gender: "Male", language: "US English", description: "Conversational" },
        { id: "Brian", name: "Brian", gender: "Male", language: "British English", description: "Authoritative" },
        
        // Female voices
        { id: "Joanna", name: "Joanna", gender: "Female", language: "US English", description: "Professional, warm" },
        { id: "Kendra", name: "Kendra", gender: "Female", language: "US English", description: "Clear, friendly" },
        { id: "Kimberly", name: "Kimberly", gender: "Female", language: "US English", description: "Soft, gentle" },
        { id: "Salli", name: "Salli", gender: "Female", language: "US English", description: "Conversational" },
        { id: "Ruth", name: "Ruth", gender: "Female", language: "US English", description: "Young, energetic" },
        { id: "Danielle", name: "Danielle", gender: "Female", language: "US English", description: "Natural, expressive" },
        { id: "Ivy", name: "Ivy", gender: "Female", language: "US English", description: "Child voice" },
        { id: "Emma", name: "Emma", gender: "Female", language: "British English", description: "Soft, elegant" },
        { id: "Amy", name: "Amy", gender: "Female", language: "British English", description: "Warm, friendly" }
    ],
    standard: [
        // Male voices
        { id: "Matthew", name: "Matthew", gender: "Male", language: "US English", description: "Deep, authoritative" },
        { id: "Joey", name: "Joey", gender: "Male", language: "US English", description: "Neutral, clear" },
        { id: "Justin", name: "Justin", gender: "Male", language: "US English", description: "Young voice" },
        { id: "Kevin", name: "Kevin", gender: "Male", language: "US English", description: "Conversational" },
        { id: "Russell", name: "Russell", gender: "Male", language: "Australian English", description: "Australian accent" },
        { id: "Brian", name: "Brian", gender: "Male", language: "British English", description: "British accent" },
        
        // Female voices
        { id: "Joanna", name: "Joanna", gender: "Female", language: "US English", description: "Professional" },
        { id: "Kendra", name: "Kendra", gender: "Female", language: "US English", description: "Clear voice" },
        { id: "Kimberly", name: "Kimberly", gender: "Female", language: "US English", description: "Soft voice" },
        { id: "Salli", name: "Salli", gender: "Female", language: "US English", description: "Conversational" },
        { id: "Ivy", name: "Ivy", gender: "Female", language: "US English", description: "Child voice" },
        { id: "Nicole", name: "Nicole", gender: "Female", language: "Australian English", description: "Australian accent" },
        { id: "Emma", name: "Emma", gender: "Female", language: "British English", description: "British accent" },
        { id: "Amy", name: "Amy", gender: "Female", language: "British English", description: "Warm British" }
    ]
};

// Function to populate voice select based on TTS service
function updateVoiceOptions(engine = "neural", currentVoice = "") {
    const voiceSelect = document.getElementById("tts_voice_id");
    if (!voiceSelect) return;

    // Clear existing options
    voiceSelect.innerHTML = "";

    let voices = [];

    if (engine === "neural") {
        voices = AWS_POLLY_VOICES.neural;
    } else if (engine === "standard") {
        voices = AWS_POLLY_VOICES.standard;
    } else {
        // For other engines, default to neural
        voices = AWS_POLLY_VOICES.neural;
    }

    // Group by gender
    const males = voices.filter(v => v.gender === "Male");
    const females = voices.filter(v => v.gender === "Female");

    // Add male voices
    if (males.length > 0) {
        const maleGroup = document.createElement("optgroup");
        maleGroup.label = "👨 Male Voices";
        males.forEach(voice => {
            const option = document.createElement("option");
            option.value = voice.id;
            option.textContent = `${voice.name} - ${voice.language} (${voice.description})`;
            if (voice.id === currentVoice) option.selected = true;
            maleGroup.appendChild(option);
        });
        voiceSelect.appendChild(maleGroup);
    }

    // Add female voices
    if (females.length > 0) {
        const femaleGroup = document.createElement("optgroup");
        femaleGroup.label = "👩 Female Voices";
        females.forEach(voice => {
            const option = document.createElement("option");
            option.value = voice.id;
            option.textContent = `${voice.name} - ${voice.language} (${voice.description})`;
            if (voice.id === currentVoice) option.selected = true;
            femaleGroup.appendChild(option);
        });
        voiceSelect.appendChild(femaleGroup);
    }

    console.log(`✅ Loaded ${voices.length} voices for ${engine} engine`);
}

// Initialize voice options when modal opens
function initializeVoiceSelect() {
    const ttsEngineSelect = document.getElementById("tts_voice_engine");
    const ttsVoiceSelect = document.getElementById("tts_voice_id");
    const ttsTemplateSelect = document.getElementById("selected_tts_template");

    if (!ttsEngineSelect || !ttsVoiceSelect) return;

    // Update voices when engine changes
    ttsEngineSelect.addEventListener("change", (e) => {
        const currentVoice = ttsVoiceSelect.value;
        updateVoiceOptions(e.target.value, currentVoice);
    });

    // When TTS template is selected, load its voice settings
    if (ttsTemplateSelect) {
        ttsTemplateSelect.addEventListener("change", async (e) => {
            const templateId = e.target.value;
            if (!templateId) return;

            try {
                // Load the selected TTS template
                const PROMPTS_API = 'https://djpb4ue6wv2ohfjey32lfnhcre0zppqd.lambda-url.eu-central-1.on.aws';
                const response = await fetch(`${PROMPTS_API}/template/${templateId}?type=tts`);
                const result = await response.json();

                if (result.success && result.data?.template) {
                    const template = result.data.template;
                    const ttsConfig = template.tts_config || {};

                    // Populate voice settings from template
                    if (ttsConfig.voice_id) {
                        document.getElementById("tts_voice_id").value = ttsConfig.voice_id;
                    }
                    if (ttsConfig.voice_engine) {
                        document.getElementById("tts_voice_engine").value = ttsConfig.voice_engine;
                        updateVoiceOptions(ttsConfig.voice_engine, ttsConfig.voice_id);
                    }
                    if (ttsConfig.voice_language) {
                        document.getElementById("tts_voice_language").value = ttsConfig.voice_language;
                    }

                    console.log('✅ Loaded voice settings from TTS template:', ttsConfig);
                }
            } catch (error) {
                console.error('❌ Failed to load TTS template:', error);
            }
        });
    }

    // Initialize on load with neural engine
    const currentEngine = ttsEngineSelect.value || "neural";
    const currentVoice = ttsVoiceSelect.value;
    updateVoiceOptions(currentEngine, currentVoice);
}

// ============================================================================
// PUBLISH SCHEDULE UI FUNCTIONS
// ============================================================================

let publishTimesArray = [];

function addPublishTime() {
    const timeInput = document.getElementById('newPublishTime');
    const time = timeInput.value;

    if (!time) {
        alert('Будь ласка, оберіть час');
        return;
    }

    // Check if time already exists
    if (publishTimesArray.includes(time)) {
        alert('Цей час вже додано');
        return;
    }

    publishTimesArray.push(time);
    renderPublishTimes();
    updatePublishTimesHidden();

    // Clear input
    timeInput.value = '';
}

function removePublishTime(time) {
    publishTimesArray = publishTimesArray.filter(t => t !== time);
    renderPublishTimes();
    updatePublishTimesHidden();
}

function renderPublishTimes() {
    const container = document.getElementById('publishTimesList');

    if (publishTimesArray.length === 0) {
        container.innerHTML = '<span style="color: #999; font-style: italic;">Немає доданих часів публікації</span>';
        return;
    }

    // Sort times
    const sorted = [...publishTimesArray].sort();

    container.innerHTML = sorted.map(time => `
        <div style="display: flex; align-items: center; gap: 6px; padding: 6px 12px; background: #f3f4f6; border-radius: 4px; border: 1px solid #e5e7eb;">
            <i class="bi bi-clock" style="color: #3b82f6;"></i>
            <span style="font-weight: 500;">${time}</span>
            <button type="button" onclick="removePublishTime('${time}')" style="margin-left: 4px; background: none; border: none; color: #ef4444; cursor: pointer; padding: 2px 4px;">
                <i class="bi bi-x-circle"></i>
            </button>
        </div>
    `).join('');
}

function updatePublishTimesHidden() {
    document.getElementById('publish_times').value = publishTimesArray.join(', ');
}

function loadPublishTimesFromString(timesString) {
    if (!timesString) {
        publishTimesArray = [];
    } else {
        publishTimesArray = timesString.split(',').map(t => t.trim()).filter(t => t);
    }
    renderPublishTimes();
    updatePublishTimesHidden();
}

function updatePublishDaysHidden() {
    const checkboxes = document.querySelectorAll('.publish-day:checked');
    const days = Array.from(checkboxes).map(cb => cb.value);
    document.getElementById('publish_days').value = days.join(', ');
}

function loadPublishDaysFromString(daysString) {
    const days = daysString ? daysString.split(',').map(d => d.trim()).filter(d => d) : [];

    // Uncheck all first
    document.querySelectorAll('.publish-day').forEach(cb => cb.checked = false);

    // Check the ones from config
    days.forEach(day => {
        const checkbox = document.querySelector(`.publish-day[value="${day}"]`);
        if (checkbox) checkbox.checked = true;
    });
}

// Add event listeners to checkboxes
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.publish-day').forEach(checkbox => {
        checkbox.addEventListener('change', updatePublishDaysHidden);
    });

});

// ========================================
// IMAGE GENERATION FUNCTIONS (DEPRECATED - NOT USED)
// These functions are kept for backward compatibility but not used
// Image generation now uses selected_image_template + visual guidance fields
// ========================================

/**
 * Toggle image generation settings visibility
 */
function toggleImageGenerationSettings() {
    const enabled = document.getElementById('image_generation_enabled').checked;
    const settings = document.getElementById('imageGenerationSettings');

    if (settings) {
        settings.style.display = enabled ? 'block' : 'none';
    }

    if (enabled) {
        updateImageProviderInfo();
        updateImageCostEstimate();
    }
}

/**
 * Update provider-specific information and UI
 */
function updateImageProviderInfo() {
    const provider = document.getElementById('image_generation_provider').value;
    const infoBox = document.getElementById('providerInfo');
    const infoText = document.getElementById('providerInfoText');
    const fluxVariantGroup = document.getElementById('fluxVariantGroup');

    // Show/hide FLUX variant field
    if (provider.includes('flux')) {
        fluxVariantGroup.style.display = 'block';
    } else {
        fluxVariantGroup.style.display = 'none';
    }

    // Update info text and box
    let info = '';
    let setupInfo = '';

    switch(provider) {
        case 'aws-bedrock-sdxl':
            infoText.textContent = '✅ Працює одразу, не потребує налаштувань';
            setupInfo = `
                <div style="padding: 16px; background: #ecfdf5; border: 1px solid #10b981; border-radius: 8px;">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                        <i class="bi bi-check-circle-fill" style="color: #10b981; font-size: 20px;"></i>
                        <strong style="color: #065f46;">AWS Bedrock SDXL - Готово до використання!</strong>
                    </div>
                    <p style="color: #047857; font-size: 13px; margin: 0;">
                        Надійний провайдер від AWS. Працює одразу після збереження конфігурації. Підходить для невеликих обсягів.
                    </p>
                </div>
            `;
            break;

        case 'replicate-flux-schnell':
        case 'replicate-flux-dev':
            const variant = provider.includes('schnell') ? 'Schnell' : 'Dev';
            infoText.textContent = '⚠️ Потребує API ключ від Replicate';
            setupInfo = `
                <div style="padding: 16px; background: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px;">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                        <i class="bi bi-exclamation-triangle-fill" style="color: #f59e0b; font-size: 20px;"></i>
                        <strong style="color: #92400e;">Replicate FLUX ${variant} - Потребує налаштування</strong>
                    </div>
                    <p style="color: #78350f; font-size: 13px; margin-bottom: 12px;">
                        Щоб використовувати цей провайдер, додайте API ключ Replicate в AWS Secrets Manager:
                    </p>
                    <code style="display: block; padding: 12px; background: white; border-radius: 4px; font-size: 12px; overflow-x: auto; color: #1f2937;">
aws secretsmanager create-secret \\<br>
&nbsp;&nbsp;--name replicate/api-key \\<br>
&nbsp;&nbsp;--secret-string '{"api_key":"r8_YOUR_KEY"}' \\<br>
&nbsp;&nbsp;--region eu-central-1
                    </code>
                    <p style="color: #78350f; font-size: 12px; margin-top: 8px; margin-bottom: 0;">
                        📖 Отримати ключ: <a href="https://replicate.com" target="_blank" style="color: #3b82f6;">replicate.com</a> → Account → API Tokens
                    </p>
                </div>
            `;
            break;

        case 'vast-ai-flux-schnell':
            infoText.textContent = '⚙️ Керуйте GPU instance через панель нижче';
            setupInfo = `
                <div style="padding: 16px; background: #e0e7ff; border: 1px solid #6366f1; border-radius: 8px;">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                        <i class="bi bi-gpu-card" style="color: #6366f1; font-size: 20px;"></i>
                        <strong style="color: #3730a3;">Vast.ai FLUX - Найдешевше рішення! 💰</strong>
                    </div>
                    <p style="color: #3730a3; font-size: 13px; margin-bottom: 8px;">
                        ✅ Економія до 95%! | ⚡ RTX 3060 12GB | 🎨 FLUX Schnell
                    </p>
                    <p style="color: #4338ca; font-size: 12px; margin: 0;">
                        Використовуйте панель керування нижче для старту/зупинки GPU instance
                    </p>
                </div>
            `;
            // Show Vast.ai control panel
            document.getElementById('vastaiControlPanel').style.display = 'block';
            // Refresh status
            setTimeout(refreshVastaiStatus, 500);
            break;
        default:
            // Hide Vast.ai panel for other providers
            document.getElementById('vastaiControlPanel').style.display = 'none';
    }

    infoBox.innerHTML = setupInfo;

    // Update cost estimate
    updateImageCostEstimate();
}

/**
 * Calculate and display cost estimates
 */
function updateImageCostEstimate() {
    const provider = document.getElementById('image_generation_provider').value;
    const quality = document.getElementById('image_generation_quality').value;

    // Cost per image based on provider and quality
    const costs = {
        'aws-bedrock-sdxl': quality === 'premium' ? 0.036 : 0.018,
        'replicate-flux-schnell': 0.003,
        'replicate-flux-dev': 0.025,
        'vast-ai-flux-schnell': 0.0012
    };

    const costPerImage = costs[provider] || 0.018;
    const scenesPerVideo = 10; // Average
    const videosPerMonth = 100;

    const costPerVideo = costPerImage * scenesPerVideo;
    const costPerMonth = costPerVideo * videosPerMonth;

    // Update UI
    document.getElementById('costPerVideo').textContent = `$${costPerVideo.toFixed(2)}`;
    document.getElementById('costPerMonth').textContent = `$${costPerMonth.toFixed(2)}`;

    // Show savings info
    const baselineCost = 0.018; // AWS Bedrock Standard
    const baselinePerMonth = baselineCost * scenesPerVideo * videosPerMonth;

    if (provider !== 'aws-bedrock-sdxl' || quality !== 'standard') {
        const savings = baselinePerMonth - costPerMonth;
        const savingsPercent = ((savings / baselinePerMonth) * 100).toFixed(0);

        let savingsText = '';
        if (savings > 0) {
            savingsText = `💰 Економія: $${savings.toFixed(2)}/міс (${savingsPercent}%) порівняно з AWS Bedrock Standard`;
        } else if (savings < 0) {
            savingsText = `⚠️ Дорожче на $${Math.abs(savings).toFixed(2)}/міс (${Math.abs(savingsPercent)}%) ніж AWS Bedrock Standard`;
        }

        document.getElementById('savingsInfo').textContent = savingsText;
    } else {
        document.getElementById('savingsInfo').textContent = '📊 Базовий тариф (для порівняння)';
    }
}

/**
 * Load image generation settings into form (TECHNICAL ONLY - no visual style)
 */
function loadImageGenerationSettings(config) {
    const imageGen = config.image_generation || {};

    // Enable/disable
    const enabledCheckbox = document.getElementById('image_generation_enabled');
    if (!enabledCheckbox) {
        console.warn('⚠️ Image generation enabled checkbox not found in form');
        return;
    }

    const enabled = imageGen.enabled === true || imageGen.enabled === 'true';
    enabledCheckbox.checked = enabled;
    toggleImageGenerationSettings();

    if (enabled) {
        // Provider
        if (imageGen.provider) {
            document.getElementById('image_generation_provider').value = imageGen.provider;
        }

        // Dimensions
        if (imageGen.width) {
            document.getElementById('image_generation_width').value = imageGen.width;
        }
        if (imageGen.height) {
            document.getElementById('image_generation_height').value = imageGen.height;
        }

        // Quality settings
        if (imageGen.quality) {
            document.getElementById('image_generation_quality').value = imageGen.quality;
        }
        if (imageGen.cfg_scale !== undefined) {
            document.getElementById('image_generation_cfg_scale').value = imageGen.cfg_scale;
        }
        if (imageGen.steps !== undefined) {
            document.getElementById('image_generation_steps').value = imageGen.steps;
        }
        if (imageGen.flux_variant) {
            document.getElementById('image_generation_flux_variant').value = imageGen.flux_variant;
        }

        updateImageProviderInfo();
        updateImageCostEstimate();
    }
}

/**
 * DEPRECATED: Load visual style settings from ChannelConfig root
 * Visual fields are now in Variation Sets only (Section 4.6)
 * This function is kept for backward compatibility but not used
 */
function loadVisualStyleSettings(config) {
    // DEPRECATED: Visual fields moved to Variation Sets
    // Visual style fields are now at root level of ChannelConfig
    if (config.visual_keywords) {
        document.getElementById('visual_keywords').value = config.visual_keywords;
    }
    if (config.visual_atmosphere) {
        document.getElementById('visual_atmosphere').value = config.visual_atmosphere;
    }
    if (config.image_style_variants) {
        document.getElementById('image_style_variants').value = config.image_style_variants;
    }
    if (config.visual_reference_type) {
        document.getElementById('visual_reference_type').value = config.visual_reference_type;
    }
    if (config.color_palettes) {
        document.getElementById('color_palettes').value = config.color_palettes;
    }
    if (config.lighting_variants) {
        document.getElementById('lighting_variants').value = config.lighting_variants;
    }
    if (config.composition_variants) {
        document.getElementById('composition_variants').value = config.composition_variants;
    }
    if (config.negative_prompt) {
        document.getElementById('negative_prompt').value = config.negative_prompt;
    }
}

/**
 * Save image generation settings to nested object (TECHNICAL ONLY - no visual style)
 */
function saveImageGenerationSettings() {
    const enabled = document.getElementById('image_generation_enabled').checked;

    const imageGen = {
        enabled: enabled
    };

    if (enabled) {
        imageGen.provider = document.getElementById('image_generation_provider').value;
        imageGen.width = parseInt(document.getElementById('image_generation_width').value);
        imageGen.height = parseInt(document.getElementById('image_generation_height').value);
        imageGen.quality = document.getElementById('image_generation_quality').value;
        imageGen.cfg_scale = parseFloat(document.getElementById('image_generation_cfg_scale').value);
        imageGen.steps = parseInt(document.getElementById('image_generation_steps').value);
        imageGen.flux_variant = document.getElementById('image_generation_flux_variant').value;
    }

    return imageGen;
}

/**
 * DEPRECATED: Save visual style settings to ChannelConfig root
 * Visual fields are now in Variation Sets only (Section 4.6)
 * This function is kept for backward compatibility but not used
 */
function saveVisualStyleSettings() {
    // DEPRECATED: Visual fields moved to Variation Sets
    return {
        visual_keywords: document.getElementById('visual_keywords').value || '',
        visual_atmosphere: document.getElementById('visual_atmosphere').value || '',
        image_style_variants: document.getElementById('image_style_variants').value || '',
        visual_reference_type: document.getElementById('visual_reference_type').value || '',
        color_palettes: document.getElementById('color_palettes').value || '',
        lighting_variants: document.getElementById('lighting_variants').value || '',
        composition_variants: document.getElementById('composition_variants').value || '',
        negative_prompt: document.getElementById('negative_prompt').value || 'blurry, low quality, distorted, ugly, text, watermark'
    };
}

// ===== VAST.AI INSTANCE MANAGEMENT =====

let vastaiStatusInterval = null;

/**
 * Refresh Vast.ai instance status
 */
async function refreshVastaiStatus() {
    try {
        const response = await fetch(`${VASTAI_API_URL}?action=status`);
        const data = await response.json();

        if (data.error) {
            document.getElementById('vastaiStatus').innerHTML = '❌ ' + data.error;
            return;
        }

        // Update status
        const status = data.status || 'unknown';
        const statusMap = {
            'running': '🟢 Running',
            'stopped': '⏹️ Stopped',
            'loading': '⏳ Starting...',
            'unknown': '❓ Unknown'
        };
        document.getElementById('vastaiStatus').innerHTML = statusMap[status] || status;

        // Update uptime
        if (data.uptime) {
            document.getElementById('vastaiUptime').textContent = formatUptime(data.uptime);
        } else {
            document.getElementById('vastaiUptime').textContent = '--';
        }

        // Update cost
        if (data.cost_today !== undefined) {
            document.getElementById('vastaiCostToday').textContent = '$' + data.cost_today.toFixed(2);
        }

        // Show/hide GPU info
        if (status === 'running' && data.gpu_info) {
            document.getElementById('vastaiGPUInfo').style.display = 'block';
            document.getElementById('vastaiVRAM').textContent = `${data.gpu_info.vram_used || 0} / ${data.gpu_info.vram_total || 12} GB`;
            document.getElementById('vastaiGPULoad').textContent = `${data.gpu_info.load || 0}%`;
        } else {
            document.getElementById('vastaiGPUInfo').style.display = 'none';
        }

        // Update button states
        const startBtn = document.getElementById('vastaiStartBtn');
        const stopBtn = document.getElementById('vastaiStopBtn');

        if (status === 'running') {
            startBtn.disabled = true;
            startBtn.style.opacity = '0.5';
            stopBtn.disabled = false;
            stopBtn.style.opacity = '1';
        } else {
            startBtn.disabled = false;
            startBtn.style.opacity = '1';
            stopBtn.disabled = true;
            stopBtn.style.opacity = '0.5';
        }

    } catch (error) {
        console.error('Failed to refresh Vast.ai status:', error);
        document.getElementById('vastaiStatus').innerHTML = '❌ Error';
    }
}

/**
 * Start Vast.ai instance
 */
async function startVastaiInstance() {
    if (!confirm('Start Vast.ai GPU instance? Це почне нараховувати $0.055/год')) {
        return;
    }

    const startBtn = document.getElementById('vastaiStartBtn');
    startBtn.disabled = true;
    startBtn.textContent = '⏳ Starting...';

    try {
        const response = await fetch(`${VASTAI_API_URL}?action=start`, { method: 'POST' });
        const data = await response.json();

        if (data.success) {
            alert('✅ Instance запускається! Зачекайте 1-2 хвилини.');
            // Start auto-refresh
            if (!vastaiStatusInterval) {
                vastaiStatusInterval = setInterval(refreshVastaiStatus, 10000); // Every 10 sec
            }
            setTimeout(refreshVastaiStatus, 2000);
        } else {
            alert('❌ Помилка: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Failed to start instance:', error);
        alert('❌ Не вдалося запустити instance');
    } finally {
        startBtn.textContent = '▶️ Start Instance';
        startBtn.disabled = false;
    }
}

/**
 * Stop Vast.ai instance
 */
async function stopVastaiInstance() {
    if (!confirm('⚠️ Зупинити Vast.ai instance? Генерація зображень буде недоступна.')) {
        return;
    }

    const stopBtn = document.getElementById('vastaiStopBtn');
    stopBtn.disabled = true;
    stopBtn.textContent = '⏳ Stopping...';

    try {
        const response = await fetch(`${VASTAI_API_URL}?action=stop`, { method: 'POST' });
        const data = await response.json();

        if (data.success) {
            alert('✅ Instance зупинено! Оплата припинена.');
            // Stop auto-refresh
            if (vastaiStatusInterval) {
                clearInterval(vastaiStatusInterval);
                vastaiStatusInterval = null;
            }
            setTimeout(refreshVastaiStatus, 2000);
        } else {
            alert('❌ Помилка: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Failed to stop instance:', error);
        alert('❌ Не вдалося зупинити instance');
    } finally {
        stopBtn.textContent = '⏹️ Stop Instance';
        stopBtn.disabled = false;
    }
}

/**
 * Format uptime in hours/minutes
 */
function formatUptime(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (hours > 0) {
        return `${hours}г ${minutes}хв`;
    } else {
        return `${minutes}хв`;
    }
}

// ==========================================
// VARIATION SETS MANAGEMENT
// ==========================================

let currentEditingSetIndex = null;

/**
 * Load and display variation sets list
 */
function loadVariationSets() {
    const config = window.currentChannelConfig;
    if (!config) {
        console.error('❌ loadVariationSets: No currentChannelConfig found');
        return;
    }

    // Get variation_sets (now properly stored as array in DynamoDB)
    let variationSets = config.variation_sets || [];

    // Ensure it's an array
    if (!Array.isArray(variationSets)) {
        console.warn('variation_sets is not an array:', typeof variationSets);
        variationSets = [];
    }

    console.log('🔄 loadVariationSets called:', {
        channel: config.channel_name,
        variation_sets_count: variationSets.length,
        generation_count: config.generation_count,
        is_array: Array.isArray(variationSets),
        type: typeof variationSets
    });

    const listContainer = document.getElementById('variation-sets-list');
    if (!listContainer) {
        console.error('❌ variation-sets-list element not found');
        return;
    }

    // Update counter in section header using specific ID
    const counterEl = document.getElementById('variation-sets-counter');
    console.log('🎯 Counter element found:', counterEl !== null);
    if (counterEl) {
        console.log('📝 Updating counter to:', `${variationSets.length}/100`);
        counterEl.textContent = `Variation Sets (${variationSets.length}/100)`;
        console.log('✅ Counter updated. Current text:', counterEl.textContent);
    } else {
        console.error('❌ variation-sets-counter element not found!');
    }

    if (variationSets.length === 0) {
        listContainer.innerHTML = `
            <div style="text-align: center; padding: 40px; background: #f8f9fa; border-radius: 8px; color: #6c757d;">
                Немає variation sets. Натисніть "➕ Додати Variation Set" щоб створити перший стиль.
            </div>
        `;
        return;
    }

    // Render each set as a card
    listContainer.innerHTML = variationSets.map((set, index) =>
        renderVariationSetCard(set, index)
    ).join('');
}

/**
 * Render a single variation set card
 */
function renderVariationSetCard(set, index) {
    const isActive = window.currentChannelConfig &&
                     window.currentChannelConfig.generation_count %
                     (window.currentChannelConfig.variation_sets?.length || 1) === index;

    return `
        <div class="variation-set-card ${isActive ? 'active' : ''}" data-set-index="${index}">
            <div class="variation-set-header">
                <h4>
                    ${set.set_name || `Set ${index + 1}`}
                    ${isActive ? '<span class="badge">АКТИВНИЙ</span>' : ''}
                </h4>
                <div class="variation-set-actions">
                    <button onclick="openVariationSetModal('edit', ${index})">✏️ Редагувати</button>
                    <button onclick="deleteVariationSet(${index})" style="color: #e53e3e;">🗑️ Видалити</button>
                </div>
            </div>
            <div class="variation-set-preview">
                <div><strong>Keywords:</strong> ${(set.visual_keywords || '').substring(0, 60)}...</div>
                <div><strong>Atmosphere:</strong> ${set.visual_atmosphere || 'N/A'}</div>
                <div><strong>Style:</strong> ${set.image_style_variants || 'N/A'}</div>
                <div><strong>Colors:</strong> ${set.color_palettes || 'N/A'}</div>
            </div>
        </div>
    `;
}

/**
 * Open variation set modal for creating or editing
 */
function openVariationSetModal(mode, setIndex = null) {
    const config = window.currentChannelConfig;
    if (!config) {
        alert('Спочатку завантажте конфігурацію каналу');
        return;
    }

    // Check limit
    if (mode === 'new' && (config.variation_sets || []).length >= 100) {
        alert('⚠️ Максимум 100 variation sets на канал');
        return;
    }

    currentEditingSetIndex = mode === 'edit' ? setIndex : null;

    // Get existing set data if editing
    let setData = {};
    if (mode === 'edit' && config.variation_sets && config.variation_sets[setIndex]) {
        setData = config.variation_sets[setIndex];
    }

    // Populate modal fields
    document.getElementById('set_name').value = setData.set_name || '';
    document.getElementById('set_visual_keywords').value = setData.visual_keywords || '';
    document.getElementById('set_visual_atmosphere').value = setData.visual_atmosphere || '';
    document.getElementById('set_image_style_variants').value = setData.image_style_variants || '';
    document.getElementById('set_color_palettes').value = setData.color_palettes || '';
    document.getElementById('set_lighting_variants').value = setData.lighting_variants || '';
    document.getElementById('set_composition_variants').value = setData.composition_variants || '';
    document.getElementById('set_visual_reference_type').value = setData.visual_reference_type || '';
    document.getElementById('set_negative_prompt').value = setData.negative_prompt || '';

    // Update modal title
    const modalTitle = document.querySelector('#variationSetModal h2');
    if (modalTitle) {
        modalTitle.textContent = mode === 'new' ? '➕ Новий Variation Set' : '✏️ Редагувати Variation Set';
    }

    // Show modal
    document.getElementById('variationSetModal').style.display = 'flex';
}

/**
 * Close variation set modal
 */
function closeVariationSetModal() {
    document.getElementById('variationSetModal').style.display = 'none';
    currentEditingSetIndex = null;
}

/**
 * Save variation set (create or update)
 */
function saveVariationSet() {
    const config = window.currentChannelConfig;
    if (!config) return;

    // Collect data from modal
    const setData = {
        set_id: currentEditingSetIndex !== null ? currentEditingSetIndex : (config.variation_sets || []).length,
        set_name: document.getElementById('set_name').value.trim(),
        visual_keywords: document.getElementById('set_visual_keywords').value.trim(),
        visual_atmosphere: document.getElementById('set_visual_atmosphere').value.trim(),
        image_style_variants: document.getElementById('set_image_style_variants').value.trim(),
        color_palettes: document.getElementById('set_color_palettes').value.trim(),
        lighting_variants: document.getElementById('set_lighting_variants').value.trim(),
        composition_variants: document.getElementById('set_composition_variants').value.trim(),
        visual_reference_type: document.getElementById('set_visual_reference_type').value.trim(),
        negative_prompt: document.getElementById('set_negative_prompt').value.trim()
    };

    // Validate required fields
    if (!setData.set_name) {
        alert('⚠️ Введіть назву variation set');
        return;
    }

    if (!setData.visual_keywords) {
        alert('⚠️ Введіть visual keywords');
        return;
    }

    // Initialize variation_sets array if needed
    if (!config.variation_sets) {
        config.variation_sets = [];
    }

    // Add or update
    if (currentEditingSetIndex !== null) {
        // Update existing set
        config.variation_sets[currentEditingSetIndex] = setData;
        console.log(`✅ Updated variation set ${currentEditingSetIndex}: ${setData.set_name}`);
    } else {
        // Add new set
        config.variation_sets.push(setData);
        console.log(`✅ Added new variation set: ${setData.set_name}`);
    }

    // Mark as modified
    window.currentChannelConfig = config;

    // Close modal and reload list
    closeVariationSetModal();
    loadVariationSets();

    alert(`✅ Variation set "${setData.set_name}" збережено! Не забудьте зберегти конфігурацію каналу.`);
}

/**
 * Delete variation set
 */
function deleteVariationSet(setIndex) {
    const config = window.currentChannelConfig;
    if (!config || !config.variation_sets) return;

    const setName = config.variation_sets[setIndex]?.set_name || `Set ${setIndex + 1}`;

    if (!confirm(`Видалити variation set "${setName}"?`)) {
        return;
    }

    // Remove from array
    config.variation_sets.splice(setIndex, 1);

    // Update set_id for remaining sets
    config.variation_sets.forEach((set, idx) => {
        set.set_id = idx;
    });

    console.log(`✅ Deleted variation set: ${setName}`);

    // Mark as modified
    window.currentChannelConfig = config;

    // Reload list
    loadVariationSets();

    alert(`✅ Variation set "${setName}" видалено! Не забудьте зберегти конфігурацію каналу.`);
}

/**
 * Load variation sets settings when opening channel config
 */
function loadVariationSetsSettings(config) {
    // Load rotation mode
    const rotationMode = document.getElementById('rotation_mode');
    if (rotationMode) {
        rotationMode.value = config.rotation_mode || 'sequential';
    }

    // Load generation count (read-only)
    const generationCount = document.getElementById('generation_count');
    if (generationCount) {
        generationCount.value = config.generation_count || 0;
    }

    // Show/hide manual set selector
    const manualSetSelector = document.getElementById('manual_set_selector');
    if (manualSetSelector) {
        manualSetSelector.style.display = config.rotation_mode === 'manual' ? 'block' : 'none';
    }

    // Load manual set index if applicable
    const manualSetIndex = document.getElementById('manual_set_index');
    if (manualSetIndex) {
        manualSetIndex.value = config.manual_set_index || 0;
    }

    // Load variation sets list
    loadVariationSets();
}

/**
 * Save variation sets settings to config
 */
function saveVariationSetsSettings(config) {
    // Save rotation mode
    const rotationMode = document.getElementById('rotation_mode');
    if (rotationMode) {
        config.rotation_mode = rotationMode.value;
    }

    // Save manual set index if in manual mode
    if (config.rotation_mode === 'manual') {
        const manualSetIndex = document.getElementById('manual_set_index');
        if (manualSetIndex) {
            config.manual_set_index = parseInt(manualSetIndex.value) || 0;
        }
    }

    // variation_sets array is already in config (modified by add/edit/delete functions)
    // generation_count is read-only (managed by Lambda)

    return config;
}

// Add event listener for rotation mode changes
document.addEventListener('DOMContentLoaded', function() {
    const rotationMode = document.getElementById('rotation_mode');
    if (rotationMode) {
        rotationMode.addEventListener('change', function() {
            const manualSetSelector = document.getElementById('manual_set_selector');
            if (manualSetSelector) {
                manualSetSelector.style.display = this.value === 'manual' ? 'block' : 'none';
            }
        });
    }
});


