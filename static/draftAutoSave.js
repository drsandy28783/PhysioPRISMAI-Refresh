/**
 * Draft Auto-Save System
 * Automatically saves form progress and restores it when users return
 */

class DraftAutoSave {
  constructor(formType, patientId, options = {}) {
    this.formType = formType;
    this.patientId = patientId;
    this.saveDelay = options.saveDelay || 2000; // 2 seconds debounce
    this.indicator = options.indicator || null; // DOM element for save indicator
    this.onRestore = options.onRestore || null; // Callback after restore
    this.onSave = options.onSave || null; // Callback after save

    this.saveTimer = null;
    this.isSaving = false;
    this.lastSavedData = null;

    // Initialize
    this.init();
  }

  /**
   * Initialize the auto-save system
   */
  async init() {
    // Try to restore draft on load
    await this.restoreDraft();

    // Set up auto-save listeners
    this.setupAutoSave();
  }

  /**
   * Restore saved draft if it exists
   */
  async restoreDraft() {
    try {
      const response = await fetch(`/api/draft/get/${this.patientId}/${this.formType}`);
      const data = await response.json();

      if (data.ok && data.has_draft && data.draft_data) {
        // Show confirmation modal asking user what to do
        const userChoice = await this.showDraftConfirmationModal(data.updated_at);

        if (userChoice === 'continue') {
          // User wants to continue with the draft - restore it
          this.applyDraftToForm(data.draft_data);

          // Show restoration notification
          this.showNotification('Draft restored from ' + this.formatDate(data.updated_at), 'success');

          // Call callback if provided
          if (this.onRestore) {
            this.onRestore(data.draft_data);
          }

          console.log('Draft restored:', data.draft_data);
        } else if (userChoice === 'discard') {
          // User wants to start fresh - delete the draft
          await this.deleteDraft();
          console.log('Draft discarded, starting fresh');
        }
        // If userChoice is null (modal closed), do nothing - leave form empty
      }
    } catch (error) {
      console.error('Error restoring draft:', error);
    }
  }

  /**
   * Apply draft data to form fields
   */
  applyDraftToForm(draftData) {
    Object.entries(draftData).forEach(([fieldName, fieldValue]) => {
      const field = document.querySelector(`[name="${fieldName}"]`);

      if (field) {
        if (field.type === 'checkbox') {
          field.checked = fieldValue;
        } else if (field.type === 'radio') {
          const radioButton = document.querySelector(`[name="${fieldName}"][value="${fieldValue}"]`);
          if (radioButton) radioButton.checked = true;
        } else {
          field.value = fieldValue;
        }
      }
    });
  }

