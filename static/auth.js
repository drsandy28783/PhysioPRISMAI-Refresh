// ================================================================
// Firebase Authentication Utilities
// ================================================================
// Centralized authentication functions for Firebase Auth integration

import {
  getAuth,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  onAuthStateChanged,
  sendPasswordResetEmail,
  updateProfile
} from 'https://www.gstatic.com/firebasejs/9.23.0/firebase-auth.js';

// ─── AUTHENTICATION STATE ───────────────────────────────────────
let authStateListeners = [];

/**
 * Register a callback to be notified when auth state changes
 * @param {Function} callback - Function to call with user object (or null if signed out)
 */
export function onAuthChange(callback) {
  authStateListeners.push(callback);

  // Also register with Firebase
  const auth = getAuth();
  return onAuthStateChanged(auth, callback);
}

/**
 * Get the current authenticated user
 * @returns {User|null} Firebase user object or null
 */
export function getCurrentUser() {
  const auth = getAuth();
  return auth.currentUser;
}

/**
 * Get fresh ID token for current user
 * @param {boolean} forceRefresh - Force token refresh (default: false)
 * @returns {Promise<string>} ID token
 */
export async function getIdToken(forceRefresh = false) {
  const auth = getAuth();
  const user = auth.currentUser;

  if (!user) {
    throw new Error('No user signed in');
  }

  return await user.getIdToken(forceRefresh);
}

// ─── SIGN IN ────────────────────────────────────────────────────
/**
 * Sign in with email and password
 * @param {string} email - User email
 * @param {string} password - User password
 * @returns {Promise<{success: boolean, user?: User, error?: string}>}
 */
export async function signIn(email, password) {
  try {
    const auth = getAuth();
    const userCredential = await signInWithEmailAndPassword(auth, email, password);

    console.log('✅ Firebase Auth sign-in successful:', userCredential.user.email);

    return {
      success: true,
      user: userCredential.user
    };
  } catch (error) {
    console.error('❌ Firebase Auth sign-in failed:', error.code, error.message);

    // User-friendly error messages
    let errorMessage = 'Sign in failed';
    switch (error.code) {
      case 'auth/invalid-email':
        errorMessage = 'Invalid email address';
        break;
      case 'auth/user-disabled':
        errorMessage = 'This account has been disabled';
        break;
      case 'auth/user-not-found':
        errorMessage = 'No account found with this email';
        break;
      case 'auth/wrong-password':
        errorMessage = 'Incorrect password';
        break;
      case 'auth/too-many-requests':
        errorMessage = 'Too many failed attempts. Please try again later';
        break;
      default:
        errorMessage = error.message;
    }

    return {
      success: false,
      error: errorMessage
    };
  }
}

// ─── REGISTER ───────────────────────────────────────────────────
/**
 * Register new user with email and password
 * @param {string} email - User email
 * @param {string} password - User password
 * @param {Object} additionalData - Additional user data (name, institute, etc.)
 * @returns {Promise<{success: boolean, user?: User, error?: string}>}
 */
export async function register(email, password, additionalData = {}) {
  try {
    const auth = getAuth();
    const userCredential = await createUserWithEmailAndPassword(auth, email, password);

    // Update profile with display name if provided
    if (additionalData.name) {
      await updateProfile(userCredential.user, {
        displayName: additionalData.name
      });
    }

    console.log('✅ Firebase Auth registration successful:', userCredential.user.email);

    return {
      success: true,
      user: userCredential.user
    };
  } catch (error) {
    console.error('❌ Firebase Auth registration failed:', error.code, error.message);

    // User-friendly error messages
    let errorMessage = 'Registration failed';
    switch (error.code) {
      case 'auth/email-already-in-use':
        errorMessage = 'An account with this email already exists';
        break;
      case 'auth/invalid-email':
        errorMessage = 'Invalid email address';
        break;
      case 'auth/weak-password':
        errorMessage = 'Password is too weak. Use at least 8 characters';
        break;
      default:
        errorMessage = error.message;
    }

    return {
      success: false,
      error: errorMessage
    };
  }
}

// ─── SIGN OUT ───────────────────────────────────────────────────
/**
 * Sign out current user
 * @returns {Promise<{success: boolean, error?: string}>}
 */
export async function signOutUser() {
  try {
    const auth = getAuth();
    await signOut(auth);

    // Clear local storage
    localStorage.clear();
    sessionStorage.clear();

    console.log('✅ User signed out successfully');

    return { success: true };
  } catch (error) {
    console.error('❌ Sign out failed:', error);
    return {
      success: false,
      error: error.message
    };
  }
}

// ─── PASSWORD RESET ─────────────────────────────────────────────
/**
 * Send password reset email
 * @param {string} email - User email
 * @returns {Promise<{success: boolean, error?: string}>}
 */
export async function resetPassword(email) {
  try {
    const auth = getAuth();
    await sendPasswordResetEmail(auth, email);

    console.log('✅ Password reset email sent to:', email);

    return { success: true };
  } catch (error) {
    console.error('❌ Password reset failed:', error);

    let errorMessage = 'Password reset failed';
    switch (error.code) {
      case 'auth/invalid-email':
        errorMessage = 'Invalid email address';
        break;
      case 'auth/user-not-found':
        errorMessage = 'No account found with this email';
        break;
      default:
        errorMessage = error.message;
    }

    return {
      success: false,
      error: errorMessage
    };
  }
}

// ─── USER DATA SYNC ─────────────────────────────────────────────
/**
 * Sync user data to Firestore after Firebase Auth registration
 * @param {User} firebaseUser - Firebase Auth user object
 * @param {Object} userData - User data to store in Firestore
 * @returns {Promise<{success: boolean, error?: string}>}
 */
export async function syncUserToFirestore(firebaseUser, userData) {
  try {
    const idToken = await firebaseUser.getIdToken();

    const response = await fetch('/api/sync-user', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${idToken}`
      },
      body: JSON.stringify({
        firebase_uid: firebaseUser.uid,
        email: firebaseUser.email,
        ...userData
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to sync user data');
    }

    console.log('✅ User data synced to Firestore');
    return { success: true };
  } catch (error) {
    console.error('❌ User sync failed:', error);
    return {
      success: false,
      error: error.message
    };
  }
}

// ─── AUTO SIGN-IN CHECK ─────────────────────────────────────────
/**
 * Check if user is already signed in on page load
 * @returns {Promise<User|null>} Current user or null
 */
export function waitForAuth() {
  return new Promise((resolve) => {
    const auth = getAuth();
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      unsubscribe();
      resolve(user);
    });
  });
}

// ─── TOKEN REFRESH HELPER ───────────────────────────────────────
/**
 * Periodically refresh ID token to prevent expiration
 * Call this after successful sign-in
 */
export function startTokenRefresh() {
  // Refresh token every 50 minutes (tokens expire after 1 hour)
  setInterval(async () => {
    try {
      const user = getCurrentUser();
      if (user) {
        await user.getIdToken(true); // Force refresh
        console.log('🔄 ID token refreshed');
      }
    } catch (error) {
      console.error('❌ Token refresh failed:', error);
    }
  }, 50 * 60 * 1000); // 50 minutes
}
