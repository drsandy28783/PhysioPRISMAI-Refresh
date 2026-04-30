// ================================================================
// Firebase Authentication - Bearer Token Integration
// ================================================================
// This wrapper automatically adds Firebase ID tokens to all API calls
// Import Firebase Auth (assumes Firebase is already initialized in your HTML)

import { getAuth, onAuthStateChanged } from 'https://www.gstatic.com/firebasejs/9.23.0/firebase-auth.js';

// Wait for Firebase Auth to be ready
let firebaseAuthReady = false;
let currentAuthUser = null;

// Listen for auth state changes
const auth = getAuth();
onAuthStateChanged(auth, (user) => {
  firebaseAuthReady = true;
  currentAuthUser = user;
  if (!user) {
    console.warn('Firebase Auth: User not signed in');
  } else {
    // HIPAA-COMPLIANT: Do not log email (PHI identifier)
    console.log('Firebase Auth: User authenticated');
  }
});

// Helper to wait for auth to be ready
async function waitForAuth() {
  return new Promise((resolve) => {
    if (firebaseAuthReady) {
      resolve(currentAuthUser);
      return;
    }

    const unsubscribe = onAuthStateChanged(auth, (user) => {
      unsubscribe();
      firebaseAuthReady = true;
      currentAuthUser = user;
      resolve(user);
    });
  });
}

// Global fetch wrapper to automatically add Firebase ID token
const originalFetch = window.fetch;
window.fetch = async function(url, options) {
  // Only add auth to API endpoints (not for static resources or external URLs)
  const isAPIEndpoint = typeof url === 'string' &&
                        (url.startsWith('/api/ai_suggestion/') ||
                         url.startsWith('/api/') ||
                         url.startsWith('/provisional_diagnosis_suggest/') ||
                         url.startsWith('/ai/followup_suggestion/'));

  if (isAPIEndpoint) {
    try {
      // Wait for Firebase Auth to be ready
      const user = await waitForAuth();

      if (!user) {
        // User not signed in - redirect to login
        alert('Your session has expired. Please sign in again.');
        window.location.href = '/login';
        throw new Error('User not authenticated');
      }

      // Get fresh ID token
      const idToken = await user.getIdToken();

      // Add Authorization header with Bearer token
      options = options || {};
      options.headers = options.headers || {};

      if (typeof options.headers.set === 'function') {
        // Headers is a Headers object
        options.headers.set('Authorization', `Bearer ${idToken}`);
      } else {
        // Headers is a plain object
        options.headers['Authorization'] = `Bearer ${idToken}`;
      }

    } catch (error) {
      console.error('Firebase Auth error:', error);
      throw error;
    }
  }

  // Call original fetch
  return originalFetch.call(this, url, options);
};

// ═══════════════════════════════════════════════════════════════════════
// UTILITY: Get current patient ID (standardized across all pages)
// ═══════════════════════════════════════════════════════════════════════
function getPatientId() {
  return window.currentPatientId || window.patientId || '';
}

// ═══════════════════════════════════════════════════════════════════════
// HIPAA-COMPLIANT: Fetch patient context from server (replaces localStorage)
// ═══════════════════════════════════════════════════════════════════════
let patientContextCache = null;
let patientContextCacheId = null;

async function getPatientContext(patientId) {
  // Use cached data if available for the same patient
  if (patientContextCache && patientContextCacheId === patientId) {
    return patientContextCache;
  }

  try {
    const response = await fetch(`/api/patient/${patientId}/context`);
    if (!response.ok) {
      console.error('Failed to fetch patient context:', response.statusText);
      return {
        ok: false,
        age_sex: '',
        present_history: '',
        past_history: '',
        subjective: {},
        perspectives: {},
        assessments: {},
        smart_goals: {}
      };
    }

    const data = await response.json();

    // Cache the result (in-memory only, cleared on page reload)
    patientContextCache = data;
    patientContextCacheId = patientId;

    return data;
  } catch (error) {
    console.error('Error fetching patient context:', error);
    return {
      ok: false,
      age_sex: '',
      present_history: '',
      past_history: '',
      subjective: {},
      perspectives: {},
      assessments: {},
      smart_goals: {}
    };
  }
}

// Helper to invalidate cache when data is updated
function invalidatePatientContextCache() {
  patientContextCache = null;
  patientContextCacheId = null;
}

// ================================================================
// AI Suggestion Modal Functions
// ================================================================

// SECURITY: HTML escaping function to prevent XSS
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

