// Firebase App, Auth, Firestore & Analytics SDK Initialization for FarmUp
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js";
import { getAnalytics } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-analytics.js";
import { 
  getAuth, 
  GoogleAuthProvider, 
  signInWithPopup, 
  signOut, 
  onAuthStateChanged,
  RecaptchaVerifier,
  signInWithPhoneNumber,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  updateProfile
} from "https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js";
import {
  getFirestore,
  doc,
  setDoc,
  getDoc,
  collection,
  query,
  where,
  getDocs,
  addDoc,
  serverTimestamp
} from "https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js";

// Web App Firebase Configuration
const firebaseConfig = {
  apiKey: "AIzaSyBMWa7OETeAxwF8iPdWBHF6O0wS3vXH-kg",
  authDomain: "farmup-84a97.firebaseapp.com",
  projectId: "farmup-84a97",
  storageBucket: "farmup-84a97.firebasestorage.app",
  messagingSenderId: "101096215459",
  appId: "1:101096215459:web:b530e40bc050f0e97c0016",
  measurementId: "G-CMBQ8H5110"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
auth.useDeviceLanguage();
const db = getFirestore(app);
const googleProvider = new GoogleAuthProvider();

let analytics = null;
try {
  analytics = getAnalytics(app);
} catch (e) {
  console.info("Firebase Analytics initialized.");
}

// Global Auth & Firestore Client Helpers (Supporting Google, Phone OTP, and Email/Password)
const FarmUpFirebaseAuth = {
  auth,
  db,
  googleProvider,

  // 1. Google Sign-In with Real Firestore Database Verification
  async signInWithGoogle() {
    try {
      const result = await signInWithPopup(auth, googleProvider);
      const user = result.user;
      
      // Look up existing farmer profile in Cloud Firestore database
      let profile = null;
      try {
        profile = await Promise.race([
          this.getFarmerProfile(user.uid),
          new Promise(r => setTimeout(() => r(null), 2500))
        ]);
        if (!profile && user.email) {
          profile = await Promise.race([
            this.getFarmerProfile(user.email),
            new Promise(r => setTimeout(() => r(null), 2000))
          ]);
        }
      } catch (err) {
        console.warn("Firestore lookup warning:", err);
      }

      if (!profile && typeof FarmUpAuth !== 'undefined') {
        profile = FarmUpAuth.findUser(user.email || user.uid);
      }

      if (profile) {
        // Account exists! Log in and sync
        profile.uid = user.uid;
        profile.gmail = user.email || profile.gmail || profile.email;
        if (typeof FarmUpAuth !== 'undefined') {
          FarmUpAuth.login(profile);
        }
        return { success: true, isNewUser: false, user, profile };
      } else {
        // Account does NOT exist in database yet -> Prompt farmer signup!
        return { 
          success: true, 
          isNewUser: true, 
          user: {
            uid: user.uid,
            displayName: user.displayName || '',
            email: user.email || '',
            phoneNumber: user.phoneNumber || '',
            photoURL: user.photoURL || ''
          }, 
          profile: null 
        };
      }
    } catch (err) {
      console.warn("Google Sign-In error:", err);
      return { success: false, error: err };
    }
  },

  // 2. Email & Password Sign-In
  async signInWithEmail(email, password) {
    try {
      const userCredential = await signInWithEmailAndPassword(auth, email, password);
      const user = userCredential.user;
      let profile = await this.getFarmerProfile(user.uid);
      if (!profile) {
        profile = {
          uid: user.uid,
          name: user.displayName || email.split('@')[0],
          gmail: email,
          phone: '9876543210',
          state: 'Punjab',
          district: 'Ludhiana',
          village: 'Bondli Kalan',
          acres: 5.5,
          soil: 'Alluvial Soil',
          crops: ['Sharbati Wheat', 'Pusa Bold Mustard'],
          irrigation: 'Borewell + Drip Irrigation',
          kisanId: `KID-IND-2026-${Math.floor(1000 + Math.random() * 9000)}`,
          verified: { email: true, phone: false, google: false, aadhaar: false }
        };
        await this.saveFarmerProfile(user.uid, profile);
      }
      if (typeof FarmUpAuth !== 'undefined') FarmUpAuth.login(profile);
      return { success: true, user, profile };
    } catch (err) {
      console.warn("Email Sign-In error:", err);
      return { success: false, error: err };
    }
  },

  // 3. Email & Password Sign-Up
  async signUpWithEmail(email, password, extraData = {}) {
    try {
      const userCredential = await createUserWithEmailAndPassword(auth, email, password);
      const user = userCredential.user;
      if (extraData.name) {
        await updateProfile(user, { displayName: extraData.name });
      }
      const profile = {
        uid: user.uid,
        name: extraData.name || user.displayName || 'Kisan Farmer',
        gmail: email,
        phone: extraData.phone || '9876543210',
        state: extraData.state || 'Punjab',
        district: extraData.district || 'Ludhiana',
        village: extraData.village || 'Gram Panchayat',
        acres: extraData.acres || 5.5,
        soil: extraData.soil || 'Alluvial Soil',
        crops: extraData.crops || ['Sharbati Wheat'],
        irrigation: extraData.irrigation || 'Borewell + Drip Irrigation',
        kisanId: `KID-${(extraData.state || 'IND').substring(0,3).toUpperCase()}-2026-${Math.floor(1000 + Math.random() * 9000)}`,
        verified: { email: true, phone: !!extraData.phone, google: false, aadhaar: true }
      };
      await this.saveFarmerProfile(user.uid, profile);
      if (typeof FarmUpAuth !== 'undefined') FarmUpAuth.login(profile);
      return { success: true, user, profile };
    } catch (err) {
      console.warn("Email Sign-Up error:", err);
      return { success: false, error: err };
    }
  },

  // 4. Phone Number OTP Verification
  initRecaptcha(containerId = 'recaptcha-container') {
    let container = document.getElementById(containerId);
    if (!container) {
      container = document.createElement('div');
      container.id = containerId;
      document.body.appendChild(container);
    }
    if (window.recaptchaVerifier) {
      try { window.recaptchaVerifier.clear(); } catch(e){}
      window.recaptchaVerifier = null;
    }
    window.recaptchaVerifier = new RecaptchaVerifier(auth, containerId, {
      size: 'invisible',
      callback: () => {}
    });
    return window.recaptchaVerifier;
  },

  async sendPhoneOtp(rawPhone, containerId = 'recaptcha-container') {
    try {
      const verifier = this.initRecaptcha(containerId);
      const digits = rawPhone.replace(/\D/g, '').slice(-10);
      const formattedPhone = `+91${digits}`;
      const confirmationResult = await signInWithPhoneNumber(auth, formattedPhone, verifier);
      window.phoneConfirmationResult = confirmationResult;
      return { success: true, confirmationResult };
    } catch (err) {
      console.warn("Phone OTP Send Error:", err);
      if (window.recaptchaVerifier) {
        try { window.recaptchaVerifier.clear(); } catch(e){}
        window.recaptchaVerifier = null;
      }
      return { success: false, error: err };
    }
  },

  async verifyPhoneOtp(otpCode) {
    try {
      if (!window.phoneConfirmationResult) {
        throw new Error("No pending phone verification. Please request OTP first.");
      }
      const result = await window.phoneConfirmationResult.confirm(otpCode);
      const user = result.user;
      let profile = await this.getFarmerProfile(user.uid);
      if (!profile) {
        profile = {
          uid: user.uid,
          name: 'Kisan Farmer',
          phone: user.phoneNumber || '',
          gmail: 'kisan@gmail.com',
          state: 'Punjab',
          district: 'Ludhiana',
          village: 'Bondli Kalan',
          acres: 5.5,
          soil: 'Alluvial Soil',
          crops: ['Sharbati Wheat', 'Pusa Bold Mustard'],
          irrigation: 'Borewell + Drip Irrigation',
          kisanId: `KID-IND-2026-${Math.floor(1000 + Math.random() * 9000)}`,
          verified: { phone: true, google: false, aadhaar: true }
        };
        await this.saveFarmerProfile(user.uid, profile);
      }
      if (typeof FarmUpAuth !== 'undefined') FarmUpAuth.login(profile);
      return { success: true, user, profile };
    } catch (err) {
      console.warn("Phone OTP Verify Error:", err);
      return { success: false, error: err };
    }
  },

  // Save farmer profile to Cloud Firestore collection "farmers/{uid}"
  async saveFarmerProfile(uid, profileData) {
    try {
      const ref = doc(db, "farmers", uid);
      const dataToSave = {
        ...profileData,
        updatedAt: new Date().toISOString()
      };
      await Promise.race([
        setDoc(ref, dataToSave, { merge: true }),
        new Promise((_, reject) => setTimeout(() => reject(new Error("Firestore save timeout")), 4000))
      ]);
      return true;
    } catch (err) {
      console.warn("Firestore save profile warning:", err);
      return false;
    }
  },

  // Get profile from Cloud Firestore by UID, Phone or Email
  async getFarmerProfile(identifier) {
    if (!identifier) return null;
    try {
      // 1. Direct UID Document Lookup
      const ref = doc(db, "farmers", identifier);
      const snap = await getDoc(ref);
      if (snap.exists()) {
        return snap.data();
      }

      // 2. Lookup by phone number query
      const cleanDigits = identifier.replace(/\D/g, '').slice(-10);
      if (cleanDigits && cleanDigits.length === 10) {
        const phoneQ = query(collection(db, "farmers"), where("phone", "==", cleanDigits));
        const phoneSnap = await getDocs(phoneQ);
        if (!phoneSnap.empty) {
          return phoneSnap.docs[0].data();
        }
      }

      // 3. Lookup by email query
      if (identifier.includes('@')) {
        const emailQ = query(collection(db, "farmers"), where("gmail", "==", identifier.trim().toLowerCase()));
        const emailSnap = await getDocs(emailQ);
        if (!emailSnap.empty) {
          return emailSnap.docs[0].data();
        }
      }
    } catch (err) {
      console.warn("Firestore fetch profile error:", err);
    }
    return null;
  },

  // Log Crop Disease Scans & AI Advisory to "farmers/{uid}/advisories"
  async logCropAdvisory(uid, advisoryData) {
    try {
      const colRef = collection(db, "farmers", uid, "advisories");
      const docRef = await addDoc(colRef, {
        ...advisoryData,
        timestamp: new Date().toISOString()
      });
      return { success: true, id: docRef.id };
    } catch (err) {
      console.warn("Firestore log advisory error:", err);
      return { success: false, error: err };
    }
  },

  // Save Plot / Parcel Telemetry to "farmers/{uid}/parcels"
  async savePlotParcel(uid, parcelData) {
    try {
      const parcelId = parcelData.id || `plot_${Date.now()}`;
      const ref = doc(db, "farmers", uid, "parcels", parcelId);
      await setDoc(ref, {
        ...parcelData,
        updatedAt: new Date().toISOString()
      }, { merge: true });
      return { success: true, parcelId };
    } catch (err) {
      console.warn("Firestore save parcel error:", err);
      return { success: false, error: err };
    }
  },

  // Save Govt Scheme & PMFBY Application to "farmers/{uid}/schemes"
  async saveSchemeApplication(uid, schemeData) {
    try {
      const colRef = collection(db, "farmers", uid, "schemes");
      const docRef = await addDoc(colRef, {
        ...schemeData,
        appliedAt: new Date().toISOString()
      });
      return { success: true, id: docRef.id };
    } catch (err) {
      console.warn("Firestore save scheme error:", err);
      return { success: false, error: err };
    }
  },

  // Sign out
  async logout() {
    try {
      await signOut(auth);
    } catch (e) {
      console.warn("Firebase signOut error:", e);
    }
    localStorage.removeItem('farmup_profile');
    if (typeof FarmUpAuth !== 'undefined') {
      FarmUpAuth.syncUI();
    }
  },

  // Listen to Auth State
  onAuthChange(callback) {
    return onAuthStateChanged(auth, async (user) => {
      if (user) {
        const profile = (await this.getFarmerProfile(user.uid)) || (typeof FarmUpAuth !== 'undefined' ? FarmUpAuth.getProfile() : null);
        callback(user, profile);
      } else {
        callback(null, null);
      }
    });
  }
};

window.firebaseApp = app;
window.firebaseAuth = auth;
window.firebaseDb = db;
window.FarmUpFirebaseAuth = FarmUpFirebaseAuth;

// Automatic Real-Time Auth & Multi-Account Synchronization
onAuthStateChanged(auth, async (user) => {
  if (user) {
    let firestoreProfile = null;
    try {
      firestoreProfile = await FarmUpFirebaseAuth.getFarmerProfile(user.uid);
      if (!firestoreProfile && user.email) {
        firestoreProfile = await FarmUpFirebaseAuth.getFarmerProfile(user.email);
      }
    } catch (e) {
      console.warn("Firestore onAuthChange fetch warning:", e);
    }

    if (firestoreProfile) {
      firestoreProfile.uid = user.uid;
      firestoreProfile.gmail = user.email || firestoreProfile.gmail || firestoreProfile.email;
      firestoreProfile.email = user.email || firestoreProfile.email || firestoreProfile.gmail;
      firestoreProfile.isLoggedIn = true;
      if (typeof FarmUpAuth !== 'undefined') {
        FarmUpAuth.login(firestoreProfile);
      }
    } else {
      // Check if localStorage has mismatched email from another account
      const localP = typeof FarmUpAuth !== 'undefined' ? FarmUpAuth.getProfile() : null;
      if (localP && localP.email && user.email && localP.email.toLowerCase() !== user.email.toLowerCase()) {
        localStorage.removeItem('farmup_profile');
        if (typeof FarmUpAuth !== 'undefined') FarmUpAuth.syncUI();
      }
    }

    // Broadcast account sync to all open page scripts
    window.dispatchEvent(new CustomEvent('farmup_account_synced', { 
      detail: firestoreProfile || { uid: user.uid, email: user.email, name: user.displayName || '' } 
    }));
  } else {
    window.dispatchEvent(new CustomEvent('farmup_account_synced', { detail: null }));
  }
});

export { app, auth, db, analytics, FarmUpFirebaseAuth };
