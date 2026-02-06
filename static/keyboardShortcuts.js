/**
 * PhysioPRISM - Keyboard Shortcuts Manager
 * ========================================
 *
 * Provides power user features:
 * - Navigation shortcuts (N = new patient, D = dashboard, etc.)
 * - Action shortcuts (Ctrl+S = save, Ctrl+P = print, etc.)
 * - Command palette (Ctrl+K) - searchable quick actions
 * - Help modal (?) - shows all available shortcuts
 *
 * Usage: This file is automatically loaded in base.html
 */

(function() {
  'use strict';

  // ============================================================================
  // CONFIGURATION
  // ============================================================================

  const SHORTCUTS = {
    // Navigation shortcuts (single key, no modifier)
    navigation: [
      { key: 'd', name: 'Dashboard', action: () => navigate('/dashboard'), description: 'Go to dashboard' },
      { key: 'n', name: 'New Patient', action: () => navigate('/add_patient'), description: 'Add a new patient' },
      { key: 'p', name: 'View Patients', action: () => navigate('/view_patients'), description: 'View all patients' },
      { key: 's', name: 'Subscription', action: () => navigate('/subscription_dashboard'), description: 'View subscription' },
      { key: 'b', name: 'Blog', action: () => navigate('/blog_list'), description: 'View blog' },
      { key: 'e', name: 'Export Data', action: () => navigate('/export_data'), description: 'Export your data' },
      { key: 'a', name: 'Audit Logs', action: () => navigate('/audit_logs'), description: 'View audit logs' },
    ],

    // Action shortcuts (with modifiers like Ctrl/Cmd)
    actions: [
      {
        key: 's',
        ctrl: true,
        name: 'Save',
        action: saveForm,
        description: 'Save current form',
        icon: '💾'
      },
      {
        key: 'p',
        ctrl: true,
        name: 'Print',
        action: printPage,
        description: 'Print current page',
        icon: '🖨️'
      },
      {
        key: 'k',
        ctrl: true,
        name: 'Command Palette',
        action: openCommandPalette,
        description: 'Open command palette',
        icon: '⌘'
      },
    ],

    // Special shortcuts
    special: [
      { key: '/', name: 'Search', action: focusSearch, description: 'Focus on search input' },
      { key: 'Escape', name: 'Close', action: closeModals, description: 'Close modals and dialogs' },
      { key: '?', name: 'Help', action: showKeyboardHelp, description: 'Show keyboard shortcuts' },
    ],
  };

  // Command palette actions (searchable)
  const COMMANDS = [
    // Patient management
    { name: 'Add New Patient', icon: '➕', shortcut: 'N', action: () => navigate('/add_patient') },
    { name: 'View All Patients', icon: '👥', shortcut: 'P', action: () => navigate('/view_patients') },
    { name: 'Export Patient Data', icon: '📥', shortcut: 'E', action: () => navigate('/export_data') },

    // Navigation
    { name: 'Go to Dashboard', icon: '🏠', shortcut: 'D', action: () => navigate('/dashboard') },
    { name: 'View Subscription', icon: '💳', shortcut: 'S', action: () => navigate('/subscription_dashboard') },
    { name: 'View Blog', icon: '📝', shortcut: 'B', action: () => navigate('/blog_list') },
    { name: 'View Pricing', icon: '💰', action: () => navigate('/pricing') },
    { name: 'View Profile', icon: '👤', action: () => navigate('/edit_profile') },
    { name: 'View Invoices', icon: '🧾', action: () => navigate('/my_invoices') },
    { name: 'View Notifications', icon: '🔔', action: () => navigate('/notifications') },

    // Admin actions
    { name: 'Audit Logs', icon: '📋', shortcut: 'A', action: () => navigate('/audit_logs') },
    { name: 'Manage Users', icon: '⚙️', action: () => navigate('/manage_users') },
    { name: 'Approve Physiotherapists', icon: '✅', action: () => navigate('/approve_physios') },

    // Actions
    { name: 'Save Current Form', icon: '💾', shortcut: 'Ctrl+S', action: saveForm },
    { name: 'Print Current Page', icon: '🖨️', shortcut: 'Ctrl+P', action: printPage },
    { name: 'Toggle Dark Mode', icon: '🌙', action: toggleTheme },
    { name: 'Show Keyboard Shortcuts', icon: '⌨️', shortcut: '?', action: showKeyboardHelp },
    { name: 'Logout', icon: '🚪', action: () => navigate('/logout') },
  ];

  // ============================================================================
  // STATE
  // ============================================================================

  let isCommandPaletteOpen = false;
  let isHelpModalOpen = false;
  let commandSearchQuery = '';

  // ============================================================================
  // HELPER FUNCTIONS
  // ============================================================================

  function navigate(url) {
    window.location.href = url;
  }

  function saveForm() {
    // Find the active form and submit it
    const forms = document.querySelectorAll('form');
    if (forms.length === 0) {
      showToast('No form found on this page', 'info');
      return;
    }

    // Prefer forms with a visible submit button
    let targetForm = null;
    for (const form of forms) {
      const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
      if (submitBtn && !form.closest('.modal[style*="display: none"]')) {
        targetForm = form;
        break;
      }
    }

    if (!targetForm) {
      targetForm = forms[0];
    }

    // Check if form has data-no-keyboard-save attribute
    if (targetForm.hasAttribute('data-no-keyboard-save')) {
      showToast('Keyboard save disabled for this form', 'info');
      return;
    }

    // Trigger form submission
    const submitBtn = targetForm.querySelector('button[type="submit"], input[type="submit"]');
    if (submitBtn) {
      submitBtn.click();
      showToast('Saving...', 'success');
    } else {
      targetForm.requestSubmit();
      showToast('Saving...', 'success');
    }
  }

  function printPage() {
    window.print();
  }

  function focusSearch() {
    // Try to find search/filter input
    const searchInputs = [
      document.querySelector('input[type="search"]'),
      document.querySelector('input[placeholder*="search" i]'),
      document.querySelector('input[placeholder*="filter" i]'),
      document.querySelector('#patient-search'),
      document.querySelector('#search'),
      document.querySelector('.search-input'),
    ];

    const searchInput = searchInputs.find(input => input && isVisible(input));

    if (searchInput) {
      searchInput.focus();
      searchInput.select();
    } else {
      showToast('No search input found on this page', 'info');
    }
  }

  function closeModals() {
    // Close AI modal if open
    const aiModal = document.getElementById('ai-suggestion-modal');
    if (aiModal && aiModal.style.display !== 'none') {
      aiModal.style.display = 'none';
      return;
    }

    // Close command palette if open
    if (isCommandPaletteOpen) {
      closeCommandPalette();
      return;
    }

    // Close help modal if open
    if (isHelpModalOpen) {
      closeHelpModal();
      return;
    }

    // Close any other visible modals
    const modals = document.querySelectorAll('.modal, .popup, [role="dialog"]');
    let closed = false;
    modals.forEach(modal => {
      if (isVisible(modal)) {
        modal.style.display = 'none';
        closed = true;
      }
    });

    if (!closed) {
      // If no modals, blur active element (exit inputs)
      if (document.activeElement && document.activeElement.blur) {
        document.activeElement.blur();
      }
    }
  }

  function isVisible(element) {
    if (!element) return false;
    const style = window.getComputedStyle(element);
    return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
  }

  function showToast(message, type = 'info') {
    // Create toast notification
    const toast = document.createElement('div');
    toast.className = `keyboard-shortcut-toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 10);

    // Remove after 2 seconds
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 300);
    }, 2000);
  }

  function toggleTheme() {
    // Check if theme manager exists
    if (window.themeManager && typeof window.themeManager.cycleTheme === 'function') {
      window.themeManager.cycleTheme();
    } else {
      showToast('Theme manager not available', 'info');
    }
  }

  // ============================================================================
  // COMMAND PALETTE
  // ============================================================================

  function openCommandPalette() {
    if (isCommandPaletteOpen) return;

    isCommandPaletteOpen = true;
    commandSearchQuery = '';

    const paletteHTML = `
      <div id="command-palette-overlay" class="command-palette-overlay">
        <div class="command-palette">
          <div class="command-palette-header">
            <input
              type="text"
              id="command-search"
              class="command-search"
              placeholder="Type a command or search..."
              autocomplete="off"
              spellcheck="false"
            />
          </div>
          <div class="command-palette-body" id="command-results">
            ${renderCommandResults(COMMANDS)}
          </div>
          <div class="command-palette-footer">
            <span>Navigate with <kbd>↑</kbd><kbd>↓</kbd></span>
            <span>Execute with <kbd>Enter</kbd></span>
            <span>Close with <kbd>Esc</kbd></span>
          </div>
        </div>
      </div>
    `;

    document.body.insertAdjacentHTML('beforeend', paletteHTML);

    // Focus search input
    const searchInput = document.getElementById('command-search');
    searchInput.focus();

    // Add event listeners
    searchInput.addEventListener('input', handleCommandSearch);
    document.getElementById('command-palette-overlay').addEventListener('click', handlePaletteBackdropClick);

    // Add keyboard navigation
    let selectedIndex = 0;
    searchInput.addEventListener('keydown', (e) => {
      const results = document.querySelectorAll('.command-item');

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        selectedIndex = Math.min(selectedIndex + 1, results.length - 1);
        updateCommandSelection(results, selectedIndex);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        selectedIndex = Math.max(selectedIndex - 1, 0);
        updateCommandSelection(results, selectedIndex);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const selected = results[selectedIndex];
        if (selected) {
          selected.click();
        }
      }
    });

    // Initial selection
    updateCommandSelection(document.querySelectorAll('.command-item'), 0);
  }

  function closeCommandPalette() {
    const overlay = document.getElementById('command-palette-overlay');
    if (overlay) {
      overlay.remove();
    }
    isCommandPaletteOpen = false;
  }

  function handleCommandSearch(e) {
    commandSearchQuery = e.target.value.toLowerCase();
    const filteredCommands = COMMANDS.filter(cmd =>
      cmd.name.toLowerCase().includes(commandSearchQuery)
    );

    const resultsContainer = document.getElementById('command-results');
    resultsContainer.innerHTML = renderCommandResults(filteredCommands);

    // Reset selection
    updateCommandSelection(document.querySelectorAll('.command-item'), 0);
  }

  function renderCommandResults(commands) {
    if (commands.length === 0) {
      return '<div class="command-no-results">No commands found</div>';
    }

    return commands.map((cmd, index) => `
      <div class="command-item" data-index="${index}" onclick="window.executeCommand(${COMMANDS.indexOf(cmd)})">
        <span class="command-icon">${cmd.icon || '⚡'}</span>
        <span class="command-name">${cmd.name}</span>
        ${cmd.shortcut ? `<span class="command-shortcut">${cmd.shortcut}</span>` : ''}
      </div>
    `).join('');
  }

  function updateCommandSelection(results, index) {
    results.forEach((item, i) => {
      if (i === index) {
        item.classList.add('selected');
        item.scrollIntoView({ block: 'nearest' });
      } else {
        item.classList.remove('selected');
      }
    });
  }

  function handlePaletteBackdropClick(e) {
    if (e.target.id === 'command-palette-overlay') {
      closeCommandPalette();
    }
  }

  window.executeCommand = function(index) {
    const command = COMMANDS[index];
    if (command && command.action) {
      closeCommandPalette();
      command.action();
    }
  };

  // ============================================================================
  // KEYBOARD SHORTCUTS HELP MODAL
  // ============================================================================

  function showKeyboardHelp() {
    if (isHelpModalOpen) return;

    isHelpModalOpen = true;

    const helpHTML = `
      <div id="keyboard-help-overlay" class="keyboard-help-overlay">
        <div class="keyboard-help-modal">
          <div class="keyboard-help-header">
            <h2>⌨️ Keyboard Shortcuts</h2>
            <button class="keyboard-help-close" onclick="window.closeKeyboardHelp()">×</button>
          </div>
          <div class="keyboard-help-body">
            <div class="keyboard-help-section">
              <h3>🧭 Navigation</h3>
              <div class="keyboard-help-grid">
                ${SHORTCUTS.navigation.map(s => `
                  <div class="keyboard-help-item">
                    <kbd>${s.key.toUpperCase()}</kbd>
                    <span>${s.description}</span>
                  </div>
                `).join('')}
              </div>
            </div>

            <div class="keyboard-help-section">
              <h3>⚡ Actions</h3>
              <div class="keyboard-help-grid">
                ${SHORTCUTS.actions.map(s => `
                  <div class="keyboard-help-item">
                    <kbd>${s.ctrl ? 'Ctrl+' : ''}${s.key.toUpperCase()}</kbd>
                    <span>${s.description}</span>
                  </div>
                `).join('')}
              </div>
            </div>

            <div class="keyboard-help-section">
              <h3>🔍 Special</h3>
              <div class="keyboard-help-grid">
                ${SHORTCUTS.special.map(s => `
                  <div class="keyboard-help-item">
                    <kbd>${s.key === '/' ? '/' : s.key}</kbd>
                    <span>${s.description}</span>
                  </div>
                `).join('')}
              </div>
            </div>

            <div class="keyboard-help-tip">
              💡 <strong>Pro Tip:</strong> Press <kbd>Ctrl+K</kbd> or <kbd>Cmd+K</kbd> to open the command palette for quick access to all actions.
            </div>
          </div>
        </div>
      </div>
    `;

    document.body.insertAdjacentHTML('beforeend', helpHTML);

    // Add event listener for backdrop click
    document.getElementById('keyboard-help-overlay').addEventListener('click', (e) => {
      if (e.target.id === 'keyboard-help-overlay') {
        closeHelpModal();
      }
    });
  }

  function closeHelpModal() {
    const overlay = document.getElementById('keyboard-help-overlay');
    if (overlay) {
      overlay.remove();
    }
    isHelpModalOpen = false;
  }

  window.closeKeyboardHelp = closeHelpModal;

  // ============================================================================
  // KEYBOARD EVENT HANDLER
  // ============================================================================

  function handleKeyboardShortcut(e) {
    // Don't trigger shortcuts when typing in inputs (except for specific cases)
    const activeElement = document.activeElement;
    const isTyping = activeElement && (
      activeElement.tagName === 'INPUT' ||
      activeElement.tagName === 'TEXTAREA' ||
      activeElement.contentEditable === 'true'
    );

    // Check for Ctrl+K / Cmd+K (works even when typing)
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      openCommandPalette();
      return;
    }

    // Check for Escape (works even when typing)
    if (e.key === 'Escape') {
      e.preventDefault();
      closeModals();
      return;
    }

    // If typing, only allow specific shortcuts
    if (isTyping) {
      // Allow Ctrl+S when typing (save form)
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        saveForm();
        return;
      }
      // Don't process other shortcuts when typing
      return;
    }

    // Check for action shortcuts (with Ctrl/Cmd)
    if (e.ctrlKey || e.metaKey) {
      const actionShortcut = SHORTCUTS.actions.find(s =>
        s.key === e.key.toLowerCase() && s.ctrl
      );

      if (actionShortcut) {
        e.preventDefault();
        actionShortcut.action();
        return;
      }
    }

    // Check for navigation shortcuts (single key, no modifier)
    if (!e.ctrlKey && !e.metaKey && !e.altKey && !e.shiftKey) {
      // Check for special shortcuts first
      const specialShortcut = SHORTCUTS.special.find(s => s.key === e.key);
      if (specialShortcut) {
        e.preventDefault();
        specialShortcut.action();
        return;
      }

      // Check for navigation shortcuts
      const navShortcut = SHORTCUTS.navigation.find(s => s.key === e.key.toLowerCase());
      if (navShortcut) {
        e.preventDefault();
        navShortcut.action();
        return;
      }
    }
  }

  // ============================================================================
  // INITIALIZATION
  // ============================================================================

  function init() {
    // Add keyboard event listener
    document.addEventListener('keydown', handleKeyboardShortcut);

    // Wire up navbar keyboard shortcuts button
    const keyboardShortcutsBtn = document.getElementById('keyboard-shortcuts-btn');
    if (keyboardShortcutsBtn) {
      keyboardShortcutsBtn.addEventListener('click', showKeyboardHelp);
    }

    // Add visual indicator that shortcuts are available
    addShortcutIndicator();

    console.log('⌨️ Keyboard shortcuts initialized. Press ? for help.');
  }

  function addShortcutIndicator() {
    // Add a small indicator in the bottom right corner
    const indicator = document.createElement('div');
    indicator.className = 'keyboard-shortcuts-indicator';
    indicator.innerHTML = '⌨️ <span>Press <kbd>?</kbd> for shortcuts</span>';
    indicator.onclick = showKeyboardHelp;
    document.body.appendChild(indicator);

    // Hide after 5 seconds
    setTimeout(() => {
      indicator.classList.add('hidden');
    }, 5000);

    // Show on hover
    indicator.addEventListener('mouseenter', () => {
      indicator.classList.remove('hidden');
    });
  }

  // ============================================================================
  // START
  // ============================================================================

  // Wait for DOM to be ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
