/**
 * PhysioPRISM - Voice Recorder Component
 * ========================================
 *
 * HIPAA-compliant voice-to-text transcription using Azure Speech Services
 *
 * Usage:
 *   VoiceRecorder.addToTextarea('textarea-id');
 */

class VoiceRecorder {
  constructor(targetElement) {
    this.targetElement = targetElement;
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.isRecording = false;
    this.stream = null;

    // Create UI elements
    this.createUI();
  }

  createUI() {
    // Create container
    this.container = document.createElement('div');
    this.container.className = 'voice-recorder-container';
    this.container.style.cssText = 'display: inline-flex; align-items: center; gap: 8px; margin-left: 8px;';

    // Create microphone button
    this.micButton = document.createElement('button');
    this.micButton.type = 'button';
    this.micButton.className = 'voice-recorder-btn';
    this.micButton.innerHTML = '🎤';
    this.micButton.title = 'Click to start voice typing';
    this.micButton.style.cssText = `
      background: linear-gradient(135deg, #1a5f5a 0%, #2d7a73 100%);
      color: white;
      border: none;
      border-radius: 50%;
      width: 40px;
      height: 40px;
      font-size: 20px;
      cursor: pointer;
      transition: all 0.3s ease;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    `;

    this.micButton.addEventListener('click', () => this.toggleRecording());
    this.micButton.addEventListener('mouseenter', () => {
      if (!this.isRecording) {
        this.micButton.style.transform = 'scale(1.1)';
        this.micButton.style.boxShadow = '0 4px 8px rgba(0,0,0,0.2)';
      }
    });
    this.micButton.addEventListener('mouseleave', () => {
      if (!this.isRecording) {
        this.micButton.style.transform = 'scale(1)';
        this.micButton.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)';
      }
    });

    // Create status indicator
    this.statusIndicator = document.createElement('span');
    this.statusIndicator.className = 'voice-recorder-status';
    this.statusIndicator.style.cssText = 'font-size: 12px; color: #666; display: none;';

    this.container.appendChild(this.micButton);
    this.container.appendChild(this.statusIndicator);

