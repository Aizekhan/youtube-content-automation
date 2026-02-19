// ============================================
// AUTH.JS - Session Management Module
// YouTube Content Automation - Multi-Tenant
// ============================================

class AuthManager {
    constructor() {
        this.user = null;
        this.idToken = null;
        this.accessToken = null;
        this.refreshToken = null;
        this.expiresAt = null;
        this.sessionKey = 'auth_session';

        // Auth configuration (populated from Cognito setup)
        this.config = {
            region: 'eu-central-1',
            userPoolId: 'eu-central-1_bQB8rhdoH',
            userPoolWebClientId: '78dqpfmq8qn43gmig2pan0v9sb',
            authDomain: 'https://youtube-automation-1764343453.auth.eu-central-1.amazoncognito.com',
        };
    }

    // ========================================
    // INITIALIZATION
    // ========================================

    /**
     * Initialize auth manager and check session
     * Call this on every page load
     * @returns {Promise<boolean>} true if authenticated, false otherwise
     */
    async initialize() {
        try {
            // Try to load existing session
            const session = this.loadSession();

            if (!session) {
                console.log(' No session found, user not authenticated');
                return false;
            }

            // Check if session expired
            const expiresAt = new Date(session.expiresAt);
            const now = new Date();

            if (expiresAt <= now) {
                console.log('⏰ Session expired');

                // Try to refresh token
                if (session.refreshToken) {
                    const refreshed = await this.refreshSession(session.refreshToken);
                    if (refreshed) {
                        console.log(' Session refreshed successfully');
                        return true;
                    }
                }

                // Refresh failed, clear session
                this.clearSession();
                return false;
            }

            // Session valid
            this.user = session.user;
            this.idToken = session.idToken;
            this.accessToken = session.accessToken;
            this.refreshToken = session.refreshToken;
            this.expiresAt = session.expiresAt;

            console.log(' Session loaded:', this.user.email);
            return true;

        } catch (error) {
            console.error(' Auth initialization error:', error);
            this.clearSession();
            return false;
        }
    }

    /**
     * Require authentication - redirect to login if not authenticated
     * Call this at the start of protected pages
     */
    async requireAuth() {
        const isAuthenticated = await this.initialize();

        if (!isAuthenticated) {
            // Save current page for redirect after login (using cookies)
            this.setCookie('auth_redirect', window.location.pathname + window.location.search, 1);

            // Redirect to login
            window.location.href = '/login.html';
            return false;
        }

        return true;
    }

    // ========================================
    // SESSION MANAGEMENT
    // ========================================

    /**
     * Set a cookie with security flags
     *
     * SECURITY FIX:
     * - Added Secure flag (cookies only sent over HTTPS)
     * - Changed SameSite to Strict (prevents CSRF attacks)
     *
     * Note: HttpOnly flag cannot be set via JavaScript (requires backend)
     */
    setCookie(name, value, days = 7) {
        const expires = new Date();
        expires.setTime(expires.getTime() + (days * 24 * 60 * 60 * 1000));

        // Build cookie string with security flags
        let cookieString = name + "=" + encodeURIComponent(value);
        cookieString += ";expires=" + expires.toUTCString();
        cookieString += ";path=/";
        cookieString += ";SameSite=Strict";  // Prevent CSRF (was Lax)

        // Add Secure flag for HTTPS (in production)
        // Detect if running on HTTPS
        if (window.location.protocol === 'https:') {
            cookieString += ";Secure";
        } else {
            console.warn('Not using HTTPS - Secure cookie flag not set');
        }

        document.cookie = cookieString;
    }

    /**
     * Get a cookie
     */
    getCookie(name) {
        const nameEQ = name + "=";
        const ca = document.cookie.split(';');
        for(let i = 0; i < ca.length; i++) {
            let c = ca[i];
            while (c.charAt(0) === ' ') c = c.substring(1);
            if (c.indexOf(nameEQ) === 0) return decodeURIComponent(c.substring(nameEQ.length));
        }
        return null;
    }

    /**
     * Delete a cookie
     */
    deleteCookie(name) {
        document.cookie = name + "=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/;";
    }

    /**
     * Load session from cookies (replaces localStorage)
     * Reads from multiple cookies (split to avoid 4KB limit)
     * @returns {Object|null} Session object or null
     */
    loadSession() {
        try {
            // Read from individual cookies
            const idToken = this.getCookie('auth_id_token');
            const accessToken = this.getCookie('auth_access_token');
            const refreshToken = this.getCookie('auth_refresh_token');
            const userStr = this.getCookie('auth_user');
            const expiresAt = this.getCookie('auth_expires');

            // Check if all required cookies exist
            if (!idToken || !userStr || !expiresAt) {
                return null;
            }

            // Parse user object
            const user = JSON.parse(userStr);

            // Reconstruct session object
            return {
                idToken,
                accessToken,
                refreshToken,
                user,
                expiresAt
            };
        } catch (error) {
            console.error('Error loading session:', error);
            return null;
        }
    }

