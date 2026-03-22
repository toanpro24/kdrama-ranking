import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || "AIzaSyAurkc0D6vlBn__Z5SA3z20Yst7ZjUJqK8",
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || "kdrama-ranking.firebaseapp.com",
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || "kdrama-ranking",
  storageBucket: "kdrama-ranking.firebasestorage.app",
  messagingSenderId: "86371495614",
  appId: "1:86371495614:web:f0709086c25d5bd100f8ef",
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();