const AIModal = {
  modal: null,
  titleEl: null,
  bodyEl: null,
  copyBtn: null,
  dismissBtn: null,
  closeBtn: null,
  currentSuggestion: '',

  init() {
    this.modal = document.getElementById('ai-suggestion-modal');
    this.titleEl = document.getElementById('ai-modal-title');
    this.bodyEl = document.getElementById('ai-modal-body');
    this.copyBtn = document.getElementById('ai-modal-copy');
    this.dismissBtn = document.getElementById('ai-modal-dismiss');
    this.closeBtn = document.getElementById('ai-modal-close');

    // Event listeners
    this.dismissBtn?.addEventListener('click', () => this.hide());
    this.closeBtn?.addEventListener('click', () => this.hide());
    this.copyBtn?.addEventListener('click', () => this.copyToClipboard());

    // Close on overlay click
    this.modal?.querySelector('.ai-modal-overlay')?.addEventListener('click', () => this.hide());

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.modal?.classList.contains('active')) {
        this.hide();
      }
    });
  },

  show(title = 'AI Suggestions') {
    if (!this.modal) this.init();
    this.titleEl.textContent = title;
    this.showLoading();
    this.modal.classList.add('active');
    this.modal.style.display = 'flex';
    document.body.style.overflow = 'hidden'; // Prevent background scroll
  },

  hide() {
    this.modal?.classList.remove('active');
    setTimeout(() => {
      if (this.modal) this.modal.style.display = 'none';
    }, 300);
    document.body.style.overflow = ''; // Restore scroll
  },

  showLoading() {
    this.bodyEl.innerHTML = `
      <div class="ai-loading">
        <div class="ai-spinner"></div>
        <p>Generating suggestions...</p>
      </div>
    `;
  },

  showContent(contentOrResponse) {
    // DEBUG: Log full input to diagnose rendering issues
    console.log("🔍 FULL AI MODAL INPUT:", contentOrResponse);
    console.log("🔍 visible_text:", contentOrResponse?.visible_text);
    console.log("🔍 reasoning_text:", contentOrResponse?.reasoning_text);
    console.log("🔍 suggestion:", contentOrResponse?.suggestion);
    console.log("🔍 reasoning:", contentOrResponse?.reasoning);
    console.log("🔍 text:", contentOrResponse?.text);
    console.log("🔍 typeof:", typeof contentOrResponse);

    // Support both old format (string) and new format (object with suggestion + reasoning)
    let visibleText, reasoningText;

    if (typeof contentOrResponse === 'string') {
      // Old format: just a string (backward compatibility)
      visibleText = contentOrResponse;
      reasoningText = null;
    } else if (contentOrResponse && typeof contentOrResponse === 'object') {
      // PRIORITY ORDER: Check visible_text first, then suggestion, diagnosis, summary
      // NEVER use .text if visible_text exists to prevent concatenation
      visibleText = contentOrResponse.visible_text
                 || contentOrResponse.suggestion
                 || contentOrResponse.diagnosis
                 || contentOrResponse.summary
                 || contentOrResponse.text
                 || '';
      reasoningText = contentOrResponse.reasoning_text || contentOrResponse.reasoning || null;
    } else {
      visibleText = '';
      reasoningText = null;
    }

    console.log("✅ FINAL visibleText:", visibleText);
    console.log("✅ FINAL reasoningText:", reasoningText);

    // Store both for copy functionality
    this.currentSuggestion = visibleText;
    this.currentReasoning = reasoningText;

    // Format the visible text
    const formattedVisibleHtml = this._formatTextToHtml(visibleText);

    // Build the content HTML
    let contentHtml = `<div class="ai-suggestion-content">${formattedVisibleHtml}</div>`;

    // Add toggle button and reasoning section if reasoning exists
    if (reasoningText && reasoningText.trim()) {
      const formattedReasoningHtml = this._formatTextToHtml(reasoningText);

      contentHtml += `
        <div class="ai-reasoning-toggle-container" style="margin-top: 20px;">
          <button id="ai-reasoning-toggle-btn" class="ai-reasoning-toggle-btn" style="
            background: #f5f5f5;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 8px 16px;
            font-size: 14px;
            cursor: pointer;
            color: #333;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s;
          ">
            <span class="toggle-icon">▶</span>
            <span class="toggle-text">Show clinical reasoning</span>
          </button>
        </div>
        <div id="ai-reasoning-content" class="ai-reasoning-content" style="
          display: none;
          margin-top: 16px;
          padding: 16px;
          background: #f9f9f9;
          border-left: 4px solid #2196F3;
          border-radius: 4px;
          font-size: 14px;
          line-height: 1.6;
        ">
          ${formattedReasoningHtml}
        </div>
      `;
    }

    this.bodyEl.innerHTML = contentHtml;

    // Wire up toggle button if it exists
    const toggleBtn = document.getElementById('ai-reasoning-toggle-btn');
    const reasoningContent = document.getElementById('ai-reasoning-content');

    if (toggleBtn && reasoningContent) {
      toggleBtn.addEventListener('click', () => {
        const isHidden = reasoningContent.style.display === 'none';

        if (isHidden) {
          // Show reasoning
          reasoningContent.style.display = 'block';
          toggleBtn.querySelector('.toggle-icon').textContent = '▼';
          toggleBtn.querySelector('.toggle-text').textContent = 'Hide clinical reasoning';
          toggleBtn.style.background = '#e3f2fd';
        } else {
          // Hide reasoning
          reasoningContent.style.display = 'none';
          toggleBtn.querySelector('.toggle-icon').textContent = '▶';
          toggleBtn.querySelector('.toggle-text').textContent = 'Show clinical reasoning';
          toggleBtn.style.background = '#f5f5f5';
        }
      });
    }
  },

  _formatTextToHtml(text) {
    if (!text) return '';

    // SECURITY: Escape HTML first to prevent XSS
    const escapedText = escapeHtml(text);

    // Strip markdown headers and internal labels before formatting
    let cleanedText = escapedText
      .replace(/^#{1,4}\s+/gm, '')  // Remove ###, ####, etc. at start of lines
      .replace(/\[CONCISE SUGGESTIONS[^\]]*\]/gi, '')  // Remove internal labels
      .replace(/\[CLINICAL REASONING[^\]]*\]/gi, '');  // Remove internal labels

    // Convert markdown bold (**text**) to HTML <strong>
    cleanedText = cleanedText.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Convert plain text to HTML with preserved formatting
    let htmlContent = cleanedText
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n/g, '<br>');

    // If content has numbered lists (1. 2. 3.), convert to <ol>
    if (/^\d+\.\s/.test(cleanedText)) {
      const items = cleanedText.split(/\n(?=\d+\.\s)/)
        .map(item => item.replace(/^\d+\.\s/, '').trim())
        .filter(item => item.length > 0);
      htmlContent = '<ol>' + items.map(item => `<li>${item}</li>`).join('') + '</ol>';
    }

    return htmlContent.startsWith('<ol>') || htmlContent.startsWith('<p>')
      ? htmlContent
      : `<p>${htmlContent}</p>`;
  },

  showError(message) {
    // SECURITY: Escape error message to prevent XSS
    const escapedMessage = escapeHtml(message);
    this.bodyEl.innerHTML = `
      <div style="text-align: center; padding: 20px; color: #d32f2f;">
        <p style="font-size: 18px; margin-bottom: 8px;">⚠️ Error</p>
        <p>${escapedMessage}</p>
      </div>
    `;
  },

  copyToClipboard() {
    if (!this.currentSuggestion) return;

    // Check if reasoning is currently visible
    const reasoningContent = document.getElementById('ai-reasoning-content');
    const isReasoningVisible = reasoningContent && reasoningContent.style.display !== 'none';

    // Build the text to copy
    let textToCopy = this.currentSuggestion;

    // If reasoning is visible OR if we want to always include it when available, add it
    if (this.currentReasoning && isReasoningVisible) {
      textToCopy += '\n\n' + this.currentReasoning;
    }

    navigator.clipboard.writeText(textToCopy)
      .then(() => {
        const originalText = this.copyBtn.textContent;
        this.copyBtn.textContent = 'Copied!';
        this.copyBtn.style.backgroundColor = '#4caf50';
        setTimeout(() => {
          this.copyBtn.textContent = originalText;
          this.copyBtn.style.backgroundColor = '';
        }, 2000);
      })
      .catch(err => {
        console.error('Failed to copy:', err);
        alert('Failed to copy to clipboard');
      });
  }
};

