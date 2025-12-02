/**
 * Unified Navigation Component
 * Single source of truth for site navigation
 */

const NAVIGATION_HTML = `
    <nav class="nav-container">
        <div class="nav-wrapper">
            <div class="nav-bar">
                <a href="index.html" class="nav-link">
                    <i class="bi bi-house-door"></i> Home
                </a>
                <a href="dashboard.html" class="nav-link">
                    <i class="bi bi-speedometer2"></i> Dashboard
                </a>
                <a href="channels.html" class="nav-link">
                    <i class="bi bi-collection"></i> Channels
                </a>
                <a href="content.html" class="nav-link">
                    <i class="bi bi-file-earmark-text"></i> Content
                </a>
                <a href="costs.html" class="nav-link">
                    <i class="bi bi-currency-dollar"></i> Costs
                </a>
                <a href="prompts-editor.html" class="nav-link">
                    <i class="bi bi-pencil-square"></i> Prompts
                </a>
                <a href="audio-library.html" class="nav-link">
                    <i class="bi bi-music-note-list"></i> Audio Library
                </a>
                <a href="settings.html" class="nav-link">
                    <i class="bi bi-gear"></i> Settings
                </a>
                <div class="nav-user-info" id="nav-user-info" style="margin-left: auto;">
                    <span id="user-email" style="color: #9ca3af; font-size: 0.9rem;"></span>
                    <button id="logout-btn" onclick="handleLogout()" style="margin-left: 10px; padding: 5px 15px; background: #ef4444; color: white; border: none; border-radius: 6px; cursor: pointer;">
                        <i class="bi bi-box-arrow-right"></i> Logout
                    </button>
                </div>
            </div>
        </div>
    </nav>
`;

/**
 * Handle logout
 */
function handleLogout() {
    // Clear session
    sessionStorage.clear();
    localStorage.clear();

    // Redirect to login
    window.location.href = 'login.html';
}

/**
 * Load user info into navigation
 */
async function loadUserInfo() {
    try {
        // Check if auth.js is loaded
        if (typeof AuthManager === 'undefined') {
            console.log('AuthManager not loaded yet, skipping user info');
            return;
        }

        const authManager = new AuthManager();
        const user = authManager.getUser();

        if (user && user.email) {
            const userEmailEl = document.getElementById('user-email');
            if (userEmailEl) {
                userEmailEl.textContent = user.email;
            }
        }
    } catch (error) {
        console.log('Could not load user info:', error);
    }
}

/**
 * Initialize navigation and set active link
 */
function initNavigation() {
    // Get current page
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';

    // Insert navigation HTML
    const navPlaceholder = document.getElementById('navigation-placeholder');
    if (navPlaceholder) {
        navPlaceholder.innerHTML = NAVIGATION_HTML;

        // Set active link
        const links = navPlaceholder.querySelectorAll('.nav-link');
        links.forEach(link => {
            const linkHref = link.getAttribute('href');
            if (linkHref === currentPage ||
                (currentPage === '' && linkHref === 'index.html')) {
                link.classList.add('active');
            }
        });

        // Load user info
        setTimeout(loadUserInfo, 100); // Small delay to ensure auth.js is loaded
    }
}

// Auto-initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initNavigation);
} else {
    initNavigation();
}
