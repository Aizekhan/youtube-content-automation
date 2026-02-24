//  Unified Channels System JavaScript
// Об'єднана система управління каналами

// Import auth manager (loaded from auth.js)
let authManager;

// API Configuration
const API_BASE = 'https://n8n-creator.space';
const VASTAI_API_URL = 'https://xmstnomewqj2zlhrgkqxnnhkz40znusc.lambda-url.eu-central-1.on.aws';

// Lambda Function URLs (multi-tenant with CORS)
const CHANNELS_API = 'https://ywsop7xk36ir7r3a66fqcphdy40esadg.lambda-url.eu-central-1.on.aws';

// Mови що підтримує Qwen3-TTS (source of truth — matches lang_map in content-audio-qwen3tts)
// code: ISO 639-1 код -> label: відображення -> tts_name: назва для Qwen3 API
const QWEN3_LANGUAGES = [
    { code: 'en', label: 'English', tts_name: 'English' },
    { code: 'zh', label: 'Chinese (Mandarin)', tts_name: 'Chinese' },
    { code: 'ja', label: 'Japanese', tts_name: 'Japanese' },
    { code: 'ko', label: 'Korean', tts_name: 'Korean' },
    { code: 'fr', label: 'French', tts_name: 'French' },
    { code: 'de', label: 'German', tts_name: 'German' },
    { code: 'es', label: 'Spanish', tts_name: 'Spanish' },
    { code: 'it', label: 'Italian', tts_name: 'Italian' },
    { code: 'pt', label: 'Portuguese', tts_name: 'Portuguese' },
    { code: 'ru', label: 'Russian', tts_name: 'Russian' },
    { code: 'ar', label: 'Arabic', tts_name: 'Arabic' },
    { code: 'hi', label: 'Hindi', tts_name: 'Hindi' }
    ];

// Голоси Qwen3-TTS (source of truth — matches speaker normalization in content-audio-qwen3tts)
// Supported speakers: aiden, dylan, eric, ono_anna, ryan, serena, sohee, uncle_fu, vivian
const QWEN3_SPEAKERS = [
    { value: '',         label: '— ryan (за замовчуванням) —' },
    { value: 'ryan',     label: 'Ryan      — глибокий чоловічий' },
    { value: 'eric',     label: 'Eric      — авторитетний чоловічий' },
    { value: 'dylan',    label: 'Dylan     — нейтральний чоловічий' },
    { value: 'aiden',    label: 'Aiden     — молодий чоловічий' },
    { value: 'uncle_fu', label: 'Uncle Fu  — зрілий чоловічий' },
    { value: 'serena',   label: 'Serena    — тепла жіноча' },
    { value: 'vivian',   label: 'Vivian    — нейтральна жіноча' },
    { value: 'ono_anna', label: 'Ono Anna  — м\'яка жіноча' },
    { value: 'sohee',    label: 'Sohee     — молода жіноча' }
];

// Populate speaker dropdown from QWEN3_SPEAKERS
function populateSpeakerDropdown(selectEl, selectedValue) {
    if (!selectEl) return;
    selectEl.innerHTML = '';
    QWEN3_SPEAKERS.forEach(sp => {
        const opt = document.createElement('option');
        opt.value = sp.value;
        opt.textContent = sp.label;
        if (sp.value === selectedValue) opt.selected = true;
        selectEl.appendChild(opt);
    });
}

// Populate language dropdowns from QWEN3_LANGUAGES
function populateLanguageDropdown(selectEl, selectedCode) {
    if (!selectEl) return;
    selectEl.innerHTML = '';
    QWEN3_LANGUAGES.forEach(lang => {
        const opt = document.createElement('option');
        opt.value = lang.code;
        opt.textContent = lang.label + ' (' + lang.code + ')';
        if (lang.code === selectedCode) opt.selected = true;
        selectEl.appendChild(opt);
    });
}

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
    console.log(' Initializing Unified Channels System');

    // Initialize auth manager
    authManager = new AuthManager();

    // Check authentication
    try {
        await authManager.requireAuth();
        console.log(' User authenticated:', authManager.getUserId());
    } catch (error) {
        console.error(' Authentication failed:', error);
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

        console.log(` Loaded ${allChannelsData.length} total channels`);

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

    console.log(` Filter: ${filter} - Showing ${filteredChannels.length} of ${allChannelsData.length} channels`);

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
            showNotification(` Канал ${isActive ? 'активовано' : 'деактивовано'}`, 'success');

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
        showNotification(' Помилка: ' + error.message, 'danger');
        // Reload channels to revert the toggle
        setTimeout(() => loadChannels(), 500);
    }
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
        showNotification(' Канали оновлено', 'success');

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
        showNotification(' Помилка: ' + error.message, 'danger');
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

        console.log(' Loaded config:', config);

        document.getElementById('modalTitle').textContent = config.channel_name || config.channel_title || 'Редагування';

        // Populate form values
        populateForm(config);

        // Initialize Story Engine UI handlers
        initializeStoryEngineUI();

        // Note: loadImageGenerationSettings() removed - deprecated feature
        // Image generation now uses selected_image_template + visual guidance fields

        // Store config globally
        window.currentChannelConfig = config;
    } catch (error) {
        console.error('Error loading config:', error);
        showNotification(' Помилка завантаження', 'danger');
        closeModal();
    }
}

