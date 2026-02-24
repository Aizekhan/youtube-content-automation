/**
 * Series Manager - Real Data Integration
 * Loads and manages SeriesState from DynamoDB
 */

const LAMBDA_URL = 'https://4cjfvbsvr5ahk5wqxoiygbj3zi0ypdwk.lambda-url.eu-central-1.on.aws/';
const USER_ID = 'c334d862-4031-7097-4207-84856b59d3ed';

// Qwen3-TTS Voice Configuration
const QWEN3_VOICES = {
    'ryan': { gender: 'M', ageGroup: 'Young', description: 'Young male protagonist' },
    'eric': { gender: 'M', ageGroup: 'Middle', description: 'Adult male' },
    'dylan': { gender: 'M', ageGroup: 'Young', description: 'Teen/young male' },
    'aiden': { gender: 'M', ageGroup: 'Young', description: 'Child/young boy' },
    'uncle_fu': { gender: 'M', ageGroup: 'Old', description: 'Wise elder/mentor' },
    'serena': { gender: 'F', ageGroup: 'Young', description: 'Young female' },
    'vivian': { gender: 'F', ageGroup: 'Young', description: 'Young female (alt)' },
    'ono_anna': { gender: 'F', ageGroup: 'Middle', description: 'Adult female' },
    'sohee': { gender: 'F', ageGroup: 'Young', description: 'Teen/young female' }
};

let currentSeriesState = null;
let currentSeriesId = null;
let currentChannelId = null;

/**
 * Initialize on page load
 */
document.addEventListener('DOMContentLoaded', async () => {
    // Get series_id from URL
    const urlParams = new URLSearchParams(window.location.search);
    currentSeriesId = urlParams.get('series_id');
    currentChannelId = urlParams.get('channel_id');

    if (!currentSeriesId || !currentChannelId) {
        showError('Missing series_id or channel_id in URL');
        return;
    }

    await loadSeriesState();
    setupEventListeners();
});

/**
 * Load SeriesState from Lambda
 */
async function loadSeriesState() {
    showLoading(true);

    try {
        const response = await fetch(LAMBDA_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                operation: 'GET',
                user_id: USER_ID,
                channel_id: currentChannelId,
                series_id: currentSeriesId
            })
        });

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Failed to load series state');
        }

        currentSeriesState = data.series_state;
        renderAllTabs();

    } catch (error) {
        console.error('Error loading series state:', error);
        showError('Failed to load series data: ' + error.message);
    } finally {
        showLoading(false);
    }
}

/**
 * Render all tabs with real data
 */
function renderAllTabs() {
    if (!currentSeriesState) return;

    renderOverviewTab();
    renderCharactersTab();
    renderThreadsTab();
    renderEpisodesTab();
}

/**
 * Render Overview Tab
 */
function renderOverviewTab() {
    const state = currentSeriesState;

    // Update header
    document.querySelector('.dashboard-header h1').innerHTML = `
        <i class="bi bi-film"></i>
        ${state.series_title}
        <span class="series-badge">Season ${state.season || 1}</span>
    `;

    // Arc goal
    const arcGoal = state.season_arc?.arc_goal || 'No arc goal defined';
    document.getElementById('arc-goal-text').textContent = arcGoal;

    // Stats
    document.getElementById('total-episodes').textContent = state.season_arc?.total_episodes || 0;
    document.getElementById('characters-count').textContent = Object.keys(state.characters || {}).length;
    document.getElementById('open-threads').textContent = (state.open_threads || []).filter(t => t.status === 'open').length;
}

/**
 * Render Characters Tab
 */