// Initialize modal when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  AIModal.init();
});

document.addEventListener('DOMContentLoaded', () => {
  const ageSexInput      = document.querySelector('input[name="age_sex"]');
  const presentTextarea  = document.querySelector('textarea[name="present_history"]');
  const pastTextarea     = document.getElementById('past_history');
  const aiResponseDiv    = document.getElementById('ai_response');

  // 1) Suggest past-history questions
  document.getElementById('suggest_questions')?.addEventListener('click', async () => {
    const payload = {
      patient_id:      getPatientId(),  // ✅ FIXED: Added patient_id
      age_sex:         ageSexInput?.value.trim() || '',
      present_history: presentTextarea?.value.trim() || ''
    };

    AIModal.show('Past History Questions');

    try {
      const res  = await fetch('/api/ai_suggestion/past_questions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      AIModal.showContent(data);
    } catch (err) {
      AIModal.showError(err.message);
    }
  });

  // 2) Generate provisional diagnoses
  document.getElementById('gen_diagnosis')?.addEventListener('click', async () => {
    const payload = {
      patient_id: getPatientId(),  // ✅ FIXED: Added patient_id
      previous: {
        age_sex:         ageSexInput?.value.trim() || '',
        present_history: presentTextarea?.value.trim() || '',
        past_history:    pastTextarea?.value.trim() || ''
      }
    };

    AIModal.show('Provisional Diagnosis');

    try {
      // Create abort controller for timeout (60 seconds for longer prompts with past history)
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 second timeout

      const res  = await fetch('/api/ai_suggestion/provisional_diagnosis', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      const data = await res.json();
      if (data.error) throw new Error(data.error);
      AIModal.showContent(data);
    } catch (err) {
      if (err.name === 'AbortError') {
        AIModal.showError('Request timed out. The AI is taking longer than expected. Please try again or simplify your request.');
      } else {
        AIModal.showError(err.message || 'Error generating diagnosis. Please try again.');
      }
    }
  });
});
document.addEventListener('DOMContentLoaded', () => {
  // Only run on subjective examination page
  const subjectiveForm = document.getElementById('subjective-form');
  if (!subjectiveForm) return;

  const ageSexInput     = document.querySelector('[name="age_sex"]');
  const presentInput    = document.querySelector('[name="present_history"]');
  const pastInput       = document.querySelector('[name="past_history"]');
  const fieldBtns       = subjectiveForm.querySelectorAll('.ai-btn[data-field]');
  const genDxBtn        = document.getElementById('gen_subjective_dx');

  fieldBtns.forEach(btn => {
    let isRequesting = false; // Additional flag to prevent race conditions

    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation(); // Prevent other listeners on same element

      // Prevent multiple clicks and race conditions
      if (btn.disabled || isRequesting) {
        console.log('Button click ignored - already processing');
        return;
      }

      isRequesting = true;
      btn.disabled = true;

      const field = btn.dataset.field;

      // Skip if no field specified
      if (!field) {
        btn.disabled = false;
        isRequesting = false;
        return;
      }

      const inputs = {};
      document.querySelectorAll('.input-field')
              .forEach(el => inputs[el.name] = el.value.trim());

      const payload = {
        age_sex:         ageSexInput?.value.trim() || '',
        present_history: presentInput?.value.trim() || '',
        past_history:    pastInput?.value.trim() || '',
        inputs
      };

      // Show modal with field-specific title
      const fieldTitle = field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      AIModal.show(`AI Suggestions: ${fieldTitle}`);

      console.log(`[AI Request] Starting request for field: ${field}`);

      try {
        const res = await fetch(`/api/ai_suggestion/subjective/${field}`, {
          method: 'POST',
          headers: {
            'Content-Type':'application/json'
          },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error);

        console.log(`[AI Response] Received response for field: ${field}`, data.suggestion?.substring(0, 100) + '...');
        AIModal.showContent(data);
      } catch (e) {
        console.error(`[AI Error] Error for field: ${field}`, e);
        AIModal.showError(e.message);
      } finally {
        console.log(`[AI Complete] Request complete for field: ${field}`);
        btn.disabled = false;
        isRequesting = false; // Reset request flag
      }
    });
  });

  genDxBtn?.addEventListener('click', async () => {
    const inputs = {};
    document.querySelectorAll('.input-field')
            .forEach(el => inputs[el.name] = el.value.trim());

    const payload = {
      age_sex:         ageSexInput?.value.trim() || '',
      present_history: presentInput?.value.trim() || '',
      past_history:    pastInput?.value.trim() || '',
      inputs
    };

    AIModal.show('Subjective Diagnosis');

    try {
      const res = await fetch('/api/ai_suggestion/subjective_diagnosis', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.error) throw new Error(error);
      AIModal.showContent(data);
    } catch (e) {
      AIModal.showError(e.message);
    }
  });
});
// ——— AI on Patient Perspectives screen ———
// Only run this block if we're on the Perspectives page
if (document.getElementById('perspectives-form')) {
  // Get current patient ID from the page
  const currentPatientId = window.currentPatientId || '';

  // HIPAA-COMPLIANT: NO localStorage for PHI - server fetches all data

  // Attach click listeners to each 🧠 button (ONLY on perspectives page)
  if (document.getElementById('perspectives-form')) {
    document.querySelectorAll('.ai-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.preventDefault();
        e.stopPropagation();

        // Prevent multiple clicks
        if (btn.disabled) return;
        btn.disabled = true;

        const field = btn.dataset.field;
        const fieldEl = document.getElementById(field);
      if (!fieldEl) {
        console.warn(`Field element '${field}' not found`);
        btn.disabled = false;
        return;
      }
      const value = fieldEl.value.trim();

      // Collect currently entered perspectives data (not from localStorage)
      const currentInputs = {};
      ['knowledge', 'knowledge_entry', 'attribution', 'attribution_entry',
       'expectation', 'expectation_entry', 'consequences_awareness', 'consequences_awareness_entry',
       'locus_of_control', 'locus_of_control_entry', 'affective_aspect', 'affective_aspect_entry'].forEach(name => {
        const el = document.getElementById(name);
        if (el) currentInputs[name] = el.value.trim();
      });

      // Show modal with field-specific title
      const fieldTitle = field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      AIModal.show(`AI Suggestions: ${fieldTitle}`);

      try {
        // HIPAA-COMPLIANT: Send only patient_id and current form inputs
        // Server fetches all historical data from database
        const res = await fetch(`/api/ai_suggestion/perspectives/${field}`, {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({
            patient_id: currentPatientId,
            inputs: currentInputs
          })
        });
        const data = await res.json();
        if (data.error) throw new Error(error);
        AIModal.showContent(data);
      } catch (e) {
        AIModal.showError(e.message);
      } finally {
        btn.disabled = false;
      }
    });
  });
  } // Close if (perspectives-form check)
}
  // ——— AI on Initial Plan screen ———
  if (document.getElementById('initial-plan-form')) {
    // Get patient-specific ID from page
    const currentPatientId = window.currentPatientId || '';

    // HIPAA-COMPLIANT: NO localStorage for PHI - server fetches all data

    // Per-field test suggestions (ONLY on initial plan page)
    if (document.getElementById('initial-plan-form')) {
      document.querySelectorAll('.ai-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
          e.preventDefault();
          e.stopPropagation();

          // Prevent multiple clicks
          if (btn.disabled) return;
          btn.disabled = true;

          const field     = btn.dataset.field;                   // e.g. 'active_movements'
          const fieldEl = document.getElementById(field);
        if (!fieldEl) {
          console.warn(`Field element '${field}' not found`);
          btn.disabled = false;
          return;
        }
        const selection = fieldEl.value.trim();

        // Show modal with field-specific title
        const fieldTitle = field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        AIModal.show(`AI Suggestions: ${fieldTitle}`);

        try {
          // HIPAA-COMPLIANT: Send only patient_id and current selection
          // Server fetches all historical data from database
          const res = await fetch(`/api/ai_suggestion/initial_plan/${field}`, {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({
              patient_id: currentPatientId,
              selection: selection
            })
          });
          const data = await res.json();
          if (data.error) throw new Error(error);
          AIModal.showContent(data);
        } catch (err) {
          AIModal.showError(err.message);
        } finally {
          btn.disabled = false;
        }
      });
    });
    } // Close if (initial-plan-form check)

    // Full summary + provisional dx
    document.getElementById('gen_initial_summary')?.addEventListener('click', async () => {
      AIModal.show('Assessment Summary & Provisional Dx');

      try {
        // HIPAA-COMPLIANT: Fetch patient context from server (not localStorage)
        const context = await getPatientContext(currentPatientId);

        // Collect current form data for assessments
        const currentAssessments = {};
        ['active_movements','passive_movements','passive_over_pressure',
         'resisted_movements','combined_movements','special_tests','neurodynamic']
          .forEach(f => {
            const fieldEl = document.getElementById(f);
            const detailsEl = document.getElementById(f + '_details');
            currentAssessments[f] = {
              choice: fieldEl?.value || '',
              details: detailsEl?.value?.trim() || ''
            };
          });

        const allPrev = {
          age_sex: context.age_sex || '',
          present_history: context.present_history || '',
          past_history: context.past_history || '',
          subjective: context.subjective || {},
          perspectives: context.perspectives || {}
        };

        const requestPayload = {
          patient_id: currentPatientId,
          previous: allPrev,
          inputs: currentAssessments
        };

        console.log('[Initial Plan Summary] Request payload:', requestPayload);

        const res = await fetch('/api/ai_suggestion/initial_plan_summary', {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify(requestPayload)
        });

        console.log('[Initial Plan Summary] Response status:', res.status);

        const responseData = await res.json();
        console.log('[Initial Plan Summary] Response data:', responseData);

        const { summary, error } = responseData;
        if (error) throw new Error(error);
        if (!summary || summary.trim() === '') {
          throw new Error('No summary generated. Please ensure assessment fields are filled in.');
        }
        AIModal.showContent(responseData);
      } catch (e) {
        console.error('[Initial Plan Summary] Error:', e);
        AIModal.showError(e.message);
      }
    });
  }


