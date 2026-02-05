/**
 * PWA Install Prompt Handler
 * Shows a beautiful install prompt for desktop and mobile users
 */

let deferredPrompt;
let installPromptShown = false;

// Check if app is already installed
function isAppInstalled() {
  // Check if running in standalone mode (already installed)
  if (window.matchMedia('(display-mode: standalone)').matches) {
    return true;
  }
  // Check if running as iOS PWA
  if (window.navigator.standalone === true) {
    return true;
  }
  // Check localStorage to see if user dismissed
  if (localStorage.getItem('pwa-install-dismissed')) {
    const dismissedTime = parseInt(localStorage.getItem('pwa-install-dismissed'));
    const daysSinceDismissed = (Date.now() - dismissedTime) / (1000 * 60 * 60 * 24);
    // Show again after 7 days
    if (daysSinceDismissed < 7) {
      return true;
    }
  }
  return false;
}

// Create install prompt HTML
function createInstallPrompt() {
  const promptHTML = `
    <div id="pwa-install-prompt" class="pwa-install-prompt">
      <div class="pwa-install-overlay"></div>
      <div class="pwa-install-content">
        <button class="pwa-install-close" id="pwa-install-close" aria-label="Close">×</button>

        <div class="pwa-install-icon">
          <img src="/static/logo.png" alt="PhysioPRISM">
        </div>

        <h2 class="pwa-install-title">Install PhysiologicPRISM</h2>

        <p class="pwa-install-description">
          Get instant access from your desktop or home screen. Works offline and loads faster!
        </p>

        <div class="pwa-install-benefits">
          <div class="pwa-benefit">
            <span class="pwa-benefit-icon">⚡</span>
            <span class="pwa-benefit-text">Lightning Fast</span>
          </div>
          <div class="pwa-benefit">
            <span class="pwa-benefit-icon">📱</span>
            <span class="pwa-benefit-text">Works Offline</span>
          </div>
          <div class="pwa-benefit">
            <span class="pwa-benefit-icon">🔒</span>
            <span class="pwa-benefit-text">Secure & Private</span>
          </div>
          <div class="pwa-benefit">
            <span class="pwa-benefit-icon">🚀</span>
            <span class="pwa-benefit-text">One-Click Access</span>
          </div>
        </div>

        <button class="pwa-install-button" id="pwa-install-button">
          <span class="pwa-install-button-icon">📥</span>
          Install Now
        </button>

        <button class="pwa-install-later" id="pwa-install-later">
          Maybe Later
        </button>
      </div>
    </div>
  `;

  document.body.insertAdjacentHTML('beforeend', promptHTML);

  // Add CSS if not already added
  if (!document.getElementById('pwa-install-styles')) {
    const styles = document.createElement('style');
    styles.id = 'pwa-install-styles';
    styles.textContent = `
      .pwa-install-prompt {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        z-index: 10000;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 20px;
        animation: pwaFadeIn 0.3s ease-out;
      }

      .pwa-install-overlay {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.6);
        backdrop-filter: blur(4px);
      }

      .pwa-install-content {
        position: relative;
        background: white;
        border-radius: 16px;
        padding: 32px 24px;
        max-width: 440px;
        width: 100%;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        animation: pwaSlideUp 0.4s ease-out;
        text-align: center;
      }

      .pwa-install-close {
        position: absolute;
        top: 12px;
        right: 12px;
        background: transparent;
        border: none;
        font-size: 32px;
        color: #9ca3af;
        cursor: pointer;
        width: 40px;
        height: 40px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        transition: all 0.2s;
      }

      .pwa-install-close:hover {
        background: #f3f4f6;
        color: #4b5563;
      }

      .pwa-install-icon {
        width: 80px;
        height: 80px;
        margin: 0 auto 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 16px;
        padding: 12px;
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.3);
      }

      .pwa-install-icon img {
        width: 100%;
        height: 100%;
        object-fit: contain;
      }

      .pwa-install-title {
        font-size: 24px;
        font-weight: 700;
        color: #1a202c;
        margin-bottom: 12px;
      }

      .pwa-install-description {
        font-size: 15px;
        color: #6b7280;
        line-height: 1.6;
        margin-bottom: 24px;
      }

      .pwa-install-benefits {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
        margin-bottom: 24px;
      }

      .pwa-benefit {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 12px 8px;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 6px;
      }

      .pwa-benefit-icon {
        font-size: 24px;
      }

      .pwa-benefit-text {
        font-size: 12px;
        font-weight: 600;
        color: #4b5563;
      }

      .pwa-install-button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 14px 24px;
        font-size: 16px;
        font-weight: 600;
        border-radius: 8px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        transition: transform 0.2s, box-shadow 0.2s;
        margin-bottom: 12px;
      }

      .pwa-install-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
      }

      .pwa-install-button:active {
        transform: translateY(0);
      }

      .pwa-install-button-icon {
        font-size: 20px;
      }

      .pwa-install-later {
        width: 100%;
        background: transparent;
        color: #6b7280;
        border: none;
        padding: 10px;
        font-size: 14px;
        cursor: pointer;
        transition: color 0.2s;
      }

      .pwa-install-later:hover {
        color: #374151;
      }

      @keyframes pwaFadeIn {
        from {
          opacity: 0;
        }
        to {
          opacity: 1;
        }
      }

      @keyframes pwaSlideUp {
        from {
          transform: translateY(40px);
          opacity: 0;
        }
        to {
          transform: translateY(0);
          opacity: 1;
        }
      }

      @media (max-width: 480px) {
        .pwa-install-content {
          padding: 24px 20px;
        }

        .pwa-install-title {
          font-size: 20px;
        }

        .pwa-install-benefits {
          grid-template-columns: 1fr 1fr;
          gap: 8px;
        }

        .pwa-benefit {
          padding: 10px 6px;
        }

        .pwa-benefit-icon {
          font-size: 20px;
        }

        .pwa-benefit-text {
          font-size: 11px;
        }
      }
    `;
    document.head.appendChild(styles);
  }
}