function renderCharactersTab() {
    const characters = currentSeriesState.characters || {};
    const container = document.getElementById('characters-list');

    container.innerHTML = Object.entries(characters).map(([charId, char]) => `
        <div class="character-card" data-char-id="${charId}">
            <div class="character-header">
                <h4>${char.name}</h4>
                <div class="character-actions">
                    <button class="btn btn-sm btn-outline-primary" onclick="editCharacter('${charId}')">
                        <i class="bi bi-pencil"></i> Edit
                    </button>
                    ${char.visual_frozen ?
                        `<span class="badge bg-success"><i class="bi bi-lock"></i> Frozen</span>` :
                        `<button class="btn btn-sm btn-warning" onclick="freezeCharacter('${charId}')">
                            <i class="bi bi-lock-fill"></i> Freeze
                        </button>`
                    }
                </div>
            </div>
            <div class="character-details">
                <div class="detail-row">
                    <strong>Voice:</strong>
                    <span class="voice-badge">${char.voice_config?.speaker || 'Not set'}</span>
                    <small class="text-muted">${QWEN3_VOICES[char.voice_config?.speaker]?.description || ''}</small>
                </div>
                <div class="detail-row">
                    <strong>Description:</strong>
                    <span>${char.voice_config?.voice_description || 'No description'}</span>
                </div>
                <div class="detail-row">
                    <strong>Visual:</strong>
                    <span class="visual-description">${char.visual_frozen || char.visual_description || 'No visual description'}</span>
                </div>
                <div class="detail-row">
                    <strong>Introduced:</strong>
                    <span>Episode ${char.introduced_ep || 1}</span>
                </div>
            </div>
        </div>
    `).join('');

    // Add character button
    const addBtn = `
        <div class="text-center mt-4">
            <button class="btn btn-primary" onclick="showAddCharacterModal()">
                <i class="bi bi-plus-circle"></i> Add New Character
            </button>
        </div>
    `;
    container.innerHTML += addBtn;
}

/**
 * Render Threads Tab
 */
function renderThreadsTab() {
    const threads = currentSeriesState.open_threads || [];
    const container = document.getElementById('threads-list');

    const openThreads = threads.filter(t => t.status === 'open');
    const closedThreads = threads.filter(t => t.status === 'closed');

    container.innerHTML = `
        <h4>Open Threads (${openThreads.length})</h4>
        ${openThreads.map(thread => renderThread(thread, true)).join('')}

        <h4 class="mt-4">Closed Threads (${closedThreads.length})</h4>
        ${closedThreads.map(thread => renderThread(thread, false)).join('')}

        <div class="text-center mt-4">
            <button class="btn btn-primary" onclick="showAddThreadModal()">
                <i class="bi bi-plus-circle"></i> Add New Thread
            </button>
        </div>
    `;
}

function renderThread(thread, isOpen) {
    const priorityClass = thread.priority === 'HIGH' ? 'danger' : thread.priority === 'MEDIUM' ? 'warning' : 'secondary';

    return `
        <div class="thread-card ${isOpen ? '' : 'closed'}" data-thread-id="${thread.thread_id}">
            <div class="thread-header">
                <span class="badge bg-${priorityClass}">${thread.priority}</span>
                <h5>${thread.description}</h5>
                <div class="thread-actions">
                    ${isOpen ?
                        `<button class="btn btn-sm btn-success" onclick="closeThread('${thread.thread_id}')">
                            <i class="bi bi-check-circle"></i> Close
                        </button>` :
                        `<button class="btn btn-sm btn-secondary" onclick="reopenThread('${thread.thread_id}')">
                            <i class="bi bi-arrow-counterclockwise"></i> Reopen
                        </button>`
                    }
                </div>
            </div>
            ${thread.resolution ? `<div class="thread-resolution">${thread.resolution}</div>` : ''}
        </div>
    `;
}

/**
 * Render Episodes Tab
 */
function renderEpisodesTab() {
    const previous = currentSeriesState.previous_episodes || [];
    const container = document.getElementById('episodes-list');

    if (previous.length === 0) {
        container.innerHTML = '<p class="text-muted text-center">No episodes generated yet</p>';
        return;
    }

    container.innerHTML = previous.map(ep => `
        <div class="episode-card">
            <div class="episode-header">
                <h4>Episode ${ep.episode_number}</h4>
                <span class="badge bg-info">${ep.archetype_used || 'Unknown archetype'}</span>
            </div>
            <p class="episode-topic"><strong>${ep.topic_text}</strong></p>
            <p class="episode-summary">${ep.episode_summary || 'No summary available'}</p>
            <div class="episode-meta">
                <small class="text-muted">Generated: ${new Date(ep.generated_at).toLocaleDateString()}</small>
            </div>
        </div>
    `).join('');
}