    // Insert after target element
    if (this.targetElement.parentNode) {
      // If textarea has a wrapper, insert after wrapper
      const wrapper = this.targetElement.closest('.control-group') ||
                      this.targetElement.closest('.field-block') ||
                      this.targetElement.parentNode;

      // Create inline container if needed
      let inlineContainer = wrapper.querySelector('.voice-recorder-inline');
      if (!inlineContainer) {
        inlineContainer = document.createElement('div');
        inlineContainer.className = 'voice-recorder-inline';
        inlineContainer.style.cssText = 'display: flex; align-items: flex-start; gap: 8px; margin-top: 8px;';

        // Move textarea into container
        const textarea = this.targetElement;
        const parent = textarea.parentNode;
        parent.insertBefore(inlineContainer, textarea);
        inlineContainer.appendChild(textarea);
        textarea.style.flex = '1';
      }

      inlineContainer.appendChild(this.container);
    }
  }

  async toggleRecording() {
    if (this.isRecording) {
      this.stopRecording();
    } else {
      await this.startRecording();
    }
  }

  async startRecording() {
    try {
      // Request microphone permission
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Create media recorder
      const mimeType = this.getSupportedMimeType();
      this.mediaRecorder = new MediaRecorder(this.stream, {
        mimeType: mimeType
      });

      this.audioChunks = [];

      this.mediaRecorder.addEventListener('dataavailable', (event) => {
        this.audioChunks.push(event.data);
      });

      this.mediaRecorder.addEventListener('stop', () => {
        this.processRecording();
      });

      this.mediaRecorder.start();
      this.isRecording = true;

      // Update UI
      this.micButton.innerHTML = '⏹️';
      this.micButton.title = 'Click to stop recording';
      this.micButton.style.background = 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)';
      this.micButton.style.animation = 'pulse 1.5s infinite';

      this.statusIndicator.textContent = 'Recording...';
      this.statusIndicator.style.display = 'inline';
      this.statusIndicator.style.color = '#ef4444';

      // Add pulse animation
      if (!document.getElementById('voice-recorder-pulse-animation')) {
        const style = document.createElement('style');
        style.id = 'voice-recorder-pulse-animation';
        style.textContent = `
          @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
          }
        `;
        document.head.appendChild(style);
      }

    } catch (error) {
      console.error('Error accessing microphone:', error);
      this.showError('Could not access microphone. Please check permissions.');
    }
  }

  stopRecording() {
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
      this.isRecording = false;

      // Stop all audio tracks
      if (this.stream) {
        this.stream.getTracks().forEach(track => track.stop());
        this.stream = null;
      }

      // Update UI
      this.micButton.innerHTML = '🎤';
      this.micButton.title = 'Click to start voice typing';
      this.micButton.style.background = 'linear-gradient(135deg, #1a5f5a 0%, #2d7a73 100%)';
      this.micButton.style.animation = 'none';

      this.statusIndicator.textContent = 'Processing...';
      this.statusIndicator.style.color = '#3b82f6';
    }
  }

  async processRecording() {
    try {
      // Create audio blob
      const audioBlob = new Blob(this.audioChunks, {
        type: this.getSupportedMimeType()
      });

      // Show processing status
      this.statusIndicator.textContent = 'Transcribing...';

      // Send to backend for transcription
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');
      formData.append('language', 'en-US'); // Could be configurable

      const response = await fetch('/api/transcribe', {
        method: 'POST',
        body: formData
      });

      const result = await response.json();

      if (result.success) {
        // Insert transcribed text into textarea
        this.insertText(result.text);

        // Show success
        this.statusIndicator.textContent = `✓ Done (${result.confidence ? (result.confidence * 100).toFixed(0) : '90'}% confidence)`;
        this.statusIndicator.style.color = '#10b981';

        // Hide status after 3 seconds
        setTimeout(() => {
          this.statusIndicator.style.display = 'none';
        }, 3000);

      } else {
        throw new Error(result.error || 'Transcription failed');
      }

    } catch (error) {
      console.error('Error processing recording:', error);
      this.showError('Failed to transcribe audio. Please try again.');
    }
  }

  insertText(text) {
    // Get current cursor position
    const start = this.targetElement.selectionStart;
    const end = this.targetElement.selectionEnd;
    const currentValue = this.targetElement.value;

    // Insert text at cursor position
    const before = currentValue.substring(0, start);
    const after = currentValue.substring(end);
    const newText = before + (before && !before.endsWith(' ') ? ' ' : '') + text + ' ' + after;

    this.targetElement.value = newText;

    // Move cursor to end of inserted text
    const newCursorPos = start + text.length + 1;
    this.targetElement.selectionStart = newCursorPos;
    this.targetElement.selectionEnd = newCursorPos;

    // Trigger input event for any listeners
    this.targetElement.dispatchEvent(new Event('input', { bubbles: true }));

    // Focus back on textarea
    this.targetElement.focus();
  }

  showError(message) {
    this.statusIndicator.textContent = `✗ ${message}`;
    this.statusIndicator.style.color = '#ef4444';
    this.statusIndicator.style.display = 'inline';

    setTimeout(() => {
      this.statusIndicator.style.display = 'none';
    }, 5000);
  }

  getSupportedMimeType() {
    const types = [
      'audio/webm',
      'audio/ogg',
      'audio/wav',
      'audio/mp4'
    ];

    for (const type of types) {
      if (MediaRecorder.isTypeSupported(type)) {
        return type;
      }
    }

    return 'audio/webm'; // Fallback
  }

  // Static method to easily add to any textarea
  static addToTextarea(textareaIdOrElement) {
    const element = typeof textareaIdOrElement === 'string'
      ? document.getElementById(textareaIdOrElement)
      : textareaIdOrElement;

    if (!element) {
      console.error('Textarea not found:', textareaIdOrElement);
      return null;
    }

    return new VoiceRecorder(element);
  }

  // Static method to add to all textareas on page
  static addToAllTextareas(selector = 'textarea') {
    const textareas = document.querySelectorAll(selector);
    const recorders = [];

    textareas.forEach(textarea => {
      // Skip if already has voice recorder
      if (textarea.closest('.voice-recorder-inline')) {
        return;
      }

      recorders.push(new VoiceRecorder(textarea));
    });

    return recorders;
  }

  // Check if browser supports voice recording
  static isSupported() {
    return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaRecorder);
  }
}

// Auto-initialize on DOMContentLoaded (optional)
document.addEventListener('DOMContentLoaded', () => {
  // Check if voice recording is supported
  if (!VoiceRecorder.isSupported()) {
    console.warn('Voice recording not supported in this browser');
    return;
  }

  // Auto-add to textareas with data-voice-enabled attribute
  document.querySelectorAll('textarea[data-voice-enabled]').forEach(textarea => {
    VoiceRecorder.addToTextarea(textarea);
  });
});
