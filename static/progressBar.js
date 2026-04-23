/**
 * Assessment Progress Bar Component
 *
 * Displays a visual progress indicator for the patient assessment workflow.
 * Supports navigation to completed steps and prevents jumping to future steps.
 *
 * @param {Object} config - Configuration object
 * @param {number} config.totalSteps - Total number of steps in the workflow
 * @param {number} config.currentStep - Current step (1-indexed)
 * @param {Array<number>} config.completedSteps - Array of completed step numbers
 * @param {Array<Object>} config.steps - Array of step definitions
 */

class ProgressBar {
  constructor(config) {
    this.totalSteps = config.totalSteps || 10;
    this.currentStep = config.currentStep || 1;
    this.completedSteps = config.completedSteps || [];
    this.steps = config.steps || this.getDefaultSteps();
    this.patientId = config.patientId;

    this.render();
    this.attachEventListeners();
  }

  /**
   * Default 10-step assessment workflow
   */
  getDefaultSteps() {
    return [
      { number: 1, label: 'Patient Details', route: 'add_patient' },
      { number: 2, label: 'Pathophysiology', route: 'patho_mechanism' },
      { number: 3, label: 'Subjective Exam', route: 'subjective' },
      { number: 4, label: 'Patient Perspectives', route: 'perspectives' },
      { number: 5, label: 'Initial Plan', route: 'initial_plan' },
      { number: 6, label: 'Risk Factors & Flags', route: 'risk_factors_clinical_flags' },
      { number: 7, label: 'Objective Assessment', route: 'objective_assessment' },
      { number: 8, label: 'Provisional Diagnosis', route: 'provisional_diagnosis' },
      { number: 9, label: 'SMART Goals', route: 'smart_goals' },
      { number: 10, label: 'Treatment Plan', route: 'treatment_plan' }
    ];
  }

  /**
   * Determine if a step is completed, current, or future
   */
  getStepStatus(stepNumber) {
    if (stepNumber === this.currentStep) {
      return 'current';
    } else if (this.completedSteps.includes(stepNumber) || stepNumber < this.currentStep) {
      return 'completed';
    } else {
      return 'future';
    }
  }

  /**
   * Calculate progress percentage
   */
  getProgressPercentage() {
    if (this.totalSteps === 0) return 0;
    const progress = ((this.currentStep - 1) / (this.totalSteps - 1)) * 100;
    return Math.min(Math.max(progress, 0), 100);
  }

  /**
   * Render the progress bar HTML
   */
  render() {
    const container = document.getElementById('assessment-progress-bar');
    if (!container) return;

    const progressPercentage = this.getProgressPercentage();

    let stepsHTML = '';
    this.steps.forEach(step => {
      const status = this.getStepStatus(step.number);
      const isClickable = status === 'completed';
      const dataRoute = isClickable ? `data-route="${step.route}"` : '';
      const dataPatientId = this.patientId ? `data-patient-id="${this.patientId}"` : '';

      stepsHTML += `
        <div class="progress-step ${status}" ${dataRoute} ${dataPatientId}>
          <div class="step-circle">
            ${status === 'completed'
              ? '<span class="step-icon">✓</span>'
              : `<span class="step-number">${step.number}</span>`
            }
          </div>
          <div class="step-label">${step.label}</div>
        </div>
      `;
    });

    container.innerHTML = `
      <div class="progress-bar-container">
        <div class="progress-steps">
          <div class="progress-line">
            <div class="progress-line-fill" style="width: ${progressPercentage}%"></div>
          </div>
          ${stepsHTML}
        </div>
      </div>
    `;
  }

  /**
   * Attach click event listeners to completed steps
   */
  attachEventListeners() {
    const completedSteps = document.querySelectorAll('.progress-step.completed');

    completedSteps.forEach(stepElement => {
      stepElement.addEventListener('click', (e) => {
        const route = stepElement.getAttribute('data-route');
        const patientId = stepElement.getAttribute('data-patient-id');

        if (route && patientId) {
          // Navigate to the selected step
          window.location.href = `/${route}/${patientId}`;
        }
      });

      // Add hover effect hint
      stepElement.setAttribute('title', 'Click to return to this step');
    });
  }

  /**
   * Update the progress bar (useful for dynamic updates)
   */
  update(newConfig) {
    if (newConfig.currentStep !== undefined) {
      this.currentStep = newConfig.currentStep;
    }
    if (newConfig.completedSteps !== undefined) {
      this.completedSteps = newConfig.completedSteps;
    }

    this.render();
    this.attachEventListeners();
  }
}

/**
 * Initialize progress bar on page load
 * Expects window.progressBarConfig to be set by the template
 */
document.addEventListener('DOMContentLoaded', function() {
  if (window.progressBarConfig) {
    window.assessmentProgressBar = new ProgressBar(window.progressBarConfig);
  }
});