// ——— AI on Pathophysiological Mechanism screen ———
if (document.querySelector('select#possible_source')) {
  const currentPatientId = window.currentPatientId || '';

  // ONLY attach on pathophysiology page
  if (document.getElementById('patho-form') || document.querySelector('[name="possible_source"]')) {
    document.querySelectorAll('.ai-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.preventDefault();
        e.stopPropagation();

        // Prevent multiple clicks
        if (btn.disabled) return;
        btn.disabled = true;

        const field = btn.dataset.field; // "possible_source"
        const fieldEl = document.getElementById(field);
        if (!fieldEl) {
          console.warn(`Field element '${field}' not found`);
          btn.disabled = false;
          return;
        }
        const selection = fieldEl.value.trim();

        // Show modal with field-specific title
        const fieldTitle = field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        AIModal.show(`AI Suggestions: ${fieldTitle}`);

        try {
          // HIPAA-COMPLIANT: Fetch patient context from server (not localStorage)
          const context = await getPatientContext(currentPatientId);

          const allPrev = {
            age_sex: context.age_sex || '',
            present_history: context.present_history || '',
            past_history: context.past_history || '',
            subjective: context.subjective || {},
            perspectives: context.perspectives || {},
            assessments: context.assessments || {}
          };

          const res = await fetch('/api/ai_suggestion/patho/possible_source', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ patient_id: currentPatientId, previous: allPrev, selection })
          });
          const data = await res.json();
          if (data.error) throw new Error(error);
          AIModal.showContent(data);
        } catch (e) {
          AIModal.showError(e.message);
        } finally {
          btn.disabled = false;
        }
      });
    });
  } // Close if (patho-form check)
}
// ——— AI on Chronic Disease Factors screen ———
if (document.getElementById('specific_factors')) {
  const currentPatientId = window.currentPatientId || '';

  // Chronic factors follow-ups
  document.querySelector('.ai-btn')?.addEventListener('click', async e => {
    e.preventDefault();
    e.stopPropagation();

    const btn = e.currentTarget;

    // Prevent multiple clicks
    if (btn.disabled) return;
    btn.disabled = true;

    const field = btn.dataset.field; // "specific_factors"
    const fieldEl = document.getElementById(field);
    if (!fieldEl) {
      console.warn(`Field element '${field}' not found`);
      btn.disabled = false;
      return;
    }
    const text = fieldEl.value.trim();
    // gather checked causes
    const causes = Array.from(document.querySelectorAll('input[name="maintenance_causes"]:checked'))
                      .map(cb => cb.value);

    // Show modal
    const fieldTitle = field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    AIModal.show(`AI Suggestions: ${fieldTitle}`);

    try {
      // HIPAA-COMPLIANT: Fetch patient context from server (not localStorage)
      const context = await getPatientContext(currentPatientId);

      const allPrev = {
        age_sex: context.age_sex || '',
        present_history: context.present_history || '',
        past_history: context.past_history || '',
        subjective: context.subjective || {},
        perspectives: context.perspectives || {},
        assessments: context.assessments || {}
      };

      const res = await fetch('/api/ai_suggestion/chronic/specific_factors', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({
          patient_id: currentPatientId,
          previous: allPrev,
          input: text,
          causes
        })
      });
      const data = await res.json();
      if (data.error) throw new Error(error);
      AIModal.showContent(data);
    } catch (err) {
      AIModal.showError(err.message);
    } finally {
      btn.disabled = false;
    }
  });
}
// ——— AI on Clinical Flags screen ———
if (document.getElementById('clinical-flags-form')) {
  const currentPatientId = window.currentPatientId || '';

  // HIPAA-COMPLIANT: Fetch patient context from server on page load for highlights
  (async () => {
    const context = await getPatientContext(currentPatientId);

    // On page load: highlight relevant flags based on server data
    const highlights = [];
    if (context.subjective && context.subjective.pain_irritability === 'Present') {
      highlights.push('yellow_flags');
    }
    if (context.assessments && context.assessments.special_tests === 'Absolutely Contraindicated') {
      highlights.push('black_flags');
    }
    highlights.forEach(id => {
      const el = document.getElementById(id + '_block');
      if (el) el.classList.add('highlight');
    });
  })();

  // Single AI button for all flags suggestions
  document.getElementById('gen_flags_suggestions')?.addEventListener('click', async () => {
    AIModal.show('AI Suggestions for Clinical Flags');

    try {
      // HIPAA-COMPLIANT: Fetch patient context from server (not localStorage)
      const context = await getPatientContext(currentPatientId);

      // Collect all flag field values
      const flagFields = ['red_flags', 'orange_flags', 'yellow_flags', 'black_flags', 'blue_flags'];
      const flagsData = {};
      flagFields.forEach(field => {
        const fieldEl = document.getElementById(field);
        if (fieldEl) {
          flagsData[field] = fieldEl.value.trim();
        }
      });

      const allPrev = {
        age_sex: context.age_sex || '',
        present_history: context.present_history || '',
        past_history: context.past_history || '',
        subjective: context.subjective || {},
        perspectives: context.perspectives || {},
        assessments: context.assessments || {}
      };

      const res = await fetch(
        `/api/ai_suggestion/clinical_flags_all/${getPatientId() || 'unknown'}`,
        {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({ previous: allPrev, flags: flagsData })
        }
      );
      const data = await res.json();
      if (data.error) throw new Error(error);
      AIModal.showContent(data);
    } catch (e) {
      AIModal.showError(e.message);
    }
  });
}
// ——— AI on Combined Risk Factors & Clinical Flags screen ———
if (document.getElementById('risk-factors-form')) {
  const currentPatientId = window.currentPatientId || '';

  // Single AI button for all flags suggestions
  document.getElementById('gen_flags_suggestions')?.addEventListener('click', async () => {
    AIModal.show('AI Suggestions for Clinical Flags');

    try {
      // HIPAA-COMPLIANT: Fetch patient context from server (not localStorage)
      const context = await getPatientContext(currentPatientId);

      // Collect all flag field values
      const flagFields = ['red_flags', 'orange_flags', 'yellow_flags', 'black_flags', 'blue_flags'];
      const flagsData = {};
      flagFields.forEach(field => {
        const fieldEl = document.getElementById(field);
        if (fieldEl) {
          flagsData[field] = fieldEl.value.trim();
        }
      });

      const allPrev = {
        age_sex: context.age_sex || '',
        present_history: context.present_history || '',
        past_history: context.past_history || '',
        subjective: context.subjective || {},
        perspectives: context.perspectives || {},
        assessments: context.assessments || {}
      };

      const res = await fetch(
        `/api/ai_suggestion/clinical_flags_all/${getPatientId() || 'unknown'}`,
        {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({ previous: allPrev, flags: flagsData })
        }
      );
      const data = await res.json();
      if (data.error) throw new Error(error);
      AIModal.showContent(data);
    } catch (e) {
      AIModal.showError(e.message);
    }
  });
}
// ——— AI on Objective Assessment screen ———
if (document.getElementById('objective-assessment-form')) {
  const currentPatientId = window.currentPatientId || '';

  // per-field AI helpers
  document.querySelectorAll('#objective-assessment-form .ai-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const field = btn.dataset.field; // "plan"
      const fieldEl = document.getElementById(field);
      if (!fieldEl) {
        console.warn(`Field element '${field}' not found`);
        return;
      }

      // Show modal
      const fieldTitle = field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      AIModal.show(`AI Suggestions: ${fieldTitle}`);

      try {
        // HIPAA-COMPLIANT: Fetch patient context from server (not localStorage)
        const context = await getPatientContext(currentPatientId);

        const allPrev = {
          age_sex: context.age_sex || '',
          present_history: context.present_history || '',
          past_history: context.past_history || '',
          subjective: context.subjective || {},
          perspectives: context.perspectives || {},
          assessments: context.assessments || {}
        };

        const res = await fetch(
          `/api/ai_suggestion/objective_assessment/${field}`,
          {
            method: 'POST',
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify({
              patient_id: currentPatientId,
              previous: allPrev,
              value: fieldEl.value
            })
          }
        );
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        AIModal.showContent(data);
      } catch (err) {
        AIModal.showError(err.message);
        console.error(err);
      }
    });
  });

  // provisional DX button
  document.getElementById('gen_provisional_dx')?.addEventListener('click', async () => {
    try {
      AIModal.show('Provisional Diagnosis');

      // HIPAA-COMPLIANT: Fetch patient context from server (not localStorage)
      const context = await getPatientContext(currentPatientId);

      const allPrev = {
        age_sex: context.age_sex || '',
        present_history: context.present_history || '',
        past_history: context.past_history || '',
        subjective: context.subjective || {},
        perspectives: context.perspectives || {},
        assessments: context.assessments || {}
      };

      // Include current plan details if available
      const planDetailsEl = document.getElementById('plan_details');
      if (planDetailsEl && planDetailsEl.value.trim()) {
        allPrev.plan_details = planDetailsEl.value.trim();
      }

      const res = await fetch(
        `/api/ai_suggestion/provisional_diagnosis`,
        {
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({
            patient_id: currentPatientId,
            previous: allPrev
          })
        }
      );
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      AIModal.showContent(data);
    } catch (err) {
      AIModal.showError(err.message);
      console.error(err);
    }
  });
}
// ——— Provisional Diagnosis AI Suggestions ———
document.addEventListener('DOMContentLoaded', () => {
  // ONLY attach on provisional diagnosis page
  if (document.getElementById('provisional-diagnosis-form') || document.querySelector('[name="provisional_diagnosis"]')) {
    document.querySelectorAll('.ai-btn[data-field]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const field = btn.dataset.field;

        // Show modal
        const fieldTitle = field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        AIModal.show(`AI Suggestions: ${fieldTitle}`);

        try {
          const currentPatientId = window.currentPatientId || '';

          // HIPAA-COMPLIANT: Fetch patient context from server (not localStorage)
          const context = await getPatientContext(currentPatientId);

          const patientData = {
            patient_id: currentPatientId,
            previous: {
              age_sex: context.age_sex || '',
              present_history: context.present_history || '',
              past_history: context.past_history || '',
              subjective: context.subjective || {},
              perspectives: context.perspectives || {},
              assessments: context.assessments || {}
            }
          };

          // Create abort controller for timeout
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 second timeout

          const res = await fetch(
            `/provisional_diagnosis_suggest/${getPatientId()}?field=${field}`,
            {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify(patientData),
              signal: controller.signal
            }
          );

          clearTimeout(timeoutId);

          const data = await res.json();
          AIModal.showContent(data.suggestion ? data : 'No suggestion available.');
        } catch (err) {
          console.error(err);
          if (err.name === 'AbortError') {
            AIModal.showError('Request timed out. The AI is taking longer than expected. Please try again or simplify your request.');
          } else {
            AIModal.showError('Error fetching suggestion. Please try again.');
          }
        }
      });
    });
  } // Close if (provisional-diagnosis-form check)
});