/**
 * Edit Character Modal
 */
function editCharacter(charId) {
    const char = currentSeriesState.characters[charId];

    const modalHTML = `
        <div class="modal fade" id="editCharModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Edit Character: ${char.name}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <label class="form-label">Voice Speaker</label>
                            <select class="form-select" id="edit-voice-speaker">
                                ${Object.entries(QWEN3_VOICES).map(([voice, info]) => `
                                    <option value="${voice}" ${char.voice_config?.speaker === voice ? 'selected' : ''}>
                                        ${voice} - ${info.description} (${info.gender}, ${info.ageGroup})
                                    </option>
                                `).join('')}
                            </select>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Voice Description</label>
                            <textarea class="form-control" id="edit-voice-desc" rows="2">${char.voice_config?.voice_description || ''}</textarea>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Visual Description</label>
                            <textarea class="form-control" id="edit-visual-desc" rows="3" ${char.visual_frozen ? 'disabled' : ''}>${char.visual_frozen || char.visual_description || ''}</textarea>
                            ${char.visual_frozen ? '<small class="text-warning">Visual is frozen</small>' : ''}
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" onclick="saveCharacter('${charId}')">Save Changes</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
    const modal = new bootstrap.Modal(document.getElementById('editCharModal'));
    modal.show();

    document.getElementById('editCharModal').addEventListener('hidden.bs.modal', function () {
        this.remove();
    });
}

/**
 * Save Character Changes
 */
async function saveCharacter(charId) {
    const speaker = document.getElementById('edit-voice-speaker').value;
    const voiceDesc = document.getElementById('edit-voice-desc').value;
    const visualDesc = document.getElementById('edit-visual-desc').value;

    currentSeriesState.characters[charId].voice_config = {
        speaker: speaker,
        voice_description: voiceDesc
    };

    if (!currentSeriesState.characters[charId].visual_frozen) {
        currentSeriesState.characters[charId].visual_description = visualDesc;
    }

    await saveSeriesState();
    bootstrap.Modal.getInstance(document.getElementById('editCharModal')).hide();
}

/**
 * Freeze Character Visual
 */
async function freezeCharacter(charId) {
    const char = currentSeriesState.characters[charId];
    char.visual_frozen = char.visual_description || 'Frozen visual description';

    await saveSeriesState();
}

/**
 * Save SeriesState to Lambda
 */
async function saveSeriesState() {
    showLoading(true);

    try {
        const response = await fetch(LAMBDA_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                operation: 'UPDATE',
                user_id: USER_ID,
                channel_id: currentChannelId,
                series_id: currentSeriesId,
                series_state: currentSeriesState
            })
        });

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Failed to save');
        }

        showSuccess('Changes saved successfully!');
        renderAllTabs();

    } catch (error) {
        console.error('Error saving:', error);
        showError('Failed to save: ' + error.message);
    } finally {
        showLoading(false);
    }
}

/**
 * UI Helpers
 */
function showLoading(show) {
    const spinner = document.getElementById('loading-spinner');
    if (spinner) {
        spinner.style.display = show ? 'block' : 'none';
    }
}

function showError(message) {
    alert('Error: ' + message);
}

function showSuccess(message) {
    // Simple success notification
    const toast = document.createElement('div');
    toast.className = 'alert alert-success position-fixed top-0 start-50 translate-middle-x mt-3';
    toast.style.zIndex = '9999';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => toast.remove(), 3000);
}

function setupEventListeners() {
    // Add any global event listeners here
}

// Export functions for onclick handlers
window.editCharacter = editCharacter;
window.saveCharacter = saveCharacter;
window.freezeCharacter = freezeCharacter;
