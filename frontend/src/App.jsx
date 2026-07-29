/**
 * App root — React Router + auth state management.
 * Tracks Supabase session (signed-in) vs guest UUID (guest).
 */
import { useState, useEffect, createContext } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { supabase } from './lib/supabaseClient';
import Landing from './pages/Landing';
import Chat from './pages/Chat';
import './App.css';

/**
 * AuthContext provides:
 *  - session: Supabase session object (null if guest/not signed in)
 *  - guestId: guest UUID string (null if signed in)
 *  - tier: 'strong' | 'weak' | null
 *  - signOut: function to sign out and return to landing
 */
export const AuthContext = createContext(null);

function App() {
  const [session, setSession] = useState(null);
  const [guestId, setGuestId] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 1. Check for existing Supabase session
    supabase.auth.getSession().then(({ data: { session: s } }) => {
      setSession(s);
      if (!s) {
        // Check for guest UUID in sessionStorage
        const stored = sessionStorage.getItem('guest_session_id');
        if (stored) setGuestId(stored);
      }
      setLoading(false);
    });

    // 2. Listen for auth state changes (login, logout, token refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, s) => {
        setSession(s);
        if (s) {
          // Signed in — clear guest state
          setGuestId(null);
          sessionStorage.removeItem('guest_session_id');
        }
      }
    );

    return () => subscription.unsubscribe();
  }, []);

  const signOut = async () => {
    await supabase.auth.signOut();
    setSession(null);
    setGuestId(null);
    sessionStorage.removeItem('guest_session_id');
  };

  // Determine tier
  const tier = session ? 'strong' : guestId ? 'weak' : null;

  // Build headers for API calls
  const getApiHeaders = () => {
    const headers = { 'Content-Type': 'application/json' };
    if (session?.access_token) {
      headers['Authorization'] = `Bearer ${session.access_token}`;
    } else if (guestId) {
      headers['X-Guest-Session-Id'] = guestId;
    }
    return headers;
  };

  if (loading) {
    return (
      <div style={{
        height: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'var(--color-text-muted)',
      }}>
        Loading…
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ session, guestId, tier, signOut, getApiHeaders, setGuestId }}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route
            path="/chat"
            element={
              tier ? <Chat /> : <Navigate to="/" replace />
            }
          />
        </Routes>
      </BrowserRouter>
    </AuthContext.Provider>
  );
}

export default App;
