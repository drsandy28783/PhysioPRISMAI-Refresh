/**
 * Version Check and Auto-Reload System
 * Automatically detects when a new version is deployed and prompts/auto-reloads
 */

(function() {
  'use strict';

  // Current app version - INCREMENT THIS WHEN DEPLOYING
  const CURRENT_VERSION = '1.0.6';

  // Check interval (10 minutes - less aggressive)
  const CHECK_INTERVAL = 10 * 60 * 1000;

  // Store version in sessionStorage for this tab
  const VERSION_KEY = 'app_version';
  const LAST_CHECK_KEY = 'last_version_check';
  const PENDING_UPDATE_KEY = 'pending_update_version';

  // Activity tracking
  let lastActivityTime = Date.now();
  let hasUnsavedChanges = false;
  let userInteractionDetected = false;

  // Configuration
  const CONFIG = {
    autoReload: false,  // Changed to false - show prompt instead of auto-reload
    showNotification: true,
    checkOnFocus: true,
    checkInterval: CHECK_INTERVAL,
    idleTimeout: 5 * 60 * 1000,  // 5 minutes idle before considering reload
    respectUnsavedChanges: true   // Never reload if user has unsaved changes
  };

  /**
   * Get the current version from the server
   */
  async function checkServerVersion() {
    try {
      const response = await fetch('/api/version', {
        method: 'GET',
        headers: {
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache'
        }
      });

      if (!response.ok) {
        console.warn('Version check failed:', response.status);
        return null;
      }

      const data = await response.json();
      return data.version;
    } catch (error) {
      console.warn('Version check error:', error);
      return null;
    }
  }

  /**
   * Show update notification with action buttons
   */
  function showUpdateNotification(newVersion) {
    // Remove existing notification if any
    const existing = document.getElementById('version-update-notification');
    if (existing) existing.remove();

    const notification = document.createElement('div');
    notification.id = 'version-update-notification';
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 20px 24px;
      border-radius: 12px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.2);
      z-index: 10000;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      max-width: 380px;
      animation: slideIn 0.3s ease-out;
    `;

    const hasChanges = detectUnsavedChanges();

    notification.innerHTML = `
      <div style="display: flex; align-items: flex-start; gap: 16px;">
        <span style="font-size: 32px;">🚀</span>
        <div style="flex: 1;">
          <div style="font-weight: 700; margin-bottom: 8px; font-size: 16px;">New Version Available!</div>
          <div style="font-size: 13px; opacity: 0.95; line-height: 1.5; margin-bottom: 12px;">
            Version ${newVersion} is ready. ${hasChanges ? '<strong>⚠️ You have unsaved changes!</strong>' : 'Refresh to get the latest features.'}
          </div>
          <div style="display: flex; gap: 8px; margin-top: 12px;">
            ${hasChanges ? `
              <button id="version-update-later" style="
                flex: 1;
                background: rgba(255,255,255,0.2);
                color: white;
                border: 1px solid rgba(255,255,255,0.3);
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                font-weight: 600;
                font-size: 13px;
                backdrop-filter: blur(10px);
              ">Save First</button>
            ` : `
              <button id="version-update-later" style="
                flex: 1;
                background: rgba(255,255,255,0.2);
                color: white;
                border: 1px solid rgba(255,255,255,0.3);
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                font-weight: 600;
                font-size: 13px;
                backdrop-filter: blur(10px);
              ">Later</button>
            `}
            <button id="version-update-now" style="
              flex: 1;
              background: white;
              color: #667eea;
              border: none;
              padding: 8px 16px;
              border-radius: 6px;
              cursor: pointer;
              font-weight: 700;
              font-size: 13px;
              box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            ">Refresh Now</button>
          </div>
        </div>
        <button id="version-update-close" style="
          background: transparent;
          border: none;
          color: white;
          font-size: 20px;
          cursor: pointer;
          padding: 0;
          width: 24px;
          height: 24px;
          opacity: 0.8;
          line-height: 1;
        ">×</button>
      </div>
    `;

    // Add animation keyframes
    const style = document.createElement('style');
    style.textContent = `
      @keyframes slideIn {
        from {
          transform: translateX(450px);
          opacity: 0;
        }
        to {
          transform: translateX(0);
          opacity: 1;
        }
      }
      #version-update-now:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      }
      #version-update-later:hover {
        background: rgba(255,255,255,0.3);
      }
    `;
    document.head.appendChild(style);

    document.body.appendChild(notification);

    // Event listeners
    document.getElementById('version-update-now').addEventListener('click', () => {
      reloadPage();
    });

    document.getElementById('version-update-later').addEventListener('click', () => {
      sessionStorage.setItem(PENDING_UPDATE_KEY, newVersion);
      notification.remove();
    });

    document.getElementById('version-update-close').addEventListener('click', () => {
      sessionStorage.setItem(PENDING_UPDATE_KEY, newVersion);
      notification.remove();
    });
  }

  /**
   * Detect unsaved changes in forms
   */
  function detectUnsavedChanges() {
    // Check for modified forms
    const forms = document.querySelectorAll('form');
    for (const form of forms) {
      if (form.classList.contains('dirty') || form.dataset.modified === 'true') {
        return true;
      }
    }

    // Check for textareas/inputs with content
    const textareas = document.querySelectorAll('textarea');
    for (const textarea of textareas) {
      if (textarea.value.trim() && textarea.dataset.originalValue !== textarea.value) {
        return true;
      }
    }

    // Check for contenteditable elements
    const editables = document.querySelectorAll('[contenteditable="true"]');
    for (const el of editables) {
      if (el.textContent.trim() && el.dataset.originalContent !== el.textContent) {
        return true;
      }
    }

    return hasUnsavedChanges;
  }

  /**
   * Track user activity
   */
  function trackActivity() {
    lastActivityTime = Date.now();
    userInteractionDetected = true;
  }

  /**
   * Check if user is idle
   */
  function isUserIdle() {
    return Date.now() - lastActivityTime > CONFIG.idleTimeout;
  }

  /**
   * Reload the page with cache busting
   */
  function reloadPage() {
    console.log('[Version Check] Reloading to get new version...');

    // Clear service worker cache if exists
    if ('caches' in window) {
      caches.keys().then(names => {
        names.forEach(name => caches.delete(name));
      });
    }

    // Hard reload with cache clear
    window.location.reload(true);
  }

  /**
   * Handle version update
   */
  function handleVersionUpdate(newVersion) {
    console.log('[Version Check] New version detected:', newVersion);

    // Check if user has unsaved changes
    const hasChanges = detectUnsavedChanges();

    if (hasChanges && CONFIG.respectUnsavedChanges) {
      console.log('[Version Check] User has unsaved changes - showing notification only');
      showUpdateNotification(newVersion);
      return;
    }

    // Check if user is actively using the app
    if (!isUserIdle() && userInteractionDetected) {
      console.log('[Version Check] User is active - showing notification');
      showUpdateNotification(newVersion);
      return;
    }

    // If auto-reload is enabled and user is idle
    if (CONFIG.autoReload && isUserIdle()) {
      console.log('[Version Check] User idle - auto-reloading');
      sessionStorage.setItem(VERSION_KEY, newVersion);
      setTimeout(reloadPage, 2000);
    } else {
      // Show notification for user to decide
      showUpdateNotification(newVersion);
    }
  }

  /**
   * Perform version check
   */
  async function performVersionCheck() {
    const storedVersion = sessionStorage.getItem(VERSION_KEY);

    // First time - just store current version
    if (!storedVersion) {
      sessionStorage.setItem(VERSION_KEY, CURRENT_VERSION);
      sessionStorage.setItem(LAST_CHECK_KEY, Date.now().toString());
      console.log('[Version Check] Initialized with version:', CURRENT_VERSION);
      return;
    }

    // Throttle checks (minimum 30 seconds between checks)
    const lastCheck = parseInt(sessionStorage.getItem(LAST_CHECK_KEY) || '0');
    const now = Date.now();
    if (now - lastCheck < 30000) {
      return; // Skip this check
    }

    sessionStorage.setItem(LAST_CHECK_KEY, now.toString());

    // Check server version
    const serverVersion = await checkServerVersion();

    if (!serverVersion) {
      return; // Skip if check failed
    }

    console.log('[Version Check] Current:', CURRENT_VERSION, 'Server:', serverVersion);

    // Compare versions
    if (serverVersion !== CURRENT_VERSION) {
      handleVersionUpdate(serverVersion);
    }
  }

  /**
   * Initialize version checking
   */
  function initialize() {
    console.log('[Version Check] Initialized - Version:', CURRENT_VERSION);
    console.log('[Version Check] Auto-reload:', CONFIG.autoReload ? 'Enabled' : 'Disabled (manual prompt)');
    console.log('[Version Check] Check interval:', CONFIG.checkInterval / 60000, 'minutes');

    // Track user activity
    const activityEvents = ['click', 'keydown', 'mousemove', 'scroll', 'touchstart'];
    activityEvents.forEach(event => {
      document.addEventListener(event, trackActivity, { passive: true, capture: true });
    });

    // Track form modifications
    document.addEventListener('input', (e) => {
      if (e.target.matches('input, textarea, [contenteditable]')) {
        trackActivity();
      }
    }, { passive: true });

    // Provide global API to mark unsaved changes
    window.markUnsavedChanges = function(hasChanges) {
      hasUnsavedChanges = hasChanges;
      console.log('[Version Check] Unsaved changes:', hasChanges);
    };

    // Initial check after 30 seconds (give app time to load)
    setTimeout(performVersionCheck, 30000);

    // Periodic checks
    setInterval(performVersionCheck, CONFIG.checkInterval);

    // Check when window regains focus (user came back to tab)
    if (CONFIG.checkOnFocus) {
      window.addEventListener('focus', () => {
        setTimeout(performVersionCheck, 2000);
      });
    }

    // Check when coming back from visibility hidden
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) {
        setTimeout(performVersionCheck, 2000);
      }
    });

    // Check for pending update on page load
    const pendingVersion = sessionStorage.getItem(PENDING_UPDATE_KEY);
    if (pendingVersion && pendingVersion !== CURRENT_VERSION) {
      console.log('[Version Check] Found pending update:', pendingVersion);
      setTimeout(() => showUpdateNotification(pendingVersion), 5000);
    }
  }

  // Start when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
  } else {
    initialize();
  }
})();
