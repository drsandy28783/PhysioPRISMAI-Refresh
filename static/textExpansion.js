/**
 * PhysioPRISM - Medical Text Expansion System
 * ============================================
 *
 * Allows quick typing of medical terms using shortcuts.
 * Type // followed by abbreviation to expand.
 *
 * Examples:
 *   //bp → blood pressure
 *   //rom → range of motion
 *   //nwb → non-weight bearing
 *
 * Usage: Automatically enabled on all textareas
 */

(function() {
  'use strict';

  // ============================================================================
  // MEDICAL ABBREVIATIONS DICTIONARY
  // ============================================================================

  const MEDICAL_EXPANSIONS = {
    // Vital Signs & Measurements
    'bp': 'blood pressure',
    'hr': 'heart rate',
    'rr': 'respiratory rate',
    'temp': 'temperature',
    'spo2': 'oxygen saturation',
    'bmi': 'body mass index',
    'wt': 'weight',
    'ht': 'height',

    // Range of Motion
    'rom': 'range of motion',
    'arom': 'active range of motion',
    'prom': 'passive range of motion',
    'flex': 'flexion',
    'ext': 'extension',
    'abd': 'abduction',
    'add': 'adduction',
    'ir': 'internal rotation',
    'er': 'external rotation',
    'df': 'dorsiflexion',
    'pf': 'plantarflexion',

    // Pain & Symptoms
    'vas': 'Visual Analog Scale',
    'nprs': 'Numeric Pain Rating Scale',
    'lbp': 'lower back pain',
    'ubp': 'upper back pain',
    'neckpain': 'neck pain',
    'shoulderpain': 'shoulder pain',
    'kneepain': 'knee pain',
    'radicular': 'radicular pain',
    'neuropathic': 'neuropathic pain',
    'acute': 'acute pain',
    'chronic': 'chronic pain',

    // Weight Bearing Status
    'wb': 'weight bearing',
    'fwb': 'full weight bearing',
    'pwb': 'partial weight bearing',
    'nwb': 'non-weight bearing',
    'ttwb': 'toe touch weight bearing',
    'wbat': 'weight bearing as tolerated',

    // Strength & Muscle
    'mmt': 'manual muscle testing',
    'str': 'strength',
    'weakness': 'muscle weakness',
    'atrophy': 'muscle atrophy',
    'spasm': 'muscle spasm',
    'guarding': 'muscle guarding',
    'tightness': 'muscle tightness',

    // Functional Status
    'adl': 'activities of daily living',
    'iadl': 'instrumental activities of daily living',
    'amb': 'ambulation',
    'transfers': 'transfer ability',
    'mobility': 'functional mobility',
    'balance': 'balance',
    'gait': 'gait pattern',
    'stairs': 'stair negotiation',

    // Treatment & Modalities
    'tens': 'Transcutaneous Electrical Nerve Stimulation',
    'us': 'ultrasound',
    'ift': 'Interferential Therapy',
    'swd': 'Short Wave Diathermy',
    'mwm': 'Mobilization with Movement',
    'pnf': 'Proprioceptive Neuromuscular Facilitation',
    'met': 'Muscle Energy Technique',
    'stt': 'Soft Tissue Therapy',
    'mfr': 'Myofascial Release',
    'heat': 'heat therapy',
    'ice': 'ice therapy/cryotherapy',
    'hydro': 'hydrotherapy',

    // Exercises
    'ex': 'exercises',
    'strex': 'strengthening exercises',
    'stretchex': 'stretching exercises',
    'romex': 'range of motion exercises',
    'stabex': 'stabilization exercises',
    'balanceex': 'balance exercises',
    'proprioex': 'proprioceptive exercises',
    'aerobicex': 'aerobic exercises',
    'resistex': 'resistance exercises',

    // Clinical Tests
    'slr': 'Straight Leg Raise',
    'fadir': 'FADIR test (hip)',
    'faber': 'FABER test (hip)',
    'thomas': 'Thomas test',
    'ober': "Ober's test",
    'neer': "Neer's test",
    'hawkins': "Hawkins-Kennedy test",
    'empty': 'Empty Can test',
    'drop': 'Drop Arm test',
    'apprehension': 'Apprehension test',
    'drawer': 'Drawer test',
    'lachman': "Lachman's test",
    'mcmurray': "McMurray's test",
    'valgus': 'Valgus stress test',
    'varus': 'Varus stress test',

    // Anatomical Regions
    'c-spine': 'cervical spine',
    't-spine': 'thoracic spine',
    'l-spine': 'lumbar spine',
    'si': 'sacroiliac joint',
    'gle': 'glenohumeral joint',
    'ac': 'acromioclavicular joint',
    'mtp': 'metatarsophalangeal joint',
    'pip': 'proximal interphalangeal joint',
    'dip': 'distal interphalangeal joint',

    // Directions & Positions
    'bilat': 'bilateral',
    'unilat': 'unilateral',
    'lt': 'left',
    'rt': 'right',
    'ant': 'anterior',
    'post': 'posterior',
    'med': 'medial',
    'lat': 'lateral',
    'prox': 'proximal',
    'dist': 'distal',
    'sup': 'superior',
    'inf': 'inferior',

    // Medical Conditions
    'oa': 'osteoarthritis',
    'ra': 'rheumatoid arthritis',
    'dx': 'diagnosis',
    'hx': 'history',
    'sx': 'symptoms',
    'tx': 'treatment',
    'rx': 'prescription',
    'pt': 'patient',
    'fx': 'fracture',
    'disloc': 'dislocation',
    'sprain': 'ligament sprain',
    'strain': 'muscle strain',
    'tendinitis': 'tendinitis',
    'bursitis': 'bursitis',
    'impingement': 'impingement syndrome',
    'radiculopathy': 'radiculopathy',
    'stenosis': 'spinal stenosis',
    'herniation': 'disc herniation',
    'spondylosis': 'spondylosis',
    'scoliosis': 'scoliosis',

    // Assessment & Outcome
    'indep': 'independent',
    'mod': 'moderate',
    'min': 'minimal',
    'max': 'maximal',
    'assist': 'assistance',
    'improved': 'improved',
    'worsened': 'worsened',
    'stable': 'stable condition',
    'progressing': 'progressing well',
    'compliant': 'compliant with treatment',
    'noncompliant': 'non-compliant with treatment',

    // Time & Frequency
    'bid': 'twice daily',
    'tid': 'three times daily',
    'qid': 'four times daily',
    'prn': 'as needed',
    'daily': 'once daily',
    'wk': 'week',
    'mo': 'month',
    'yr': 'year',
    'x': 'times',

    // Common Phrases
    'nka': 'no known allergies',
    'nkda': 'no known drug allergies',
    'wnl': 'within normal limits',
    'unremarkable': 'unremarkable',
    'negative': 'negative',
    'positive': 'positive',
    'denies': 'patient denies',
    'reports': 'patient reports',
    'complains': 'patient complains of',
    'presents': 'patient presents with',
    'demonstrates': 'patient demonstrates',

    // Consent & Documentation
    'informed': 'informed consent obtained',
    'verbal': 'verbal consent obtained',
    'written': 'written consent obtained',
    'discussed': 'treatment plan discussed with patient',
    'educated': 'patient educated regarding',
    'instructions': 'home exercise instructions provided',
    'precautions': 'precautions explained',
    'goals': 'treatment goals established',
  };

  // ============================================================================
  // EXPANSION ENGINE
  // ============================================================================

  let activeTextarea = null;
  let currentTrigger = '';

  /**
   * Initialize text expansion on all textareas
   */
  function init() {
    // Find all textareas and inputs
    const fields = document.querySelectorAll('textarea, input[type="text"]');

    fields.forEach(field => {
      // Skip if already initialized
      if (field.hasAttribute('data-text-expansion-enabled')) return;

      field.setAttribute('data-text-expansion-enabled', 'true');
      field.addEventListener('input', handleInput);
      field.addEventListener('keydown', handleKeyDown);
    });

    console.log(`📝 Text expansion enabled on ${fields.length} fields`);
  }

  /**
   * Handle input events to detect // trigger
   */
  function handleInput(e) {
    const field = e.target;
    const value = field.value;
    const cursorPos = field.selectionStart;

    // Get text before cursor
    const textBeforeCursor = value.substring(0, cursorPos);

    // Check if we just typed //
    if (textBeforeCursor.endsWith('//')) {
      activeTextarea = field;
      currentTrigger = '';
      showExpansionHint(field);
      return;
    }

    // If we have an active trigger, accumulate letters
    if (activeTextarea === field && textBeforeCursor.includes('//')) {
      const lastSlashPos = textBeforeCursor.lastIndexOf('//');
      currentTrigger = textBeforeCursor.substring(lastSlashPos + 2);

      // Check if trigger matches any abbreviation
      const expansion = MEDICAL_EXPANSIONS[currentTrigger.toLowerCase()];
      if (expansion) {
        showExpansionPreview(field, currentTrigger, expansion);
      } else {
        hideExpansionPreview();
      }
    }
  }

  /**
   * Handle keydown for Tab or Space to trigger expansion
   */
  function handleKeyDown(e) {
    const field = e.target;

    // Check for Tab or Space when we have a trigger
    if ((e.key === 'Tab' || e.key === ' ') && activeTextarea === field && currentTrigger) {
      const expansion = MEDICAL_EXPANSIONS[currentTrigger.toLowerCase()];

      if (expansion) {
        e.preventDefault();
        expandAbbreviation(field, currentTrigger, expansion);
        return;
      }
    }

    // Reset on Escape
    if (e.key === 'Escape') {
      resetExpansion();
    }
  }

  /**
   * Expand the abbreviation
   */
  function expandAbbreviation(field, trigger, expansion) {
    const value = field.value;
    const cursorPos = field.selectionStart;

    // Find the position of //trigger
    const textBeforeCursor = value.substring(0, cursorPos);
    const lastSlashPos = textBeforeCursor.lastIndexOf('//');

    // Replace //trigger with expansion
    const before = value.substring(0, lastSlashPos);
    const after = value.substring(cursorPos);
    const newValue = before + expansion + after;

    field.value = newValue;

    // Move cursor to end of expansion
    const newCursorPos = lastSlashPos + expansion.length;
    field.setSelectionRange(newCursorPos, newCursorPos);

    // Trigger input event for auto-save
    field.dispatchEvent(new Event('input', { bubbles: true }));

    // Show success toast
    showSuccessToast(`Expanded: //${trigger} → ${expansion}`);

    // Reset
    resetExpansion();
  }

  /**
   * Show expansion hint when // is typed
   */
  function showExpansionHint(field) {
    const hint = document.getElementById('text-expansion-hint');
    if (hint) {
      hint.remove();
    }

    const hintEl = document.createElement('div');
    hintEl.id = 'text-expansion-hint';
    hintEl.className = 'text-expansion-hint';
    hintEl.innerHTML = '💡 Type abbreviation, then <kbd>Tab</kbd> or <kbd>Space</kbd> to expand';

    field.parentNode.insertBefore(hintEl, field.nextSibling);

    // Auto-hide after 3 seconds
    setTimeout(() => {
      if (hintEl.parentNode) {
        hintEl.remove();
      }
    }, 3000);
  }

  /**
   * Show expansion preview
   */
  function showExpansionPreview(field, trigger, expansion) {
    let preview = document.getElementById('text-expansion-preview');

    if (!preview) {
      preview = document.createElement('div');
      preview.id = 'text-expansion-preview';
      preview.className = 'text-expansion-preview';
      field.parentNode.insertBefore(preview, field.nextSibling);
    }

    preview.innerHTML = `
      <span class="expansion-trigger">//${trigger}</span> →
      <span class="expansion-result">${expansion}</span>
      <span class="expansion-action">Press <kbd>Tab</kbd> or <kbd>Space</kbd></span>
    `;
  }

  /**
   * Hide expansion preview
   */
  function hideExpansionPreview() {
    const preview = document.getElementById('text-expansion-preview');
    if (preview) {
      preview.remove();
    }
  }

  /**
   * Reset expansion state
   */
  function resetExpansion() {
    activeTextarea = null;
    currentTrigger = '';
    hideExpansionPreview();
  }

  /**
   * Show success toast
   */
  function showSuccessToast(message) {
    const toast = document.createElement('div');
    toast.className = 'text-expansion-toast';
    toast.innerHTML = `✅ ${message}`;
    document.body.appendChild(toast);

    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 300);
    }, 2000);
  }

  // ============================================================================
  // INITIALIZATION
  // ============================================================================

  // Initialize on DOM ready
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
          const fields = node.querySelectorAll ? node.querySelectorAll('textarea, input[type="text"]') : [];
          fields.forEach(field => {
            if (!field.hasAttribute('data-text-expansion-enabled')) {
              field.setAttribute('data-text-expansion-enabled', 'true');
              field.addEventListener('input', handleInput);
              field.addEventListener('keydown', handleKeyDown);
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

  // Expose for debugging
  window.textExpansion = {
    expansions: MEDICAL_EXPANSIONS,
    addExpansion: (key, value) => {
      MEDICAL_EXPANSIONS[key] = value;
      console.log(`Added expansion: ${key} → ${value}`);
    },
  };

})();
