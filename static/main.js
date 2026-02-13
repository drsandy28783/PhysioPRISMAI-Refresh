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

  showContent(content) {
    this.currentSuggestion = content;

    // Convert plain text to HTML with preserved formatting
    let htmlContent = content
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n/g, '<br>');

    // If content has numbered lists (1. 2. 3.), convert to <ol>
    if (/^\d+\.\s/.test(content)) {
      const items = content.split(/\n(?=\d+\.\s)/)
        .map(item => item.replace(/^\d+\.\s/, '').trim())
        .filter(item => item.length > 0);
      htmlContent = '<ol>' + items.map(item => `<li>${item}</li>`).join('') + '</ol>';
    }

    this.bodyEl.innerHTML = htmlContent.startsWith('<ol>') || htmlContent.startsWith('<p>')
      ? htmlContent
      : `<p>${htmlContent}</p>`;
  },

  showError(message) {
    this.bodyEl.innerHTML = `
      <div style="text-align: center; padding: 20px; color: #d32f2f;">
        <p style="font-size: 18px; margin-bottom: 8px;">⚠️ Error</p>
        <p>${message}</p>
      </div>
    `;
  },

  copyToClipboard() {
    if (!this.currentSuggestion) return;

    navigator.clipboard.writeText(this.currentSuggestion)
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
      AIModal.showContent(data.suggestion);
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
      const res  = await fetch('/api/ai_suggestion/provisional_diagnosis', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      AIModal.showContent(data.suggestion);
    } catch (err) {
      AIModal.showError(err.message);
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
        const { suggestion, error } = await res.json();
        if (error) throw new Error(error);

        console.log(`[AI Response] Received response for field: ${field}`, suggestion?.substring(0, 100) + '...');
        AIModal.showContent(suggestion);
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
      const { suggestion, error } = await res.json();
      if (error) throw new Error(error);
      AIModal.showContent(suggestion);
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
        const { suggestion, error } = await res.json();
        if (error) throw new Error(error);
        AIModal.showContent(suggestion);
      } catch (e) {
        AIModal.showError(e.message);
      } finally {
        btn.disabled = false;
      }
    });
  });
  } // Close if (perspectives-form check)

  // Provisional diagnosis button 🩺
  document.getElementById('gen_perspectives_dx')?.addEventListener('click', async () => {
    // gather all perspective values
    const inputs = {};
    ['knowledge','attribution','expectation','consequences_awareness','locus_of_control','affective_aspect']
      .forEach(name => {
        const el = document.getElementById(name);
        inputs[name] = el ? el.value.trim() : '';
      });

    AIModal.show('Provisional Impressions');

    try {
      // FIX: Use provisional_diagnosis endpoint instead of patient_perspectives
      // to generate diagnosis (not questions)
      const res = await fetch('/api/ai_suggestion/provisional_diagnosis', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({
          previous: {
            ...allPrev,
            perspectives: inputs  // Include the just-entered perspective values
          }
        })
      });
      const { suggestion, error } = await res.json();
      if (error) throw new Error(error);
      AIModal.showContent(suggestion);
    } catch (e) {
      AIModal.showError(e.message);
    }
  });
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
          const { suggestion, error } = await res.json();
          if (error) throw new Error(error);
          AIModal.showContent(suggestion);
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

        const res = await fetch('/api/ai_suggestion/initial_plan_summary', {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({
            patient_id: currentPatientId,
            previous: allPrev,
            inputs: currentAssessments
          })
        });
        const { summary, error } = await res.json();
        if (error) throw new Error(error);
        AIModal.showContent(summary);
      } catch (e) {
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
          const { suggestion, error } = await res.json();
          if (error) throw new Error(error);
          AIModal.showContent(suggestion);
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
      const { suggestion, error } = await res.json();
      if (error) throw new Error(error);
      AIModal.showContent(suggestion);
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

  // Wire up AI buttons (ONLY on clinical flags page)
  if (document.getElementById('flags-form') || document.querySelector('[name="red_flags"]')) {
    document.querySelectorAll('.ai-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const field = btn.dataset.field;
        const fieldEl = document.getElementById(field);
        if (!fieldEl) {
          console.warn(`Field element '${field}' not found`);
          return;
        }
        const text = fieldEl.value.trim();

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
            `/api/ai_suggestion/clinical_flags/${getPatientId() || 'unknown'}/suggest`,
            {
              method: 'POST',
              headers: {'Content-Type':'application/json'},
              body: JSON.stringify({ previous: allPrev, field, text })
            }
          );
          const { suggestions, error } = await res.json();
          if (error) throw new Error(error);
          AIModal.showContent(suggestions);
        } catch (e) {
          AIModal.showError(e.message);
        }
      });
    });
  } // Close if (flags-form check)
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
        const { suggestion, error } = await res.json();
        if (error) throw new Error(error);
        AIModal.showContent(suggestion.trim());
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
      const { diagnosis, error } = await res.json();
      if (error) throw new Error(error);
      AIModal.showContent(diagnosis.trim());
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

          const res = await fetch(
            `/provisional_diagnosis_suggest/${getPatientId()}?field=${field}`,
            {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify(patientData)
            }
          );
          const { suggestion } = await res.json();
          AIModal.showContent(suggestion || 'No suggestion available.');
        } catch (err) {
          console.error(err);
          AIModal.showError('Error fetching suggestion');
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
          patient_goals: input.value
        })
      });
      const { suggestion, error } = await resp.json();
      if (error) {
        AIModal.showError(error);
      } else {
        AIModal.showContent(suggestion);
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
          AIModal.showContent(data.suggestion || 'No suggestion');
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
    AIModal.show('Treatment Summary');

    try {
      const resp = await fetch(
        `/api/ai_suggestion/treatment_plan_summary/${window.patientId}`
      );
      const data = await resp.json();
      if (data.error) {
        AIModal.showError(data.error);
      } else {
        AIModal.showContent(data.summary);
      }
    } catch (err) {
      console.error(err);
      AIModal.showError('Error generating summary');
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
        const resp = await fetch(`/ai/followup_suggestion/${window.patientId}`, {
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
          AIModal.showContent(data.suggestion || 'No suggestion available');
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