//  Generation Mode Toggle 
function setGenerationMode(value) {
    // Update hidden select
    const select = document.getElementById('factual_mode');
    if (select) select.value = value;

    // Update card visuals
    document.querySelectorAll('.mode-card').forEach(card => {
        card.classList.toggle('active', card.dataset.value === value);
    });
}


function populateForm(config) {
    // Populate language dropdown from QWEN3_LANGUAGES (dynamic, not hardcoded)
    populateLanguageDropdown(document.getElementById('language'), config.language || 'en');
    populateSpeakerDropdown(document.getElementById('tts_voice_speaker'), config.tts_voice_speaker || '');

    const fields = [
        'channel_id',
        // Basic Identity
        'channel_name', 'language', 'tts_voice_speaker', 'timezone', 'genre',
        // Content Identity
        'factual_mode',
        // Publishing Schedule
        'publish_times', 'publish_days', 'daily_upload_count',
        // Production Settings
        'video_duration_target', 'target_character_count', 'scene_count_target', 'max_tokens',
        // TTS Settings 'format',        'example_keywords_for_youtube', 'unique_variation_logic'
        // Story Engine - Manual Input Mode
        'manual_mode_enabled', 'manual_theme', 'manual_narrative',
        // Story Engine - Story Mode
        'story_mode',
        // Story Engine - A/B Testing (Sprint 3)
        'enrichment_ab_enabled', 'enrichment_ab_group',
        // Story Engine - Story DNA
        'world_type', 'tone', 'psychological_depth', 'plot_intensity',
        // Story Engine - Character Engine
        'character_mode', 'character_archetype', 'enable_internal_conflict', 'enable_secret', 'moral_dilemma_level',
        // Story Engine - Story Structure
        'story_structure_mode', 'story_structure_template',
        // Story Engine - Logic & Consistency
        'generate_plan_before_writing', 'auto_consistency_check', 'character_motivation_validation', 'no_cliches_mode', 'surprise_injection_level',
        // Story Engine v4.0 - Three Phase System
        'complexity_level', 'narrative_tone'
    ];
    
    fields.forEach(field => {
        const element = document.getElementById(field);
        if (!element) return;

        const configValue = config[field];
        const hasConfigValue = configValue !== undefined && configValue !== null && configValue !== '';

        // Special handling for template fields
        if (field.startsWith('selected_') && field.includes('_template')) {
            console.log(` Template field: ${field}`);
            console.log(`   Config value: ${configValue}`);
            console.log(`   Default template: ${element.dataset.defaultTemplateId}`);

            if (hasConfigValue) {
                // Check if option exists in select
                const optionExists = Array.from(element.options).some(opt => opt.value === configValue);

                if (optionExists) {
                    element.value = configValue;
                    console.log(`    Set to config value: ${configValue}`);
                } else {
                    console.log(`    Config value "${configValue}" not found in options, using default`);
                    if (element.dataset.defaultTemplateId) {
                        element.value = element.dataset.defaultTemplateId;
                        console.log(`    Set to default: ${element.dataset.defaultTemplateId}`);
                    }
                }
            } else if (element.dataset.defaultTemplateId) {
                element.value = element.dataset.defaultTemplateId;
                console.log(`    Set to default: ${element.dataset.defaultTemplateId}`);
            } else {
                console.log(`    No value set - no config and no default found`);
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

    // Sync generation mode cards with saved factual_mode
    setGenerationMode(config.factual_mode || 'fictional');

    // Load Story Engine v4.0 fields
    // complexity_level slider
    if (config.complexity_level !== undefined) {
        const complexitySlider = document.getElementById('complexity_level');
        if (complexitySlider) {
            complexitySlider.value = config.complexity_level;
            updateComplexityHint(config.complexity_level);
        }
    }

    // narrative_tone dropdown (already handled by fields loop above)

    // archetype_pool checkboxes
    if (config.archetype_pool && Array.isArray(config.archetype_pool)) {
        // Uncheck all first
        document.querySelectorAll('.archetype-checkbox').forEach(cb => cb.checked = false);

        // Check the ones from config
        config.archetype_pool.forEach(archetype => {
            const checkbox = document.querySelector(`.archetype-checkbox[value="${archetype}"]`);
            if (checkbox) checkbox.checked = true;
        });
    }
}

// REMOVED: initializeTemplateSelects() - Templates system deleted

/**
 * Load Image Generation Templates for channel config dropdown
 */
async function loadImageGenerationTemplates() {
    const PROMPTS_API = 'https://djpb4ue6wv2ohfjey32lfnhcre0zppqd.lambda-url.eu-central-1.on.aws';
    const selectElement = document.getElementById('image_generation_template_id');

    if (!selectElement) {
        console.warn(' Image generation template select not found');
        return;
    }

    try {
        const response = await fetch(`${PROMPTS_API}?type=image`);
        const result = await response.json();

        if (!result.success) {
            console.error(' Failed to load image templates:', result.error);
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
            const defaultLabel = template.is_default ? '  [Default]' : '';

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

        console.log(` Loaded ${activeTemplates.length} image generation templates`);
    } catch (error) {
        console.error(' Failed to load image templates:', error);
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
        showNotification(' Max Tokens не може бути більше 16000 (GPT-4o ліміт: 16384)', 'danger');
        return;
    }

    if (targetCharCount > 16000) {
        showNotification(' Цільова к-ть символів не може бути більше 16000', 'danger');
        return;
    }

    const fields = Array.from(form.querySelectorAll('input, textarea, select'));
    fields.forEach(field => {
        if (field.id) {
            // Skip archetype checkboxes - will be handled separately
            if (field.classList.contains('archetype-checkbox')) {
                return;
            }

            // Handle checkboxes specially
            if (field.type === 'checkbox') {
                formData.append(field.id, field.checked ? 'true' : 'false');
            } else {
                formData.append(field.id, field.value);
            }

            // Log template fields
            if (field.id.startsWith('selected_') && field.id.includes('_template')) {
                console.log(` Saving ${field.id}: ${field.value}`);
            }
        }
    });

    // Save Story Engine v4.0 fields
    // complexity_level (already handled by fields loop)
    // narrative_tone (already handled by fields loop)

    // archetype_pool - collect checked archetype checkboxes into JSON array
    const archetypePool = Array.from(document.querySelectorAll('.archetype-checkbox:checked'))
        .map(cb => cb.value);
    formData.append('archetype_pool', JSON.stringify(archetypePool));
    console.log(` Saving archetype_pool: ${JSON.stringify(archetypePool)}`);

    try {
        const response = await fetch('/api/update-channel-config.php', {
            method: 'POST',
            headers: { 'Authorization': 'Basic ' + btoa('admin:FHrifd45') },
            body: formData
        });
        const result = await response.json();
        
        if (result.success) {
            showNotification(' Конфіг збережено!', 'success');

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
        showNotification(' Помилка збереження', 'danger');
    }
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
    const setupInfoBox = document.getElementById('providerSetupInfo');
    const infoText = document.querySelector('#imageGenerationSettings .settings-info-text');
    let setupInfo = '';

    if (provider === 'ec2-zimage') {
        infoText.textContent = 'Z-Image-Turbo - Fast and efficient';
        setupInfo = `
            <div style="padding: 16px; background: #dcfce7; border: 1px solid #16a34a; border-radius: 8px;">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                    <i class="bi bi-lightning-charge" style="color: #16a34a; font-size: 20px;"></i>
                    <strong style="color: #166534;">EC2 Z-Image-Turbo</strong>
                </div>
                <p style="color: #166534; font-size: 13px; margin-bottom: 8px;">
                    Fast image generation (~5s per image) | g5.xlarge GPU
                </p>
                <p style="color: #15803d; font-size: 12px; margin: 0;">
                    Managed automatically by Step Functions
                </p>
            </div>
        `;
    } else {
        infoText.textContent = 'Unknown provider - using ec2-zimage';
        setupInfo = '<p style="color: #dc2626;">Unknown provider. Please select ec2-zimage.</p>';
    }

    // Update setup info box
    if (setupInfoBox) {
        setupInfoBox.innerHTML = setupInfo;
    }

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
            savingsText = ` Економія: $${savings.toFixed(2)}/міс (${savingsPercent}%) порівняно з AWS Bedrock Standard`;
        } else if (savings < 0) {
            savingsText = ` Дорожче на $${Math.abs(savings).toFixed(2)}/міс (${Math.abs(savingsPercent)}%) ніж AWS Bedrock Standard`;
        }

        document.getElementById('savingsInfo').textContent = savingsText;
    } else {
        document.getElementById('savingsInfo').textContent = ' Базовий тариф (для порівняння)';
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
        console.warn(' Image generation enabled checkbox not found in form');
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
            document.getElementById('vastaiStatus').innerHTML = ' ' + data.error;
            return;
        }

        // Update status
        const status = data.status || 'unknown';
        const statusMap = {
            'running': ' Running',
            'stopped': '⏹ Stopped',
            'loading': '⏳ Starting...',
            'unknown': ' Unknown'
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
        document.getElementById('vastaiStatus').innerHTML = ' Error';
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
            alert(' Instance запускається! Зачекайте 1-2 хвилини.');
            // Start auto-refresh
            if (!vastaiStatusInterval) {
                vastaiStatusInterval = setInterval(refreshVastaiStatus, 10000); // Every 10 sec
            }
            setTimeout(refreshVastaiStatus, 2000);
        } else {
            alert(' Помилка: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Failed to start instance:', error);
        alert(' Не вдалося запустити instance');
    } finally {
        startBtn.textContent = ' Start Instance';
        startBtn.disabled = false;
    }
}

/**
 * Stop Vast.ai instance
 */
async function stopVastaiInstance() {
    if (!confirm(' Зупинити Vast.ai instance? Генерація зображень буде недоступна.')) {
        return;
    }

    const stopBtn = document.getElementById('vastaiStopBtn');
    stopBtn.disabled = true;
    stopBtn.textContent = '⏳ Stopping...';

    try {
        const response = await fetch(`${VASTAI_API_URL}?action=stop`, { method: 'POST' });
        const data = await response.json();

        if (data.success) {
            alert(' Instance зупинено! Оплата припинена.');
            // Stop auto-refresh
            if (vastaiStatusInterval) {
                clearInterval(vastaiStatusInterval);
                vastaiStatusInterval = null;
            }
            setTimeout(refreshVastaiStatus, 2000);
        } else {
            alert(' Помилка: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Failed to stop instance:', error);
        alert(' Не вдалося зупинити instance');
    } finally {
        stopBtn.textContent = '⏹ Stop Instance';
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

// REMOVED: Variation Sets Management (Templates system deleted)
// See CLEANUP_STATUS_CHECKPOINT.md for details

// ============================================================================
// STORY ENGINE UI HANDLERS
// ============================================================================

/**
 * Set Story Mode (Fiction / Real Events / Hybrid)
 */
function setStoryMode(mode) {
    // Update hidden select
    const selectEl = document.getElementById('story_mode');
    if (selectEl) {
        selectEl.value = mode;
    }

    // Update visual cards
    const cards = document.querySelectorAll('.mode-card');
    cards.forEach(card => {
        if (card.dataset.value === mode) {
            card.style.border = '2px solid #667eea';
            card.style.background = '#f0f4ff';
        } else {
            card.style.border = '2px solid #e0e0e0';
            card.style.background = 'white';
        }
    });
}

/**
 * Update slider value display
 */
function updateSliderValue(slider, valueId) {
    const valueDisplay = document.getElementById(valueId);
    if (valueDisplay) {
        valueDisplay.textContent = slider.value;
    }
}

/**
 * Generate empty narrative template
 */
function generateManualNarrativeTemplate() {
    const template = {
        "story_title": "Your Story Title Here",
        "scenes": [
            {
                "scene_number": 1,
                "scene_title": "Scene Title",
                "scene_narration": "Narration text for this scene...",
                "image_prompt": "Detailed image generation prompt...",
                "negative_prompt": "blurry, low quality, distorted",
                "music_track": "optional_music.mp3",
                "sfx_cues": ["optional_sound1.mp3"],
                "timing_estimates": [0, 5]
            }
        ],
        "metadata": {
            "total_scenes": 1,
            "estimated_duration_seconds": 60
        }
    };

    const textarea = document.getElementById('manual_narrative');
    if (textarea) {
        textarea.value = JSON.stringify(template, null, 2);
    }
}

/**
 * Validate and preview manual narrative JSON
 */
function validateManualNarrative() {
    const textarea = document.getElementById('manual_narrative');
    const previewDiv = document.getElementById('manual-narrative-preview');

    if (!textarea || !previewDiv) return;

    try {
        const narrative = JSON.parse(textarea.value);

        // Validate structure
        if (!narrative.story_title) {
            throw new Error('Missing story_title');
        }
        if (!narrative.scenes || !Array.isArray(narrative.scenes)) {
            throw new Error('Missing or invalid scenes array');
        }
        if (narrative.scenes.length === 0) {
            throw new Error('Scenes array is empty');
        }

        // Validate each scene
        narrative.scenes.forEach((scene, index) => {
            if (!scene.scene_number) throw new Error(`Scene ${index + 1}: missing scene_number`);
            if (!scene.scene_title) throw new Error(`Scene ${index + 1}: missing scene_title`);
            if (!scene.scene_narration) throw new Error(`Scene ${index + 1}: missing scene_narration`);
            if (!scene.image_prompt) throw new Error(`Scene ${index + 1}: missing image_prompt`);
        });

        // Generate preview HTML
        let previewHTML = `
            <div style="border-left: 4px solid #48bb78; padding-left: 12px; margin-bottom: 15px;">
                <strong style="color: #48bb78;">✓ Valid JSON</strong>
            </div>
            <div style="margin-bottom: 12px;">
                <strong>Title:</strong> ${narrative.story_title}
            </div>
            <div style="margin-bottom: 12px;">
                <strong>Scenes:</strong> ${narrative.scenes.length}
            </div>
            <div style="border-top: 1px solid #e0e0e0; padding-top: 12px;">
        `;

        narrative.scenes.forEach(scene => {
            previewHTML += `
                <div style="margin-bottom: 10px; padding: 8px; background: white; border-radius: 4px; border: 1px solid #e0e0e0;">
                    <strong>Scene ${scene.scene_number}:</strong> ${scene.scene_title}<br>
                    <span style="font-size: 12px; color: #718096;">
                        ${scene.scene_narration.substring(0, 80)}${scene.scene_narration.length > 80 ? '...' : ''}
                    </span>
                </div>
            `;
        });

        previewHTML += '</div>';
        previewDiv.innerHTML = previewHTML;

        showNotification('✓ Valid narrative JSON', 'success');

    } catch (error) {
        previewDiv.innerHTML = `
            <div style="border-left: 4px solid #f56565; padding-left: 12px;">
                <strong style="color: #f56565;">✗ Invalid JSON</strong><br>
                <span style="font-size: 13px; color: #718096;">${error.message}</span>
            </div>
        `;
        showNotification('Invalid JSON: ' + error.message, 'danger');
    }
}

/**
 * Initialize Story Engine UI event listeners
 */
function initializeStoryEngineUI() {
    // Manual Mode checkbox - show/hide manual input fields
    const manualModeCheckbox = document.getElementById('manual_mode_enabled');
    const manualInputFields = document.getElementById('manual-input-fields');

    if (manualModeCheckbox && manualInputFields) {
        manualModeCheckbox.addEventListener('change', function() {
            manualInputFields.style.display = this.checked ? 'block' : 'none';
        });

        // Initialize visibility based on current state
        manualInputFields.style.display = manualModeCheckbox.checked ? 'block' : 'none';
    }

    // Initialize Story Mode cards
    const storyModeSelect = document.getElementById('story_mode');
    if (storyModeSelect && storyModeSelect.value) {
        setStoryMode(storyModeSelect.value);
    }

    // Initialize slider values
    const sliders = [
        { sliderId: 'psychological_depth', valueId: 'psychological_depth_value' },
        { sliderId: 'plot_intensity', valueId: 'plot_intensity_value' },
        { sliderId: 'moral_dilemma_level', valueId: 'moral_dilemma_level_value' },
        { sliderId: 'surprise_injection_level', valueId: 'surprise_injection_level_value' }
    ];

    sliders.forEach(({ sliderId, valueId }) => {
        const slider = document.getElementById(sliderId);
        const valueDisplay = document.getElementById(valueId);
        if (slider && valueDisplay) {
            valueDisplay.textContent = slider.value;
        }
    });
}


