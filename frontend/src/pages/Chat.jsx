/**
 * Chat page — main chat interface with ChatGPT-style history sidebar.
 */
import { useState, useEffect, useRef, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '../App';
import ChatWindow from '../components/ChatWindow';
import MemorySidebar from '../components/MemorySidebar';
import DisclaimerBanner from '../components/DisclaimerBanner';
import './Chat.css';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api';

function Chat() {
  const { tier, session, guestId, setGuestId, signOut, getApiHeaders } = useContext(AuthContext);
  const navigate = useNavigate();

  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [showDisclaimer, setShowDisclaimer] = useState(true);
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark');
  const [sessions, setSessions] = useState([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const inputRef = useRef(null);

  const userEmail = session?.user?.email;
  const userName = session?.user?.user_metadata?.full_name || userEmail?.split('@')[0];
  const userAvatar = session?.user?.user_metadata?.avatar_url;

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const sessionCreated = useRef(false);

  // Create a session ONCE on mount (strong tier)
  useEffect(() => {
    if (tier === 'strong' && !sessionCreated.current) {
      sessionCreated.current = true;
      createSession();
      loadSessions();
    }
  }, [tier]);

  // Focus input on mount + listen for suggestion clicks
  useEffect(() => {
    inputRef.current?.focus();
    const handler = (e) => {
      setInput(e.detail || '');
      inputRef.current?.focus();
    };
    window.addEventListener('suggestion-click', handler);
    return () => window.removeEventListener('suggestion-click', handler);
  }, []);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const loadSessions = async () => {
    if (tier !== 'strong') return;
    setSessionsLoading(true);
    try {
      const resp = await fetch(`${API_BASE}/sessions`, { headers: getApiHeaders() });
      const data = await resp.json();
      // Only show sessions that have a title (meaning at least one message was sent)
      const withMessages = (data.sessions || []).filter(s => s.title);
      setSessions(withMessages);
    } catch (err) {
      console.error('Load sessions error:', err);
    } finally {
      setSessionsLoading(false);
    }
  };

  const loadSessionHistory = async (sid) => {
    try {
      const resp = await fetch(`${API_BASE}/sessions/${sid}/messages`, { headers: getApiHeaders() });
      const data = await resp.json();
      const msgs = (data.messages || []).map((m) => ({
        role: m.role,
        content: m.content,
      }));
      setMessages(msgs);
      setSessionId(sid);
      setHistoryOpen(false);
    } catch (err) {
      console.error('Load history error:', err);
    }
  };

  const startNewSession = async () => {
    setMessages([]);
    await createSession();
    loadSessions();
  };

  const deleteSession = async (sid, e) => {
    e.stopPropagation();
    try {
      await fetch(`${API_BASE}/sessions/${sid}`, {
        method: 'DELETE',
        headers: getApiHeaders(),
      });
      setSessions((prev) => prev.filter((s) => s.id !== sid));
      if (sessionId === sid) {
        setMessages([]);
        createSession();
      }
    } catch (err) {
      console.error('Delete session error:', err);
    }
  };

  const createSession = async () => {
    try {
      const resp = await fetch(`${API_BASE}/session`, {
        method: 'POST',
        headers: getApiHeaders(),
      });
      const data = await resp.json();
      if (data.session_id) {
        setSessionId(data.session_id);
      }
      if (data.checkin_message) {
        setMessages([{
          role: 'assistant',
          content: data.checkin_message,
          isCheckin: true,
        }]);
      }
    } catch (err) {
      console.error('Session init error:', err);
    }
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const payload = { message: text };
      if (sessionId) payload.session_id = sessionId;

      const resp = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getApiHeaders(),
        },
        body: JSON.stringify(payload),
      });

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.error || `HTTP ${resp.status}`);
      }

      const data = await resp.json();

      const assistantMsg = {
        role: 'assistant',
        content: data.response,
        model: data.model,
        citations: data.citations || [],
      };

      setMessages((prev) => [...prev, assistantMsg]);

      // Refresh session list to get updated titles
      if (tier === 'strong') {
        setTimeout(loadSessions, 1500);
      }
    } catch (err) {
      console.error('Chat API error:', err);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `There was an error processing your request: ${err.message}. Please try again.`,
          isError: true,
        },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const formatSessionDate = (dateStr) => {
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now - d;
    const diffDays = Math.floor(diffMs / 86400000);
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    return d.toLocaleDateString();
  };

  return (
    <div className="chat-page">
      {/* Chat History Sidebar */}
      {tier === 'strong' && (
        <aside className={`chat-history-sidebar ${historyOpen ? 'chat-history-sidebar--open' : ''}`}>
          <div className="chat-history-sidebar__header">
            <span className="chat-history-sidebar__title">
              <i className='bx bx-history'></i> Chat History
            </span>
            <button className="chat-history-sidebar__close" onClick={() => setHistoryOpen(false)}>
              <i className='bx bx-x'></i>
            </button>
          </div>

          <button className="chat-history-sidebar__new" onClick={startNewSession}>
            <i className='bx bx-plus'></i> New Chat
          </button>

          <div className="chat-history-sidebar__list">
            {sessionsLoading ? (
              <div className="chat-history-sidebar__loading">
                <div className="skeleton-line medium" style={{ margin: '0.5rem 0' }}></div>
                <div className="skeleton-line short" style={{ margin: '0.5rem 0' }}></div>
                <div className="skeleton-line long" style={{ margin: '0.5rem 0' }}></div>
              </div>
            ) : sessions.length === 0 ? (
              <p className="chat-history-sidebar__empty">No previous chats yet.</p>
            ) : (
              sessions.map((s) => (
                <div
                  key={s.id}
                  className={`chat-history-sidebar__item ${s.id === sessionId ? 'chat-history-sidebar__item--active' : ''}`}
                  onClick={() => loadSessionHistory(s.id)}
                >
                  <div className="chat-history-sidebar__item-content">
                    <span className="chat-history-sidebar__item-title">
                      {s.title || 'New Conversation'}
                    </span>
                    <span className="chat-history-sidebar__item-date">
                      {formatSessionDate(s.created_at)}
                    </span>
                  </div>
                  <button
                    className="chat-history-sidebar__item-delete"
                    onClick={(e) => deleteSession(s.id, e)}
                    title="Delete session"
                  >
                    <i className='bx bx-trash'></i>
                  </button>
                </div>
              ))
            )}
          </div>
        </aside>
      )}

      {/* Overlay for mobile */}
      {historyOpen && (
        <div className="chat-overlay" onClick={() => setHistoryOpen(false)} />
      )}

      {/* Main Chat Content */}
      <div className="chat-layout">
        {/* Header */}
        <header className="chat-header">
          <div className="chat-header__left">
            {/* History toggle (signed-in only) */}
            {tier === 'strong' && (
              <button
                className="chat-header__icon-btn"
                onClick={() => setHistoryOpen(!historyOpen)}
                title="Chat History"
              >
                <i className='bx bx-sidebar'></i>
              </button>
            )}

            <div className="chat-header__logo" onClick={() => navigate('/')}>
              <div className="chat-header__logo-icon">
                <i className='bx bx-heart-circle' style={{ fontSize: '1.2rem' }}></i>
              </div>
              <span className="chat-header__logo-text">Core Health</span>
            </div>

            {/* User Profile Pill */}
            {session ? (
              <div className="chat-header__user-pill chat-header__user-pill--strong">
                {userAvatar ? (
                  <img src={userAvatar} alt="avatar" className="chat-header__avatar" />
                ) : (
                  <div className="chat-header__avatar-fallback">
                    {userName ? userName[0].toUpperCase() : 'U'}
                  </div>
                )}
                <div className="chat-header__user-info">
                  <span className="chat-header__user-name">{userName || 'User'}</span>
                  <span className="chat-header__user-email">{userEmail}</span>
                </div>
                <span className="chat-header__tier-tag">
                  <i className='bx bx-lock-alt'></i> Memory On
                </span>
              </div>
            ) : (
              <div className="chat-header__user-pill chat-header__user-pill--weak">
                <div className="chat-header__avatar-fallback">
                  <i className='bx bx-user' style={{ fontSize: '1rem' }}></i>
                </div>
                <div className="chat-header__user-info">
                  <span className="chat-header__user-name">Guest Session</span>
                  <span className="chat-header__user-email">Ephemeral · not saved</span>
                </div>
                <span className="chat-header__tier-tag chat-header__tier-tag--weak">
                  Guest
                </span>
              </div>
            )}
          </div>

          <div className="chat-header__right">
            {/* Theme Toggle */}
            <button className="chat-header__icon-btn" onClick={toggleTheme} title="Toggle theme">
              {theme === 'dark' ? (
                <i className='bx bx-sun'></i>
              ) : (
                <i className='bx bx-moon'></i>
              )}
            </button>

            {/* Memory Panel (signed-in only) */}
            {tier === 'strong' && (
              <button
                className="chat-header__btn chat-header__btn--memory"
                onClick={() => setSidebarOpen(!sidebarOpen)}
              >
                <i className='bx bx-brain'></i> Memory
              </button>
            )}

            {/* Sign In (guest only) */}
            {!session && (
              <button
                className="chat-header__btn chat-header__btn--signin"
                onClick={() => navigate('/')}
              >
                <i className='bx bx-log-in'></i> Sign In
              </button>
            )}

            {/* Log Out (signed-in only) */}
            {session && (
              <button className="chat-header__btn chat-header__btn--signout" onClick={signOut}>
                <i className='bx bx-log-out'></i> Log Out
              </button>
            )}
          </div>
        </header>

        {/* Chat body */}
        <div className="chat-body">
          <main className="chat-main">
            {showDisclaimer && (
              <DisclaimerBanner tier={tier} onDismiss={() => setShowDisclaimer(false)} />
            )}

            <ChatWindow messages={messages} loading={loading} />

            {/* Input area */}
            <div className="chat-input-area">
              <div className="chat-input">
                <textarea
                  ref={inputRef}
                  className="chat-input__field"
                  placeholder="Ask a health question, describe symptoms..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={loading}
                  rows={1}
                />
                <button
                  className="chat-input__send"
                  onClick={handleSend}
                  disabled={loading || !input.trim()}
                >
                  {loading ? (
                    <div className="chat-input__spinner" />
                  ) : (
                    <i className='bx bx-send' style={{ fontSize: '1.3rem' }}></i>
                  )}
                </button>
              </div>
              <p className="chat-input__hint">
                Core Health AI · General health info only · Not a substitute for medical advice
              </p>
            </div>
          </main>

          {/* Memory sidebar */}
          {tier === 'strong' && (
            <MemorySidebar
              isOpen={sidebarOpen}
              onClose={() => setSidebarOpen(false)}
              apiBase={API_BASE}
              headers={getApiHeaders()}
            />
          )}
        </div>
      </div>
    </div>
  );
}

export default Chat;
