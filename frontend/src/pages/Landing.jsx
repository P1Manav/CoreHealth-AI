/**
 * Landing page — Dual Theme (Dark Lime Remix vs Light Terracotta) Split Hero
 * Styled using reference UI, dual theme engine, SVG vector icons, Google OAuth,
 * and exact Healthcare Chatbot domain content.
 */
import { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '../App';
import AuthModal from '../components/AuthModal';
import WebglBackground from '../components/WebglBackground';
import './Landing.css';

function Landing() {
  const navigate = useNavigate();
  const { session, setGuestId, signOut } = useContext(AuthContext);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [urlError, setUrlError] = useState('');
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark');

  const userEmail = session?.user?.email;
  const userName = session?.user?.user_metadata?.full_name || userEmail?.split('@')[0];

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  useEffect(() => {
    const searchParams = new URLSearchParams(window.location.search);
    const hashParams = new URLSearchParams(window.location.hash.replace('#', '?'));
    const errDesc = searchParams.get('error_description') || hashParams.get('error_description');
    if (errDesc) {
      setUrlError(decodeURIComponent(errDesc).replace(/\+/g, ' '));
    }
  }, []);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const handleGuest = () => {
    const id = crypto.randomUUID();
    sessionStorage.setItem('guest_session_id', id);
    setGuestId(id);
    navigate('/chat');
  };

  return (
    <div className="platform-hero">
      {/* Dynamic Organic Bokeh Canvas Background */}
      <WebglBackground theme={theme} />

      {/* Auth Modal */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        onGuestClick={handleGuest}
      />

      {/* Top Navbar */}
      <nav className="platform-hero__nav">
        <div className="platform-hero__logo" onClick={() => navigate('/')}>
          <div className="platform-hero__logo-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
            </svg>
          </div>
          <span className="platform-hero__logo-text">HealthChat AI</span>
        </div>

        {/* Center Navigation Pill Menu */}
        <div className="platform-hero__nav-pill">
          <a href="#symptoms">Symptoms</a>
          <a href="#memory">Memory System</a>
          <a href="#ensemble">AI Ensemble</a>
          <a href="#citations">Citations</a>
        </div>

        <div className="platform-hero__nav-right">
          {/* Theme Switcher Button (Sun / Moon) */}
          <button
            className="platform-hero__theme-toggle"
            onClick={toggleTheme}
            title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Theme`}
          >
            {theme === 'dark' ? (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="5"></circle>
                <line x1="12" y1="1" x2="12" y2="3"></line>
                <line x1="12" y1="21" x2="12" y2="23"></line>
                <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
                <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
                <line x1="1" y1="12" x2="3" y2="12"></line>
                <line x1="21" y1="12" x2="23" y2="12"></line>
                <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
                <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
              </svg>
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
              </svg>
            )}
          </button>

          {session ? (
            <div className="platform-hero__user-bar">
              <span className="platform-hero__user-pill">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                  <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                </svg>
                {userEmail}
              </span>
              <button
                className="platform-hero__btn platform-hero__btn--primary"
                onClick={() => navigate('/chat')}
              >
                Open Chat →
              </button>
              <button
                className="platform-hero__btn platform-hero__btn--secondary"
                onClick={signOut}
              >
                Log Out
              </button>
            </div>
          ) : (
            <div className="platform-hero__nav-actions">
              <button
                className="platform-hero__link-btn"
                onClick={() => setAuthModalOpen(true)}
              >
                Sign In
              </button>
              <button
                className="platform-hero__btn platform-hero__btn--primary"
                onClick={handleGuest}
              >
                Start Guest Chat
              </button>
            </div>
          )}
        </div>
      </nav>

      {/* URL Auth Error Banner */}
      {urlError && (
        <div className="platform-hero__error-banner">
          <span>⚠️ {urlError}</span>
          <button onClick={() => setUrlError('')}>✕</button>
        </div>
      )}

      {/* 2-Column Split Hero Layout */}
      <main className="platform-hero__split">
        {/* Left Column: Healthcare Headline & Action Buttons */}
        <div className="platform-hero__left">
          {/* Status Badge Pill */}
          <div className="platform-hero__badge-pill">
            <span className="platform-hero__badge-dot" />
            AI-Powered Health Platform v2.0
          </div>

          {/* Display Typography */}
          <h1 className="platform-hero__display">
            Grounded<br />Health Intelligence
          </h1>

          <p className="platform-hero__subtitle">
            Ask general medical questions, analyze symptoms, and receive evidence-backed answers
            — benchmarked across OpenRouter AI models and grounded in NIH MedlinePlus & CDC medical knowledge.
          </p>

          <div className="platform-hero__actions">
            {session ? (
              <button
                className="platform-hero__btn platform-hero__btn--primary platform-hero__btn--lg"
                onClick={() => navigate('/chat')}
              >
                Open Chat →
              </button>
            ) : (
              <>
                <button
                  className="platform-hero__btn platform-hero__btn--primary platform-hero__btn--lg"
                  onClick={handleGuest}
                >
                  Start Health Chat →
                </button>
                <button
                  className="platform-hero__btn platform-hero__btn--secondary platform-hero__btn--lg"
                  onClick={() => setAuthModalOpen(true)}
                >
                  Sign In with Google
                </button>
              </>
            )}
          </div>
        </div>

        {/* Right Column: Floating Glass Healthcare Capabilities Card over Bokeh */}
        <div className="platform-hero__right">
          <div className="platform-hero__glass-card">
            <div className="platform-hero__glass-header">
              <h2>Healthcare Capabilities</h2>
              <span className="platform-hero__status-tag">• ACTIVE</span>
            </div>

            <div className="platform-hero__divider" />

            <div className="platform-hero__capabilities-grid">
              <div className="platform-hero__cap-item">
                <div className="platform-hero__cap-icon">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
                  </svg>
                </div>
                <div className="platform-hero__cap-content">
                  <h3>Symptom Guidance</h3>
                  <p>Grounded information on common symptoms and care advice.</p>
                </div>
              </div>

              <div className="platform-hero__cap-item">
                <div className="platform-hero__cap-icon">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"></path>
                    <path d="M2 12h20"></path>
                  </svg>
                </div>
                <div className="platform-hero__cap-content">
                  <h3>Two-Tier Memory</h3>
                  <p>pgvector semantic recall for users & guest TTLCache.</p>
                </div>
              </div>

              <div className="platform-hero__cap-item">
                <div className="platform-hero__cap-icon">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
                  </svg>
                </div>
                <div className="platform-hero__cap-content">
                  <h3>Ensemble Benchmark</h3>
                  <p>Parallel multi-model verification via OpenRouter.</p>
                </div>
              </div>

              <div className="platform-hero__cap-item">
                <div className="platform-hero__cap-icon">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                  </svg>
                </div>
                <div className="platform-hero__cap-content">
                  <h3>RAGAS-Lite Scorer</h3>
                  <p>Automated faithfulness, scope, and safety hard-gates.</p>
                </div>
              </div>

              <div className="platform-hero__cap-item">
                <div className="platform-hero__cap-icon">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
                    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
                  </svg>
                </div>
                <div className="platform-hero__cap-content">
                  <h3>NIH & CDC Sources</h3>
                  <p>Every factual claim cited with MedlinePlus & CDC links.</p>
                </div>
              </div>

              <div className="platform-hero__cap-item">
                <div className="platform-hero__cap-icon">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="8" x2="12" y2="12"></line>
                    <line x1="12" y1="16" x2="12.01" y2="16"></line>
                  </svg>
                </div>
                <div className="platform-hero__cap-content">
                  <h3>Emergency Safety Net</h3>
                  <p>Instant triage detection for chest pain & severe symptoms.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Floating Bottom Right Remix Badge */}
      <div className="platform-hero__remix-badge">
        <div className="platform-hero__remix-thumb">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
          </svg>
        </div>
        <div className="platform-hero__remix-info">
          <span className="platform-hero__remix-title">HealthChat AI Platform</span>
          <span className="platform-hero__remix-sub">Lime Remix System | NIH & CDC Grounded</span>
        </div>
      </div>
    </div>
  );
}

export default Landing;
