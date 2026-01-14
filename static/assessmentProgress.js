/**
 * Assessment Progress Tracker for Web App
 * Tracks completion status of patient assessment workflow
 */

// Assessment workflow steps in order
const ASSESSMENT_STEPS = [
  { key: 'basicInfo', label: 'Basic Info', route: '/add_patient' },
  { key: 'subjectiveExamination', label: 'Functioning Assessment', route: '/subjective' },
  { key: 'patientPerspectives', label: 'Patient Perspectives', route: '/perspectives' },
  { key: 'objectiveAssessment', label: 'Objective Assessment', route: '/objective_assessment' },
  { key: 'provisionalDiagnosis', label: 'Provisional Diagnosis', route: '/provisional_diagnosis' },
  { key: 'initialPlan', label: 'Initial Plan', route: '/initial_plan' },
  { key: 'smartGoals', label: 'SMART Goals', route: '/smart_goals' },
  { key: 'treatmentPlan', label: 'Treatment Plan', route: '/treatment_plan' },
];

/**
 * Determine which steps are completed based on patient data
 * @param {Object} patient - Patient object from database
 * @returns {Object} Status object with boolean values for each step
 */
function getAssessmentStatus(patient) {
  if (!patient) {
    return {
      basicInfo: false,
      subjectiveExamination: false,
      patientPerspectives: false,
      objectiveAssessment: false,
      provisionalDiagnosis: false,
      initialPlan: false,
      smartGoals: false,
      treatmentPlan: false,
    };
  }

  return {
    basicInfo: !!(patient.patient_name && patient.age_sex),
    subjectiveExamination: !!(
      patient.subjective_examination ||
      patient.impairment_body_structure ||
      patient.impairment_body_function
    ),
    patientPerspectives: !!(
      patient.patient_perspectives ||
      patient.knowledge ||
      patient.attribution
    ),
    objectiveAssessment: !!(
      patient.objective_assessment ||
      patient.active_movements ||
      patient.passive_movements
    ),
    provisionalDiagnosis: !!(
      patient.provisional_diagnosis ||
      patient.diagnosis
    ),
    initialPlan: !!(
      patient.initial_plan ||
      patient.plan
    ),
    smartGoals: !!(
      patient.smart_goals ||
      patient.patient_goal ||
      patient.therapist_goal
    ),
    treatmentPlan: !!(
      patient.treatment_plan
    ),
  };
}

/**
 * Get the next incomplete step
 * @param {Object} patient - Patient object
 * @returns {Object|null} Next step object or null if complete
 */
function getNextIncompleteStep(patient) {
  const status = getAssessmentStatus(patient);

  for (const step of ASSESSMENT_STEPS) {
    if (!status[step.key]) {
      return step;
    }
  }

  return null; // All steps completed
}

/**
 * Calculate completion percentage
 * @param {Object} patient - Patient object
 * @returns {number} Percentage (0-100)
 */
function getCompletionPercentage(patient) {
  const status = getAssessmentStatus(patient);
  const completedSteps = Object.values(status).filter(Boolean).length;
  return Math.round((completedSteps / ASSESSMENT_STEPS.length) * 100);
}

/**
 * Check if assessment is fully complete
 * @param {Object} patient - Patient object
 * @returns {boolean} True if all steps complete
 */
function isAssessmentComplete(patient) {
  const status = getAssessmentStatus(patient);
  return Object.values(status).every(Boolean);
}

/**
 * Get list of completed steps
 * @param {Object} patient - Patient object
 * @returns {Array<string>} Array of completed step keys
 */
function getCompletedSteps(patient) {
  const status = getAssessmentStatus(patient);
  return Object.entries(status)
    .filter(([_, completed]) => completed)
    .map(([key, _]) => key);
}

/**
 * Get list of incomplete steps
 * @param {Object} patient - Patient object
 * @returns {Array<string>} Array of incomplete step keys
 */
function getIncompleteSteps(patient) {
  const status = getAssessmentStatus(patient);
  return Object.entries(status)
    .filter(([_, completed]) => !completed)
    .map(([key, _]) => key);
}

/**
 * Generate HTML for progress bar
 * @param {Object} patient - Patient object
 * @returns {string} HTML string for progress bar
 */
function generateProgressBarHTML(patient) {
  const percentage = getCompletionPercentage(patient);
  const nextStep = getNextIncompleteStep(patient);
  const isComplete = isAssessmentComplete(patient);

  let html = '<div class="assessment-progress-container">';

  // Progress bar
  html += '<div class="progress-bar-wrapper">';
  html += `<div class="progress-bar">`;
  html += `<div class="progress-fill" style="width: ${percentage}%"></div>`;
  html += '</div>';
  html += `<span class="progress-text">${percentage}% complete</span>`;
  html += '</div>';

  // Next step or completion badge
  if (isComplete) {
    html += '<div class="completion-badge">';
    html += '<span class="badge badge-success">✓ Complete</span>';
    html += '</div>';
  } else if (nextStep) {
    html += '<div class="next-step-indicator">';
    html += `<span class="next-step-text">Next: ${nextStep.label}</span>`;
    html += '</div>';
  }

  html += '</div>';
  return html;
}

/**
 * Generate continue button HTML
 * @param {string} patientId - Patient ID
 * @param {Object} patient - Patient object
 * @returns {string} HTML string for continue button
 */
function generateContinueButtonHTML(patientId, patient) {
  const nextStep = getNextIncompleteStep(patient);
  const isComplete = isAssessmentComplete(patient);

  if (isComplete || !nextStep) {
    return '';
  }

  return `
    <a href="${nextStep.route}/${patientId}" class="btn btn-primary btn-continue">
      <i class="fas fa-arrow-right"></i> Continue Assessment
    </a>
  `;
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    ASSESSMENT_STEPS,
    getAssessmentStatus,
    getNextIncompleteStep,
    getCompletionPercentage,
    isAssessmentComplete,
    getCompletedSteps,
    getIncompleteSteps,
    generateProgressBarHTML,
    generateContinueButtonHTML,
  };
}