  /**
   * Show modal asking user if they want to continue with draft or start fresh
   * Returns: 'continue', 'discard', or null (if cancelled)
   */
  showDraftConfirmationModal(updatedAt) {
    return new Promise((resolve) => {
      // Create modal overlay
      const overlay = document.createElement('div');
      overlay.className = 'draft-modal-overlay';
      overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 100000;
        animation: fadeIn 0.2s ease;
      `;

      // Create modal
      const modal = document.createElement('div');
      modal.className = 'draft-modal';
      modal.style.cssText = `
        background: white;
        border-radius: 12px;
        padding: 30px;
        max-width: 500px;
        width: 90%;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
        animation: slideUp 0.3s ease;
      `;

      const formattedDate = this.formatDate(updatedAt);

      modal.innerHTML = `
        <div style="text-align: center; margin-bottom: 20px;">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" style="margin: 0 auto;">
            <path d="M9 12L11 14L15 10M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z"
                  stroke="#17a2b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>

        <h2 style="margin: 0 0 15px 0; color: #333; font-size: 24px; text-align: center;">
          Draft Found
        </h2>

        <p style="margin: 0 0 10px 0; color: #666; font-size: 16px; text-align: center;">
          You have unsaved work from <strong>${formattedDate}</strong>.
        </p>

        <p style="margin: 0 0 25px 0; color: #666; font-size: 16px; text-align: center;">
          Would you like to continue where you left off?
        </p>

        <div style="display: flex; gap: 12px; justify-content: center;">
          <button id="draft-continue-btn" style="
            flex: 1;
            padding: 12px 24px;
            background: #17a2b8;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.2s;
          ">
            Continue with Draft
          </button>

          <button id="draft-discard-btn" style="
            flex: 1;
            padding: 12px 24px;
            background: #6c757d;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.2s;
          ">
            Start Fresh
          </button>
        </div>
      `;

      overlay.appendChild(modal);
      document.body.appendChild(overlay);

      // Add hover effects
      const continueBtn = modal.querySelector('#draft-continue-btn');
      const discardBtn = modal.querySelector('#draft-discard-btn');

      continueBtn.addEventListener('mouseenter', () => {
        continueBtn.style.background = '#138496';
      });
      continueBtn.addEventListener('mouseleave', () => {
        continueBtn.style.background = '#17a2b8';
      });

      discardBtn.addEventListener('mouseenter', () => {
        discardBtn.style.background = '#5a6268';
      });
      discardBtn.addEventListener('mouseleave', () => {
        discardBtn.style.background = '#6c757d';
      });

      // Handle button clicks
      continueBtn.addEventListener('click', () => {
        overlay.remove();
        resolve('continue');
      });

      discardBtn.addEventListener('click', () => {
        overlay.remove();
        resolve('discard');
      });

      // Close on overlay click
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
          overlay.remove();
          resolve(null);
        }
      });

      // Close on Escape key
      const escapeHandler = (e) => {
        if (e.key === 'Escape') {
          overlay.remove();
          document.removeEventListener('keydown', escapeHandler);
          resolve(null);
        }
      };
      document.addEventListener('keydown', escapeHandler);
    });
  }

  /**
   * Set up auto-save on form input changes
   */
  setupAutoSave() {
    // Get all form inputs
    const form = document.querySelector('form');
    if (!form) return;

    const inputs = form.querySelectorAll('input, textarea, select');

    inputs.forEach(input => {
      // Skip certain input types
      if (input.type === 'submit' || input.type === 'button' || input.name === 'csrf_token') {
        return;
      }

      // Add event listeners
      input.addEventListener('input', () => this.debouncedSave());
      input.addEventListener('change', () => this.debouncedSave());
    });

    // Save on form submission and delete draft
    form.addEventListener('submit', async (e) => {
      // Save immediately before submit
      await this.saveDraft();

      // Delete draft after successful submission
      // (small delay to ensure form submission completes)
      setTimeout(() => this.deleteDraft(), 1000);
    });
  }

  /**
   * Debounced save - waits for user to stop typing before saving
   */
  debouncedSave() {
    // Clear existing timer
    if (this.saveTimer) {
      clearTimeout(this.saveTimer);
    }

    // Set new timer
    this.saveTimer = setTimeout(() => {
      this.saveDraft();
    }, this.saveDelay);
  }

  /**
   * Collect current form data
   */
  collectFormData() {
    const form = document.querySelector('form');
    if (!form) return {};

    const formData = {};
    const inputs = form.querySelectorAll('input, textarea, select');

    inputs.forEach(input => {
      // Skip certain inputs
      if (input.type === 'submit' || input.type === 'button' || input.name === 'csrf_token') {
        return;
      }

      const name = input.name;
      if (!name) return;

      if (input.type === 'checkbox') {
        formData[name] = input.checked;
      } else if (input.type === 'radio') {
        if (input.checked) {
          formData[name] = input.value;
        }
      } else {
        formData[name] = input.value;
      }
    });

    return formData;
  }

  /**
   * Save draft to server
   */
  async saveDraft() {
    // Prevent concurrent saves
    if (this.isSaving) return;

    try {
      this.isSaving = true;
      this.updateIndicator('saving');

      const formData = this.collectFormData();

      // Check if data has changed
      if (JSON.stringify(formData) === JSON.stringify(this.lastSavedData)) {
        this.updateIndicator('saved');
        this.isSaving = false;
        return;
      }

      const response = await fetch('/api/draft/save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          form_type: this.formType,
          patient_id: this.patientId,
          form_data: formData
        })
      });

      const data = await response.json();

      if (data.ok) {
        this.lastSavedData = formData;
        this.updateIndicator('saved');

        // Call callback if provided
        if (this.onSave) {
          this.onSave(formData);
        }

        console.log('Draft saved successfully');
      } else {
        this.updateIndicator('error');
        console.error('Error saving draft:', data.error);
      }

    } catch (error) {
      this.updateIndicator('error');
      console.error('Error saving draft:', error);
    } finally {
      this.isSaving = false;
    }
  }

  /**
   * Delete draft from server
   */
  async deleteDraft() {
    try {
      const response = await fetch(`/api/draft/delete/${this.patientId}/${this.formType}`, {
        method: 'DELETE'
      });

      const data = await response.json();

      if (data.ok) {
        console.log('Draft deleted successfully');
      }
    } catch (error) {
      console.error('Error deleting draft:', error);
    }
  }

  /**
   * Update save indicator UI
   */
  updateIndicator(status) {
    if (!this.indicator) return;

    // Remove all status classes
    this.indicator.classList.remove('saving', 'saved', 'error');

    // Add current status class
    this.indicator.classList.add(status);

    // Update text
    const statusText = {
      'saving': 'Saving...',
      'saved': 'Saved',
      'error': 'Error saving'
    };

    this.indicator.textContent = statusText[status] || '';

    // Auto-hide after 3 seconds if saved
    if (status === 'saved') {
      setTimeout(() => {
        this.indicator.textContent = '';
      }, 3000);
    }
  }

  /**
   * Show notification banner
   */
  showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `draft-notification draft-notification-${type}`;
    notification.textContent = message;

    notification.style.cssText = `
      position: fixed;
      top: 80px;
      right: 20px;
      background: ${type === 'success' ? '#d4edda' : '#d1ecf1'};
      color: ${type === 'success' ? '#155724' : '#0c5460'};
      padding: 12px 20px;
      border-radius: 8px;
      border-left: 4px solid ${type === 'success' ? '#28a745' : '#17a2b8'};
      box-shadow: 0 2px 8px rgba(0,0,0,0.15);
      z-index: 10000;
      max-width: 400px;
      animation: slideIn 0.3s ease;
    `;

    document.body.appendChild(notification);

    // Auto-remove after 5 seconds
    setTimeout(() => {
      notification.style.animation = 'slideOut 0.3s ease';
      setTimeout(() => notification.remove(), 300);
    }, 5000);
  }

  /**
   * Format date for display
   */
  formatDate(timestamp) {
    if (!timestamp) return '';

    // Handle Firestore timestamp
    if (timestamp._seconds) {
      timestamp = new Date(timestamp._seconds * 1000);
    } else if (typeof timestamp === 'string') {
      timestamp = new Date(timestamp);
    }

    const now = new Date();
    const diff = now - timestamp;

    // Less than 1 minute
    if (diff < 60000) {
      return 'just now';
    }

    // Less than 1 hour
    if (diff < 3600000) {
      const minutes = Math.floor(diff / 60000);
      return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    }

    // Less than 1 day
    if (diff < 86400000) {
      const hours = Math.floor(diff / 3600000);
      return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    }

    // More than 1 day
    const days = Math.floor(diff / 86400000);
    if (days < 7) {
      return `${days} day${days > 1 ? 's' : ''} ago`;
    }

    // Format as date
    return timestamp.toLocaleDateString();
  }

  /**
   * Manually trigger save
   */
  async manualSave() {
    await this.saveDraft();
  }

  /**
   * Discard draft
   */
  async discardDraft() {
    if (confirm('Are you sure you want to discard the saved draft? This cannot be undone.')) {
      await this.deleteDraft();

      // Clear form
      const form = document.querySelector('form');
      if (form) {
        form.reset();
      }

      this.showNotification('Draft discarded', 'success');
    }
  }
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
  @keyframes slideIn {
    from {
      transform: translateX(100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }

  @keyframes slideOut {
    from {
      transform: translateX(0);
      opacity: 1;
    }
    to {
      transform: translateX(100%);
      opacity: 0;
    }
  }

  .draft-save-indicator {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    padding: 6px 12px;
    border-radius: 4px;
    transition: all 0.3s ease;
  }

  .draft-save-indicator.saving {
    background: #fff3cd;
    color: #856404;
  }

  .draft-save-indicator.saving::before {
    content: '⏳';
  }

  .draft-save-indicator.saved {
    background: #d4edda;
    color: #155724;
  }

  .draft-save-indicator.saved::before {
    content: '✓';
  }

  .draft-save-indicator.error {
    background: #f8d7da;
    color: #721c24;
  }

  .draft-save-indicator.error::before {
    content: '⚠️';
  }
`;
document.head.appendChild(style);

// Export for use in pages
if (typeof module !== 'undefined' && module.exports) {
  module.exports = DraftAutoSave;
}
