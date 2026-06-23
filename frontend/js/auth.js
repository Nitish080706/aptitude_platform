/**
 * auth.js — Firebase Auth state management.
 * Firebase SDK v12.15.0 via CDN.
 * User profiles stored in Firestore users/{uid}.
 */

// ─── Firebase Config ─────────────────────────────────────────────
const firebaseConfig = {
  apiKey:            "AIzaSyDHgnMpbxenyeZL--y2pZrWYi5PeN3FeX4",
  authDomain:        "aptitude-cf8d3.firebaseapp.com",
  projectId:         "aptitude-cf8d3",
  storageBucket:     "aptitude-cf8d3.firebasestorage.app",
  messagingSenderId: "950458778954",
  appId:             "1:950458778954:web:b2ea0fa96853268da52db3",
  measurementId:     "G-T06KT57QHR",
};

// ─── Firebase SDK (CDN — same version everywhere) ────────────────
import { initializeApp }           from 'https://www.gstatic.com/firebasejs/12.15.0/firebase-app.js';
import {
  getAuth,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  onAuthStateChanged,
} from 'https://www.gstatic.com/firebasejs/12.15.0/firebase-auth.js';

const app  = initializeApp(firebaseConfig);
const auth = getAuth(app);

// ─── Token Getter (used by api.js) ───────────────────────────────
// api.js calls window.__getIdToken() to attach Bearer token to every request.
window.__getIdToken = async () => {
  const user = auth.currentUser;
  if (!user) return null;
  return user.getIdToken(/* forceRefresh */ false);
};

// ─── Sign-in (client-side Firebase Auth) ─────────────────────────
export async function signIn(email, password) {
  const cred = await signInWithEmailAndPassword(auth, email, password);
  return cred.user;
}

// ─── Sign-out ─────────────────────────────────────────────────────
export async function logout() {
  await signOut(auth);
  localStorage.removeItem('userProfile');
  window.location.href = '/index.html';
}

// ─── Auth State Listener ──────────────────────────────────────────
export function onAuth(callback) {
  return onAuthStateChanged(auth, callback);
}

export function getCurrentFirebaseUser() {
  return auth.currentUser;
}

// ─── Profile Cache (from Firestore via /auth/me) ─────────────────
export function getCachedProfile() {
  try {
    return JSON.parse(localStorage.getItem('userProfile') || 'null');
  } catch { return null; }
}

export function setCachedProfile(profile) {
  localStorage.setItem('userProfile', JSON.stringify(profile));
}

// ─── Route Guard ──────────────────────────────────────────────────
/**
 * Call on any protected page.
 * Redirects to /login.html if not signed in.
 * Resolves with the user profile (from Firestore via /auth/me) once confirmed.
 * adminOnly = true → redirects non-admins to /dashboard.html
 */
export function requireAuth(adminOnly = false) {
  return new Promise((resolve) => {
    const unsub = onAuthStateChanged(auth, async (firebaseUser) => {
      unsub();
      if (!firebaseUser) {
        window.location.href = adminOnly ? '/admin/login.html' : '/login.html';
        return;
      }

      // Use cached profile if it matches current UID
      let profile = getCachedProfile();
      if (!profile || profile.uid !== firebaseUser.uid) {
        try {
          const token = await firebaseUser.getIdToken();
          const res = await fetch(
            `${window.API_BASE_URL || 'http://localhost:8000'}/auth/me`,
            { headers: { Authorization: `Bearer ${token}` } }
          );
          if (!res.ok) throw new Error('Profile not found');
          profile = await res.json();
          setCachedProfile(profile);
        } catch {
          await signOut(auth);
          window.location.href = '/login.html';
          return;
        }
      }

      if (adminOnly && profile.role !== 'admin') {
        window.location.href = '/dashboard.html';
        return;
      }

      resolve(profile);
    });
  });
}

export { auth };
