/**
 * PhysioPRISM - Dark Mode Theme Manager
 * Handles theme switching, persistence, and system preference detection
 */

(function() {
  'use strict';

  const THEME_KEY = 'physioPrism_theme';
  const THEMES = {
    LIGHT: 'light',
    DARK: 'dark',
    AUTO: 'auto'
  };

  class ThemeManager {
    constructor() {
      this.currentTheme = this.loadTheme();
      this.init();
    }

    /**
     * Load theme preference from localStorage
     */
    loadTheme() {
      const savedTheme = localStorage.getItem(THEME_KEY);
      return savedTheme || THEMES.AUTO;
    }

    /**
     * Save theme preference to localStorage
     */
    saveTheme(theme) {
      localStorage.setItem(THEME_KEY, theme);
      this.currentTheme = theme;
    }

    /**
     * Get system preference for dark mode
     */
    getSystemPreference() {
      if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        return THEMES.DARK;
      }
      return THEMES.LIGHT;
    }

    /**
     * Determine which theme to apply
     */
    getEffectiveTheme() {
      if (this.currentTheme === THEMES.AUTO) {
        return this.getSystemPreference();
      }
      return this.currentTheme;
    }

    /**
     * Apply theme to document
     */
    applyTheme(theme) {
      const effectiveTheme = theme === THEMES.AUTO ? this.getSystemPreference() : theme;

      // Remove both theme attributes
      document.documentElement.removeAttribute('data-theme');

      // Set the effective theme
      if (effectiveTheme === THEMES.DARK) {
        document.documentElement.setAttribute('data-theme', 'dark');
      } else {
        document.documentElement.setAttribute('data-theme', 'light');
      }

      // Update meta theme-color for mobile browsers
      const metaThemeColor = document.querySelector('meta[name="theme-color"]');
      if (metaThemeColor) {
        metaThemeColor.setAttribute('content', effectiveTheme === THEMES.DARK ? '#1a1a1a' : '#3b82f6');
      }

      // Dispatch custom event for components to react to theme change
      window.dispatchEvent(new CustomEvent('themechange', {
        detail: { theme: effectiveTheme }
      }));
    }

    /**
     * Toggle between light and dark (cycles: light → dark → auto → light)
     */
    toggle() {
      let newTheme;

      if (this.currentTheme === THEMES.LIGHT) {
        newTheme = THEMES.DARK;
      } else if (this.currentTheme === THEMES.DARK) {
        newTheme = THEMES.AUTO;
      } else {
        newTheme = THEMES.LIGHT;
      }

      this.setTheme(newTheme);
      return newTheme;
    }

    /**
     * Set specific theme
     */
    setTheme(theme) {
      if (!Object.values(THEMES).includes(theme)) {
        console.error('Invalid theme:', theme);
        return;
      }

      this.saveTheme(theme);
      this.applyTheme(theme);
      this.updateToggleButton();
    }

    /**
     * Update theme toggle button appearance
     */
    updateToggleButton() {
      const button = document.getElementById('theme-toggle');
      if (!button) return;

      const effectiveTheme = this.getEffectiveTheme();
      const icon = button.querySelector('.theme-icon');
      const label = button.querySelector('.theme-label');

      if (!icon || !label) return;

      // Update icon and label based on current setting (not effective theme)
      if (this.currentTheme === THEMES.LIGHT) {
        icon.textContent = '☀️';
        label.textContent = 'Light';
        button.title = 'Switch to dark mode';
      } else if (this.currentTheme === THEMES.DARK) {
        icon.textContent = '🌙';
        label.textContent = 'Dark';
        button.title = 'Switch to auto mode';
      } else {
        icon.textContent = '🌓';
        label.textContent = 'Auto';
        button.title = 'Switch to light mode';
      }

      // Add visual indication of effective theme
      button.setAttribute('data-effective-theme', effectiveTheme);
    }

    /**
     * Initialize theme manager
     */
    init() {
      // Apply theme immediately (before page render if possible)
      this.applyTheme(this.currentTheme);

      // Listen for system preference changes
      if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
          if (this.currentTheme === THEMES.AUTO) {
            this.applyTheme(THEMES.AUTO);
          }
        });
      }

      // Wait for DOM to be ready
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => this.setupToggleButton());
      } else {
        this.setupToggleButton();
      }
    }

    /**
     * Setup theme toggle button
     */
    setupToggleButton() {
      const button = document.getElementById('theme-toggle');
      if (button) {
        button.addEventListener('click', () => {
          this.toggle();

          // Optional: Add a subtle animation
          button.style.transform = 'rotate(360deg)';
          setTimeout(() => {
            button.style.transform = 'rotate(0deg)';
          }, 300);
        });

        this.updateToggleButton();
      }
    }

    /**
     * Get current theme setting
     */
    getCurrentTheme() {
      return this.currentTheme;
    }

    /**
     * Get effective theme (what's actually displayed)
     */
    getActiveTheme() {
      return this.getEffectiveTheme();
    }
  }

  // Create global theme manager instance
  window.themeManager = new ThemeManager();

  // Expose theme constants globally
  window.THEMES = THEMES;

  console.log('[ThemeManager] Initialized with theme:', window.themeManager.getCurrentTheme());
})();