// SMART Goals suggestions
document.querySelectorAll('.ai-btn[data-screen="smart_goals"]').forEach(btn => {
  btn.addEventListener('click', async () => {
    const field = btn.dataset.field; // e.g. "patient_goal"
    const input = document.getElementById(field);

    // Skip if input doesn't exist on this page
    if (!input) {
      console.warn(`Required elements for '${field}' not found on this page`);
      return;
    }

    // Show modal
    const fieldTitle = field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    AIModal.show(`AI Suggestions: ${fieldTitle}`);

    try {
      const currentPatientId = window.currentPatientId || '';

      // HIPAA-COMPLIANT: Fetch patient context from server (not localStorage)
      const context = await getPatientContext(currentPatientId);

      const resp = await fetch(`/api/ai_suggestion/smart_goals/${field}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          patient_id: getPatientId(),
          previous: {
            age_sex: context.age_sex || '',
            present_history: context.present_history || '',
            past_history: context.past_history || '',
            subjective: context.subjective || {},
            perspectives: context.perspectives || {},
            assessments: context.assessments || {}
          },
          input: input.value
        })
      });
      const data = await resp.json();
      if (data.error) {
        AIModal.showError(error);
      } else {
        AIModal.showContent(data);
      }
    } catch (err) {
      console.error(err);
      AIModal.showError('Error fetching suggestion');
    }
  });
});
// ----------------------------------------------------------------
// Treatment Plan screen:
// ----------------------------------------------------------------
// ONLY attach on treatment plan page
if (document.getElementById('treatment-plan-form') || document.querySelector('[name="treatment_plan"]')) {
  document.querySelectorAll('.ai-btn[data-field]').forEach(btn => {
    // Only attach to buttons with data-field attribute (treatment_plan, etc.)
    btn.addEventListener('click', async () => {
      const field = btn.dataset.field;
      const inputField = document.getElementById(field);

      // Skip if input field doesn't exist on this page
      if (!inputField) {
        console.warn(`Input field '${field}' not found on this page`);
        return;
      }

      // Show modal
      const fieldTitle = field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      AIModal.show(`AI Suggestions: ${fieldTitle}`);

      try {
        const currentPatientId = window.currentPatientId || '';

        // HIPAA-COMPLIANT: Fetch patient context from server (not localStorage)
        const context = await getPatientContext(currentPatientId);

        const resp = await fetch(
          `/api/ai_suggestion/treatment_plan/${field}`,
          {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({
              patient_id: getPatientId(),
              previous: {
                age_sex: context.age_sex || '',
                present_history: context.present_history || '',
                past_history: context.past_history || '',
                provisional_diagnosis: context.provisional_diagnosis || '',
                subjective: context.subjective || {},
                perspectives: context.perspectives || {},
                assessments: context.assessments || {},
                smart_goals: context.smart_goals || {}
              },
              input: inputField.value
            })
          }
        );
        const data = await resp.json();
        if (data.error) {
          AIModal.showError(data.error);
        } else {
          AIModal.showContent(data.suggestion ? data : 'No suggestion');
        }
      } catch (err) {
        AIModal.showError('Error fetching suggestion');
        console.error(err);
      }
    });
  });
} // Close if (treatment-plan-form check)

// Generate full treatment summary:
const genBtn = document.getElementById('gen_summary');
if (genBtn) {
  genBtn.addEventListener('click', async () => {
    console.log('[Treatment Summary] Button clicked');
    AIModal.show('Treatment Summary');

    try {
      const url = `/api/ai_suggestion/treatment_plan_summary/${getPatientId()}`;
      console.log('[Treatment Summary] Fetching:', url);

      const resp = await fetch(url);
      console.log('[Treatment Summary] Response status:', resp.status);
      console.log('[Treatment Summary] Response headers:', [...resp.headers.entries()]);

      const data = await resp.json();
      console.log('[Treatment Summary] Response data:', data);

      if (data.error) {
        console.error('[Treatment Summary] Error from server:', data.error);
        AIModal.showError(data.error);
      } else if (!data.summary || data.summary.trim() === '') {
        console.error('[Treatment Summary] Empty summary received');
        AIModal.showError('No summary generated. Please ensure all assessment sections are completed and saved.');
      } else {
        console.log('[Treatment Summary] Summary received, length:', data.summary.length);
        AIModal.showContent(data);
      }
    } catch (err) {
      console.error('[Treatment Summary] Exception caught:', err);
      console.error('[Treatment Summary] Error stack:', err.stack);
      AIModal.showError('Error generating summary: ' + err.message);
    }
  });
}

// Follow-up session AI suggestions (already correctly scoped)
if (document.getElementById('followup-form')) {
  document.querySelectorAll('.ai-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const textarea = btn.previousElementSibling;
      const field    = textarea?.id || 'followup';

      // Show modal
      const fieldTitle = field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      AIModal.show(`AI Suggestions: ${fieldTitle}`);

      try {
        const resp = await fetch(`/ai/followup_suggestion/${getPatientId()}`, {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({
            session_number: document.querySelector('input[name="session_number"]')?.value || '',
            session_date:   document.querySelector('input[name="session_date"]')?.value || '',
            grade:          document.querySelector('select[name="grade"]')?.value || '',
            perception:     document.querySelector('select[name="belief_treatment"]')?.value || '',
            feedback:       document.querySelector('textarea[name="belief_feedback"]')?.value || ''
          })
        });
        const data = await resp.json();
        if (data.error) {
          AIModal.showError(data.error);
        } else {
          AIModal.showContent(data.suggestion ? data : 'No suggestion available');
        }
      } catch(err) {
        console.error(err);
        AIModal.showError('Error fetching suggestion');
      }
    });
  });
}


// -------------------------------------------------------------
// Logout redirect handler (CSP-safe, externalized)
// -------------------------------------------------------------
if (window.location.pathname === '/logout') {
  (async function() {
    try {
      // Step 1: Sign out from Firebase Auth FIRST (important for persistence)
      console.log('[Logout] Signing out from Firebase Auth...');
      try {
        const { signOut } = await import('https://www.gstatic.com/firebasejs/9.23.0/firebase-auth.js');
        const auth = getAuth();
        await signOut(auth);
        console.log('[Logout] Firebase Auth sign out successful.');
      } catch (firebaseError) {
        console.warn('[Logout] Firebase sign out failed (non-critical):', firebaseError);
      }

      // Step 2: Clear all client-side storage
      localStorage.clear();
      sessionStorage.clear();

      console.log('[Logout] Cleared local and session storage.');

      // Step 3: Redirect to login after short delay
      setTimeout(() => {
        window.location.href = '/login';
      }, 1000);
    } catch (err) {
      console.error('[Logout] Error during logout cleanup:', err);
      // fallback redirect immediately
      window.location.href = '/login';
    }
  })();
}

// ── Auto-grow textareas ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  function growTextarea(el) {
    el.style.height = 'auto';
    el.style.height = el.scrollHeight + 'px';
  }
  document.querySelectorAll('textarea.input-field').forEach(function (ta) {
    ta.addEventListener('input', function () { growTextarea(ta); });
    ta.addEventListener('paste', function () {
      setTimeout(function () { growTextarea(ta); }, 0);
    });
    if (ta.value) { growTextarea(ta); }
  });
});
