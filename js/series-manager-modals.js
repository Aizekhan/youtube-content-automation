// ============================================
// THREADS MANAGEMENT
// ============================================

/**
 * Show modal to add new thread
 */
function showAddThreadModal() {
    const modalHTML = `
        <div class="modal fade" id="addThreadModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Add New Story Thread</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <label class="form-label">Thread Description</label>
                            <textarea class="form-control" id="thread-description" rows="3"
                                placeholder="What mystery or question will drive the story forward?"></textarea>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Priority</label>
                            <select class="form-select" id="thread-priority">
                                <option value="LOW">Low</option>
                                <option value="MEDIUM" selected>Medium</option>
                                <option value="HIGH">High</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Introduced in Episode</label>
                            <input type="number" class="form-control" id="thread-episode"
                                value="${currentSeriesState.episodes_generated + 1}" min="1">
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" onclick="addThread()">Add Thread</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
    const modal = new bootstrap.Modal(document.getElementById('addThreadModal'));
    modal.show();

    document.getElementById('addThreadModal').addEventListener('hidden.bs.modal', function () {
        this.remove();
    });
}

async function addThread() {
    const description = document.getElementById('thread-description').value.trim();
    const priority = document.getElementById('thread-priority').value;
    const episode = parseInt(document.getElementById('thread-episode').value);

    if (!description) {
        alert('Please enter thread description');
        return;
    }

    try {
        showLoading(true);

        const newThread = {
            thread_id: 'thread-' + Date.now(),
            description: description,
            priority: priority,
            introduced_ep: episode,
            status: 'open',
            resolution: null
        };

        currentSeriesState.plot_threads = currentSeriesState.plot_threads || [];
        currentSeriesState.plot_threads.push(newThread);

        await saveSeriesState();

        bootstrap.Modal.getInstance(document.getElementById('addThreadModal')).hide();
        renderThreadsTab();
        showSuccess('Thread added successfully!');

    } catch (error) {
        console.error('Error adding thread:', error);
        showError('Failed to add thread: ' + error.message);
    } finally {
        showLoading(false);
    }
}

async function closeThread(threadId) {
    const resolution = prompt('Enter resolution for this thread:');
    if (!resolution) return;

    try {
        showLoading(true);

        const thread = currentSeriesState.plot_threads.find(t => t.thread_id === threadId);
        if (thread) {
            thread.status = 'closed';
            thread.resolution = resolution;
            thread.resolved_ep = currentSeriesState.episodes_generated;
        }

        await saveSeriesState();
        renderThreadsTab();
        showSuccess('Thread closed!');

    } catch (error) {
        showError('Failed to close thread: ' + error.message);
    } finally {
        showLoading(false);
    }
}

async function reopenThread(threadId) {
    try {
        showLoading(true);

        const thread = currentSeriesState.plot_threads.find(t => t.thread_id === threadId);
        if (thread) {
            thread.status = 'open';
            thread.resolution = null;
            thread.resolved_ep = null;
        }

        await saveSeriesState();
        renderThreadsTab();
        showSuccess('Thread reopened!');

    } catch (error) {
        showError('Failed to reopen thread: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// ============================================
// CHARACTERS MANAGEMENT
// ============================================

function showAddCharacterModal() {
    const modalHTML = `
        <div class="modal fade" id="addCharacterModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Add New Character</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <label class="form-label">Character Name</label>
                            <input type="text" class="form-control" id="char-name" placeholder="e.g., Elena">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Gender</label>
                            <select class="form-select" id="char-gender">
                                <option value="male">Male</option>
                                <option value="female">Female</option>
                                <option value="neutral">Neutral</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Age Group</label>
                            <select class="form-select" id="char-age">
                                <option value="child">Child</option>
                                <option value="young_adult" selected>Young Adult</option>
                                <option value="adult">Adult</option>
                                <option value="elder">Elder</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Character Type</label>
                            <select class="form-select" id="char-type">
                                <option value="protagonist">Protagonist</option>
                                <option value="mirror" selected>Mirror Character</option>
                                <option value="antagonist">Antagonist</option>
                                <option value="supporting">Supporting</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Description</label>
                            <textarea class="form-control" id="char-description" rows="3"
                                placeholder="Physical traits, personality, role in story..."></textarea>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" onclick="addCharacter()">Add Character</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
    const modal = new bootstrap.Modal(document.getElementById('addCharacterModal'));
    modal.show();

    document.getElementById('addCharacterModal').addEventListener('hidden.bs.modal', function () {
        this.remove();
    });
}

async function addCharacter() {
    const name = document.getElementById('char-name').value.trim();
    const gender = document.getElementById('char-gender').value;
    const ageGroup = document.getElementById('char-age').value;
    const charType = document.getElementById('char-type').value;
    const description = document.getElementById('char-description').value.trim();

    if (!name || !description) {
        alert('Please enter character name and description');
        return;
    }

    try {
        showLoading(true);

        const charId = name.toLowerCase().replace(/\s+/g, '_');

        currentSeriesState.characters = currentSeriesState.characters || {};
        currentSeriesState.characters[charId] = {
            name: name,
            gender: gender,
            age_group: ageGroup,
            character_type: charType,
            description: description,
            voice_config: inferVoice({ gender, age_group: ageGroup, character_type: charType, description }),
            appearances: [],
            current_state: '',
            frozen_string: null
        };

        await saveSeriesState();

        bootstrap.Modal.getInstance(document.getElementById('addCharacterModal')).hide();
        renderCharactersTab();
        showSuccess('Character added successfully!');

    } catch (error) {
        console.error('Error adding character:', error);
        showError('Failed to add character: ' + error.message);
    } finally {
        showLoading(false);
    }
}

function inferVoice(charData) {
    const VOICE_MAPPING = {
        'male-child': 'aiden',
        'male-young_adult': 'dylan',
        'male-adult': 'ryan',
        'male-elder': 'uncle_fu',
        'female-child': 'sohee',
        'female-young_adult': 'vivian',
        'female-adult': 'serena',
        'female-elder': 'ono_anna',
    };

    const key = charData.gender + '-' + charData.age_group;
    const speaker = VOICE_MAPPING[key] || 'ryan';
    const voiceDesc = charData.gender + ' ' + charData.age_group.replace('_', ' ') + ' voice';

    return { speaker, voice_description: voiceDesc };
}

// Make functions global
window.showAddThreadModal = showAddThreadModal;
window.addThread = addThread;
window.closeThread = closeThread;
window.reopenThread = reopenThread;
window.showAddCharacterModal = showAddCharacterModal;
window.addCharacter = addCharacter;