    /**
     * Save session to cookies (replaces localStorage)
     * Split into multiple cookies to avoid 4KB limit
     * @param {Object} session - Session object
     */
    saveSession(session) {
        try {
            // Store tokens and data in separate cookies to avoid size limit
            this.setCookie('auth_id_token', session.idToken, 7);
            this.setCookie('auth_access_token', session.accessToken, 7);
            this.setCookie('auth_refresh_token', session.refreshToken, 7);
            this.setCookie('auth_user', JSON.stringify(session.user), 7);
            this.setCookie('auth_expires', session.expiresAt, 7);

            // Update instance variables
            this.user = session.user;
            this.idToken = session.idToken;
            this.accessToken = session.accessToken;
            this.refreshToken = session.refreshToken;
            this.expiresAt = session.expiresAt;

            console.log(' Session saved to cookies (split into 5 cookies)');

        } catch (error) {
            console.error('Error saving session:', error);
        }
    }

    /**
     * Clear session from cookies and memory
     */
    clearSession() {
        // Delete all auth cookies
        this.deleteCookie('auth_id_token');
        this.deleteCookie('auth_access_token');
        this.deleteCookie('auth_refresh_token');
        this.deleteCookie('auth_user');
        this.deleteCookie('auth_expires');
        this.deleteCookie('auth_redirect');

        // Also delete old cookie if it exists
        this.deleteCookie(this.sessionKey);

        this.user = null;
        this.idToken = null;
        this.accessToken = null;
        this.refreshToken = null;
        this.expiresAt = null;
    }

    /**
     * Refresh access token using refresh token
     * @param {string} refreshToken - Refresh token
     * @returns {Promise<boolean>} true if successful
     */
    async refreshSession(refreshToken) {
        try {
            const params = new URLSearchParams({
                grant_type: 'refresh_token',
                client_id: this.config.userPoolWebClientId,
                refresh_token: refreshToken
            });

            const response = await fetch(`${this.config.authDomain}/oauth2/token`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: params.toString()
            });

            if (!response.ok) {
                return false;
            }

            const tokens = await response.json();

            // Parse new ID token
            const userInfo = this.parseJwt(tokens.id_token);

            // Save new session
            const session = {
                idToken: tokens.id_token,
                accessToken: tokens.access_token,
                refreshToken: refreshToken,  // Keep old refresh token
                expiresAt: new Date(Date.now() + tokens.expires_in * 1000).toISOString(),
                user: {
                    user_id: userInfo.sub,
                    email: userInfo.email,
                    name: userInfo.name,
                    picture: userInfo.picture
                }
            };

            this.saveSession(session);
            return true;

        } catch (error) {
            console.error('Error refreshing session:', error);
            return false;
        }
    }

    // ========================================
    // AUTHENTICATION HEADERS
    // ========================================

    /**
     * Get authentication headers for API calls
     * @returns {Object} Headers object
     */
    getAuthHeaders() {
        if (!this.idToken) {
            console.warn(' No auth token available');
            return {};
        }

        return {
            'Authorization': `Bearer ${this.idToken}`,
            'X-User-ID': this.user?.user_id || '',
            'Content-Type': 'application/json'
        };
    }

    /**
     * Get user ID for queries
     *
     *  SECURITY WARNING: This user_id is extracted from an UNVERIFIED JWT!
     * Backend Lambda functions MUST validate the JWT signature and extract
     * user_id from the verified token, NOT from this client-provided value.
     *
     * This is only for convenience (pre-filling forms, etc.)
     *
     * @returns {string|null} User ID (UNVERIFIED - for display only)
     */
    getUserId() {
        return this.user?.user_id || null;
    }

    // ========================================
    // LOGOUT
    // ========================================

    /**
     * Sign out user and redirect to login
     */
    signOut() {
        const logoutUrl = `${this.config.authDomain}/logout?` +
            `client_id=${this.config.userPoolWebClientId}&` +
            `logout_uri=${encodeURIComponent(window.location.origin + '/login.html')}`;

        // Clear local session
        this.clearSession();

        // Redirect to Cognito logout
        window.location.href = logoutUrl;
    }

    // ========================================
    // USER INFO
    // ========================================

    /**
     * Get current user info
     * @returns {Object|null} User object
     */
    getUser() {
        return this.user;
    }

    /**
     * Check if user is authenticated
     * @returns {boolean}
     */
    isAuthenticated() {
        return this.user !== null && this.idToken !== null;
    }

    /**
     * Get user's display name
     * @returns {string}
     */
    getUserDisplayName() {
        if (!this.user) return 'Guest';
        return this.user.name || this.user.email || 'User';
    }

    /**
     * Get user's profile picture URL
     * @returns {string|null}
     */
    getUserPicture() {
        return this.user?.picture || null;
    }

    // ========================================
    // UTILITIES
    // ========================================

    /**
     * Parse JWT token (CLIENT-SIDE ONLY - NO SIGNATURE VERIFICATION)
     *
     *  SECURITY WARNING: This function does NOT verify the JWT signature!
     * It only decodes the payload for display purposes (user info, expiration).
     *
     * NEVER use this for authorization decisions!
     * Backend MUST validate JWT signature before trusting any claims.
     *
     * @param {string} token - JWT token
     * @returns {Object} Decoded token payload (UNVERIFIED)
     */
    parseJwt(token) {
        try {
            if (!token || typeof token !== 'string') {
                throw new Error('Invalid token format');
            }

            const parts = token.split('.');
            if (parts.length !== 3) {
                throw new Error('Invalid JWT structure');
            }

            const base64Url = parts[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
                return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
            }).join(''));

            const payload = JSON.parse(jsonPayload);

            // Basic validation (NOT signature verification!)
            if (!payload.sub || !payload.exp) {
                console.warn('JWT missing required claims (sub, exp)');
            }

            // Check expiration (client-side check only, backend must verify!)
            const now = Math.floor(Date.now() / 1000);
            if (payload.exp && payload.exp < now) {
                console.warn('JWT has expired (client-side check)');
            }

            return payload;
        } catch (e) {
            console.error('Error parsing JWT:', e);
            return {};
        }
    }

    /**
     * Format time until session expires
     * @returns {string} Human-readable time
     */
    getSessionTimeRemaining() {
        if (!this.expiresAt) return 'Unknown';

        const now = new Date();
        const expires = new Date(this.expiresAt);
        const diff = expires - now;

        if (diff <= 0) return 'Expired';

        const hours = Math.floor(diff / (1000 * 60 * 60));
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

        if (hours > 0) {
            return `${hours}h ${minutes}m`;
        }
        return `${minutes}m`;
    }
}

