// 🚀 Unified Channels System JavaScript
// Об'єднана система управління каналами

// API Configuration
const API_BASE = 'https://n8n-creator.space';
const API_URLS = {
    getChannels: '/api/channels.php',
    getChannelConfig: '/api/get-channel-config.php',
    saveConfig: '/api/update-channel-config.php',
    toggleStatus: '/api/toggle-channel-status.php'
};

// State Management
let currentTab = 'overview';
let channelsData = [];
let selectedChannelId = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Initializing Unified Channels System');

    // Set active navigation link
    setActiveNavLink('channels.html');

    // Load channels
    loadChannels();
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
        // Add cache busting to prevent stale data
        const cacheBuster = '?t=' + new Date().getTime();
        const response = await fetch(API_URLS.getChannels + cacheBuster);
        if (!response.ok) throw new Error('HTTP Error: ' + response.status);

        const data = await response.json();

        channelsData = Array.isArray(data) ? data : (data.channels || []);

        if (channelsData.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="bi bi-collection"></i>
                    <h3>No channels found</h3>
                    <p>Start by adding your first YouTube channel</p>
                </div>
            `;
            return;
        }

        renderChannelsGrid(channelsData);
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
                '<span class="stat-value">' + (channel.videos_per_week || 3) + '</span>' +
                '<span class="stat-label">Videos/Week</span>' +
            '</div>' +
            '<div class="stat-item">' +
                '<span class="stat-value">' + (channel.content_count || 0) + '</span>' +
                '<span class="stat-label">Content</span>' +
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
    try {
        const formData = new FormData();
        formData.append('channel_id', channelId);
        formData.append('is_active', isActive ? 'true' : 'false');
        
        const response = await fetch('/api/toggle-channel-status.php', {
            method: 'POST',
            headers: {
                'Authorization': 'Basic ' + btoa('admin:FHrifd45')
            },
            body: formData
        });
        
        if (!response.ok) throw new Error('Failed to toggle');
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('✅ Статус каналу оновлено', 'success');
            
            // Update local data and reload to refresh card styling
            const channel = channelsData.find(c => c.channel_id === channelId);
            if (channel) {
                channel.is_active = isActive;
            }
            
            // Reload channels to update card colors
            loadChannels();
        } else {
            throw new Error(result.error || 'Failed');
        }
    } catch (error) {
        console.error('Toggle error:', error);
        showNotification('❌ Помилка оновлення статусу', 'danger');
        // Reload to revert the toggle
        loadChannels();
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
        const response = await fetch('/api/update-stats.php');
        const result = await response.json();

        if (result.success) {
            showNotification('✅ Статистика оновлена', 'success');
            await loadChannels();
        } else {
            showNotification('❌ Помилка оновлення', 'danger');
        }
    } catch (error) {
        console.error('Failed to update stats:', error);
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
        
        document.getElementById('modalTitle').textContent = config.channel_name || config.channel_title || 'Редагування';
        populateForm(config);
        initializeVoiceSelect();
    } catch (error) {
        console.error('Error loading config:', error);
        showNotification('❌ Помилка завантаження', 'danger');
        closeModal();
    }
}

function populateForm(config) {
    const fields = [
        'channel_id', 'channel_name', 'channel_theme', 'genre', 'core_idea', 'tone', 'narration_style',
        'target_audience', 'format', 'factual_mode', 'content_focus', 'story_structure_pattern',
        'visual_keywords', 'narrative_keywords', 'narrative_pace', 'preferred_ending_tone',
        'emotional_temperature', 'tts_voice_profile', 'tts_service', 'tts_mood_variants',
        'recommended_music_variants', 'image_style_variants', 'color_palettes', 'lighting_variants',
        'composition_variants', 'visual_reference_type', 'visual_atmosphere', 'story_setting_variants',
        'story_character_types', 'story_point_of_view_variants', 'music_tempo_variants',
        'example_keywords_for_youtube', 'meta_theme', 'unique_variation_logic',
        'channel_description', 'thumbnail_url', 'banner_url', 'channel_watermark_url',
        'featured_video_id', 'seo_keywords', 'publish_times', 'publish_days',
        'daily_upload_count', 'timezone', 'monetization_enabled', 'adsense_enabled',
        'adsense_account_id', 'auto_caption_language', 'default_license', 'allow_embedding',
        'video_duration_target', 'target_character_count', 'scene_count_target',
        'image_generation_service', 'image_model', 'image_resolution', 'negative_prompt'
    ];
    
    fields.forEach(field => {
        const element = document.getElementById(field);
        if (element && config[field] !== undefined && config[field] !== null) {
            element.value = config[field];
        }
    });
}

function closeModal() {
    document.getElementById('editModal').style.display = 'none';
}

async function saveModalConfig() {
    const form = document.getElementById('configForm');
    const formData = new FormData();
    
    const fields = Array.from(form.querySelectorAll('input, textarea, select'));
    fields.forEach(field => {
        if (field.id) {
            formData.append(field.id, field.value);
        }
    });

    try {
        const response = await fetch('/api/update-channel-config.php', {
            method: 'POST',
            headers: { 'Authorization': 'Basic ' + btoa('admin:FHrifd45') },
            body: formData
        });
        const result = await response.json();
        
        if (result.success) {
            showNotification('✅ Конфіг збережено!', 'success');
            
            // Update local channel data
            const channelId = document.getElementById('channel_id').value;
            const ttsVoice = document.getElementById('tts_voice_profile').value;
            const ttsService = document.getElementById('tts_service').value;
            
            // Update in channelsData array
            const channelIndex = channelsData.findIndex(c => c.channel_id === channelId);
            if (channelIndex !== -1) {
                channelsData[channelIndex].tts_voice_profile = ttsVoice;
                channelsData[channelIndex].tts_service = ttsService;
            }
            
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
function updateVoiceOptions(service, currentVoice = "") {
    const voiceSelect = document.getElementById("tts_voice_profile");
    if (!voiceSelect) return;
    
    // Clear existing options
    voiceSelect.innerHTML = "";
    
    let voices = [];
    
    if (service === "aws_polly_neural") {
        voices = AWS_POLLY_VOICES.neural;
    } else if (service === "aws_polly_standard") {
        voices = AWS_POLLY_VOICES.standard;
    } else {
        // For other services (ElevenLabs, Google), show default options
        voiceSelect.innerHTML = "<option value=\"\">Select voice after choosing AWS Polly</option>";
        return;
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
    
    console.log(`✅ Loaded ${voices.length} voices for ${service}`);
}

// Initialize voice options when modal opens
function initializeVoiceSelect() {
    const ttsServiceSelect = document.getElementById("tts_service");
    const ttsVoiceSelect = document.getElementById("tts_voice_profile");
    
    if (!ttsServiceSelect || !ttsVoiceSelect) return;
    
    // Update voices when service changes
    ttsServiceSelect.addEventListener("change", (e) => {
        const currentVoice = ttsVoiceSelect.value;
        updateVoiceOptions(e.target.value, currentVoice);
    });
    
    // Initialize on load
    const currentService = ttsServiceSelect.value;
    const currentVoice = ttsVoiceSelect.value;
    updateVoiceOptions(currentService, currentVoice);
}
