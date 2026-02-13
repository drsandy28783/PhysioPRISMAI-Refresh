/**
 * PhysioPRISM - Smart Autocomplete from History
 * ==============================================
 *
 * Learns from YOUR past patient notes to provide intelligent suggestions.
 * Suggests phrases you've used before as you type.
 *
 * Usage: Automatically enabled on all textareas
 */

(function() {
  'use strict';

  // ============================================================================
  // CONFIGURATION
  // ============================================================================

  const CONFIG = {
    minQueryLength: 3,           // Minimum characters before showing suggestions
    debounceDelay: 300,          // Wait 300ms after typing stops
    maxSuggestions: 5,           // Show max 5 suggestions
    apiEndpoint: '/api/autocomplete/suggestions',
  };

  // ============================================================================
  // STATE
  // ============================================================================

  let activeField = null;
  let suggestionsList = null;
  let currentSuggestions = [];
  let selectedIndex = -1;
  let debounceTimer = null;

  // ============================================================================
  // INITIALIZATION
  // ============================================================================

  function init() {
    // Find all textareas
    const textareas = document.querySelectorAll('textarea');

    textareas.forEach(textarea => {
      // Skip if already initialized
      if (textarea.hasAttribute('data-autocomplete-enabled')) return;

      // Skip if explicitly disabled
      if (textarea.hasAttribute('data-autocomplete-disabled')) return;

      textarea.setAttribute('data-autocomplete-enabled', 'true');
      textarea.addEventListener('input', handleInput);
      textarea.addEventListener('keydown', handleKeyDown);
      textarea.addEventListener('blur', handleBlur);
      textarea.addEventListener('focus', handleFocus);
    });

    console.log(`🧠 Smart autocomplete enabled on ${textareas.length} fields`);
  }

  // ============================================================================
  // EVENT HANDLERS
  // ============================================================================

  function handleInput(e) {
    const field = e.target;
    const value = field.value;
    const cursorPos = field.selectionStart;

    // Get text before cursor
    const textBeforeCursor = value.substring(0, cursorPos);

    // Extract the current word/phrase being typed
    const currentPhrase = extractCurrentPhrase(textBeforeCursor);

    // Clear previous timer
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }

    // If phrase is too short, hide suggestions
    if (!currentPhrase || currentPhrase.length < CONFIG.minQueryLength) {
      hideSuggestions();
      return;
    }

    // Debounce API calls
    debounceTimer = setTimeout(() => {
      fetchSuggestions(field, currentPhrase);
    }, CONFIG.debounceDelay);
  }

  function handleKeyDown(e) {
    // Only handle if suggestions are visible
    if (!suggestionsList || currentSuggestions.length === 0) {
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        selectedIndex = Math.min(selectedIndex + 1, currentSuggestions.length - 1);
        updateSelection();
        break;

      case 'ArrowUp':
        e.preventDefault();
        selectedIndex = Math.max(selectedIndex - 1, 0);
        updateSelection();
        break;

      case 'Enter':
      case 'Tab':
        if (selectedIndex >= 0) {
          e.preventDefault();
          selectSuggestion(currentSuggestions[selectedIndex]);
        }
        break;

      case 'Escape':
        e.preventDefault();
        hideSuggestions();
        break;
    }
  }

  function handleBlur(e) {
    // Delay hiding to allow click on suggestion
    setTimeout(() => {
      if (activeField === e.target) {
        hideSuggestions();
      }
    }, 200);
  }

  function handleFocus(e) {
    activeField = e.target;
  }

  // ============================================================================
  // SUGGESTION LOGIC
  // ============================================================================

  /**
   * Extract the current phrase being typed (last sentence or partial sentence)
   */
  function extractCurrentPhrase(text) {
    // Split by sentence markers
    const sentences = text.split(/[.!?]\s*/);

    // Get the last sentence (current one being typed)
    const currentSentence = sentences[sentences.length - 1].trim();

    return currentSentence;
  }

  /**
   * Fetch suggestions from backend API
   */
  async function fetchSuggestions(field, query) {
    try {
      // Get field name (try id, then name attribute)
      const fieldName = field.id || field.name || 'unknown';

      const response = await fetch(CONFIG.apiEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          field: fieldName,
          query: query,
          limit: CONFIG.maxSuggestions,
        }),
      });

      const data = await response.json();

      if (data.suggestions && data.suggestions.length > 0) {
        currentSuggestions = data.suggestions;
        showSuggestions(field, data.suggestions);
      } else {
        hideSuggestions();
      }

    } catch (error) {
      console.error('Autocomplete error:', error);
      hideSuggestions();
    }
  }

  /**
   * Show suggestions dropdown
   */
  function showSuggestions(field, suggestions) {
    activeField = field;

    // Remove existing dropdown
    if (suggestionsList) {
      suggestionsList.remove();
    }

    // Create dropdown
    suggestionsList = document.createElement('div');
    suggestionsList.className = 'autocomplete-suggestions';

    suggestions.forEach((suggestion, index) => {
      const item = document.createElement('div');
      item.className = 'autocomplete-item';
      item.innerHTML = `
        <span class="autocomplete-text">${highlightMatch(suggestion.text, getCurrentQuery(field))}</span>
        <span class="autocomplete-frequency" title="Used ${suggestion.frequency} times">×${suggestion.frequency}</span>
      `;

      item.addEventListener('mousedown', (e) => {
        e.preventDefault(); // Prevent blur
        selectSuggestion(suggestion);
      });

      item.addEventListener('mouseenter', () => {
        selectedIndex = index;
        updateSelection();
      });

      suggestionsList.appendChild(item);
    });

    // Position dropdown
    positionDropdown(field, suggestionsList);

    document.body.appendChild(suggestionsList);

    // Select first item by default
    selectedIndex = 0;
    updateSelection();
  }

  /**
   * Hide suggestions dropdown
   */
  function hideSuggestions() {
    if (suggestionsList) {
      suggestionsList.remove();
      suggestionsList = null;
    }
    currentSuggestions = [];
    selectedIndex = -1;
    activeField = null;
  }

  /**
   * Select a suggestion and insert into textarea
   */
  function selectSuggestion(suggestion) {
    if (!activeField) return;

    const field = activeField;
    const value = field.value;
    const cursorPos = field.selectionStart;

    // Get text before and after cursor
    const textBeforeCursor = value.substring(0, cursorPos);
    const textAfterCursor = value.substring(cursorPos);

    // Find where current phrase starts
    const sentences = textBeforeCursor.split(/[.!?]\s*/);
    const lastSentenceStart = textBeforeCursor.lastIndexOf(sentences[sentences.length - 1]);

    // Replace current phrase with suggestion
    const newValue =
      textBeforeCursor.substring(0, lastSentenceStart) +
      suggestion.text +
      '. ' +
      textAfterCursor;

    field.value = newValue;

    // Move cursor to after suggestion
    const newCursorPos = lastSentenceStart + suggestion.text.length + 2;
    field.setSelectionRange(newCursorPos, newCursorPos);

    // Trigger input event for auto-save
    field.dispatchEvent(new Event('input', { bubbles: true }));

    // Hide suggestions
    hideSuggestions();

    // Show success toast
    showToast(`Inserted from history (used ${suggestion.frequency}x before)`);
  }

  /**
   * Update visual selection in dropdown
   */
  function updateSelection() {
    if (!suggestionsList) return;

    const items = suggestionsList.querySelectorAll('.autocomplete-item');
    items.forEach((item, index) => {
      if (index === selectedIndex) {
        item.classList.add('selected');
        item.scrollIntoView({ block: 'nearest' });
      } else {
        item.classList.remove('selected');
      }
    });
  }

  // ============================================================================
  // HELPER FUNCTIONS
  // ============================================================================

  /**
   * Get current query from field
   */
  function getCurrentQuery(field) {
    const value = field.value;
    const cursorPos = field.selectionStart;
    const textBeforeCursor = value.substring(0, cursorPos);
    return extractCurrentPhrase(textBeforeCursor);
  }

  /**
   * Highlight matching part of suggestion
   */
  /**
   * Escape HTML to prevent XSS attacks
   * SECURITY: Sanitize user input before displaying
   */
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function highlightMatch(text, query) {
    if (!query) return escapeHtml(text);

    // SECURITY: Escape HTML first to prevent XSS
    const escapedText = escapeHtml(text);
    const regex = new RegExp(`(${escapeRegex(query)})`, 'gi');
    return escapedText.replace(regex, '<mark>$1</mark>');
  }

  /**
   * Escape regex special characters
   */
  function escapeRegex(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  /**
   * Position dropdown relative to field
   */
  function positionDropdown(field, dropdown) {
    const rect = field.getBoundingClientRect();

    dropdown.style.position = 'fixed';
    dropdown.style.left = `${rect.left}px`;
    dropdown.style.top = `${rect.bottom + 4}px`;
    dropdown.style.width = `${rect.width}px`;
    dropdown.style.maxWidth = '600px';
  }

  /**
   * Show toast notification
   */
  function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'autocomplete-toast';
    toast.innerHTML = `💡 ${message}`;
    document.body.appendChild(toast);

    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 300);
    }, 2500);
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

  // Re-initialize when new content is added (for dynamic forms)
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        if (node.nodeType === 1) { // Element node
          const textareas = node.querySelectorAll ? node.querySelectorAll('textarea') : [];
          textareas.forEach(textarea => {
            if (!textarea.hasAttribute('data-autocomplete-enabled')) {
              textarea.setAttribute('data-autocomplete-enabled', 'true');
              textarea.addEventListener('input', handleInput);
              textarea.addEventListener('keydown', handleKeyDown);
              textarea.addEventListener('blur', handleBlur);
              textarea.addEventListener('focus', handleFocus);
            }
          });
        }
      });
    });
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });

})();