// ============================================
// GLOBAL AUTH INSTANCE
// ============================================
const auth = new AuthManager();

// ============================================
// UI HELPERS
// ============================================

/**
 * Create user profile dropdown for navigation
 * Call this in navigation.js or page load
 */
function createUserProfileDropdown() {
    if (!auth.isAuthenticated()) return;

    const user = auth.getUser();
    const picture = auth.getUserPicture();
    const displayName = auth.getUserDisplayName();

    // Find or create profile container in navbar
    const navbar = document.querySelector('.navbar-nav');
    if (!navbar) return;

    // Create profile dropdown HTML
    const profileHTML = `
        <li class="nav-item dropdown ms-auto">
            <a class="nav-link dropdown-toggle d-flex align-items-center" href="#"
               id="userDropdown" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                ${picture ?
                    `<img src="${picture}" alt="Profile" class="rounded-circle me-2"
                         style="width: 32px; height: 32px; object-fit: cover;">` :
                    `<i class="bi bi-person-circle me-2" style="font-size: 1.5rem;"></i>`
                }
                <span>${displayName}</span>
            </a>
            <ul class="dropdown-menu dropdown-menu-end" aria-labelledby="userDropdown">
                <li>
                    <div class="dropdown-item-text">
                        <small class="text-muted">${user.email}</small>
                    </div>
                </li>
                <li><hr class="dropdown-divider"></li>
                <li>
                    <a class="dropdown-item" href="#">
                        <i class="bi bi-person me-2"></i>Profile
                    </a>
                </li>
                <li>
                    <a class="dropdown-item" href="#">
                        <i class="bi bi-gear me-2"></i>Settings
                    </a>
                </li>
                <li><hr class="dropdown-divider"></li>
                <li>
                    <a class="dropdown-item text-danger" href="#" onclick="auth.signOut()">
                        <i class="bi bi-box-arrow-right me-2"></i>Sign Out
                    </a>
                </li>
            </ul>
        </li>
    `;

    navbar.insertAdjacentHTML('beforeend', profileHTML);
}

/**
 * Show loading overlay during auth checks
 */
function showAuthLoadingOverlay() {
    const overlay = document.createElement('div');
    overlay.id = 'auth-loading-overlay';
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(26, 29, 46, 0.95);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9999;
    `;
    overlay.innerHTML = `
        <div style="text-align: center; color: #e5e7eb;">
            <div class="spinner-border" role="status" style="width: 3rem; height: 3rem; border-color: #667eea; border-right-color: transparent;">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p style="margin-top: 1rem;">Verifying authentication...</p>
        </div>
    `;
    document.body.appendChild(overlay);
}

function hideAuthLoadingOverlay() {
    const overlay = document.getElementById('auth-loading-overlay');
    if (overlay) overlay.remove();
}

// ============================================
// EXPORT FOR USE IN OTHER MODULES
// ============================================
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AuthManager, auth };
}