// Show install prompt
function showInstallPrompt() {
  if (installPromptShown) return;

  createInstallPrompt();
  installPromptShown = true;

  const prompt = document.getElementById('pwa-install-prompt');
  const installButton = document.getElementById('pwa-install-button');
  const laterButton = document.getElementById('pwa-install-later');
  const closeButton = document.getElementById('pwa-install-close');

  // Install button click
  installButton.addEventListener('click', async () => {
    if (deferredPrompt) {
      // Show browser's native install prompt
      deferredPrompt.prompt();

      // Wait for user's response
      const { outcome } = await deferredPrompt.userChoice;
      console.log(`PWA install outcome: ${outcome}`);

      // Clear the deferredPrompt
      deferredPrompt = null;
    }

    hideInstallPrompt();
  });

  // Later button click
  laterButton.addEventListener('click', () => {
    hideInstallPrompt();
    localStorage.setItem('pwa-install-dismissed', Date.now().toString());
  });

  // Close button click
  closeButton.addEventListener('click', () => {
    hideInstallPrompt();
    localStorage.setItem('pwa-install-dismissed', Date.now().toString());
  });

  // Close on overlay click
  document.querySelector('.pwa-install-overlay').addEventListener('click', () => {
    hideInstallPrompt();
    localStorage.setItem('pwa-install-dismissed', Date.now().toString());
  });
}

// Hide install prompt
function hideInstallPrompt() {
  const prompt = document.getElementById('pwa-install-prompt');
  if (prompt) {
    prompt.style.animation = 'pwaFadeIn 0.2s ease-out reverse';
    setTimeout(() => {
      prompt.remove();
    }, 200);
  }
}

// Listen for beforeinstallprompt event
window.addEventListener('beforeinstallprompt', (e) => {
  console.log('[PWA] beforeinstallprompt event fired');

  // Prevent the default browser prompt
  e.preventDefault();

  // Store the event for later use
  deferredPrompt = e;

  // Check if we should show the prompt
  if (!isAppInstalled()) {
    // Show prompt after 5 seconds to not be intrusive
    setTimeout(() => {
      showInstallPrompt();
    }, 5000);
  }
});

// Listen for app installed event
window.addEventListener('appinstalled', () => {
  console.log('[PWA] App installed successfully!');

  // Clear the deferredPrompt
  deferredPrompt = null;

  // Hide the prompt if it's showing
  hideInstallPrompt();

  // Remove dismissed flag
  localStorage.removeItem('pwa-install-dismissed');

  // Optional: Show a thank you message
  if (typeof showFlash === 'function') {
    showFlash('success', 'PhysioPRISM installed successfully! 🎉');
  }
});

// iOS Install Instructions (iOS doesn't support beforeinstallprompt)
function showIOSInstallInstructions() {
  const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
  const isInStandaloneMode = window.navigator.standalone === true;

  if (isIOS && !isInStandaloneMode && !isAppInstalled()) {
    // Show iOS-specific instructions after 10 seconds
    setTimeout(() => {
      const iosPromptHTML = `
        <div id="pwa-ios-prompt" class="pwa-install-prompt">
          <div class="pwa-install-overlay"></div>
          <div class="pwa-install-content">
            <button class="pwa-install-close" onclick="document.getElementById('pwa-ios-prompt').remove()">×</button>

            <div class="pwa-install-icon">
              <img src="/static/logo.png" alt="PhysioPRISM">
            </div>

            <h2 class="pwa-install-title">Install on iPhone</h2>

            <p class="pwa-install-description">
              To install PhysioPRISM on your iPhone:
            </p>

            <div style="text-align: left; background: #f9fafb; padding: 16px; border-radius: 8px; margin: 16px 0;">
              <ol style="margin: 0; padding-left: 20px; color: #4b5563; line-height: 1.8;">
                <li>Tap the <strong>Share</strong> button <span style="font-size: 18px;">⬆️</span></li>
                <li>Scroll down and tap <strong>"Add to Home Screen"</strong> <span style="font-size: 18px;">➕</span></li>
                <li>Tap <strong>"Add"</strong> in the top right</li>
              </ol>
            </div>

            <button class="pwa-install-later" onclick="document.getElementById('pwa-ios-prompt').remove(); localStorage.setItem('pwa-install-dismissed', Date.now());">
              Got it!
            </button>
          </div>
        </div>
      `;

      document.body.insertAdjacentHTML('beforeend', iosPromptHTML);
    }, 10000);
  }
}

// Initialize on page load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', showIOSInstallInstructions);
} else {
  showIOSInstallInstructions();
}

// Log PWA status
console.log('[PWA] Install handler loaded');
console.log('[PWA] Running in standalone mode:', window.matchMedia('(display-mode: standalone)').matches);
