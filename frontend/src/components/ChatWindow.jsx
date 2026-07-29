/**
 * ChatWindow — scrollable message list with skeleton loading state.
 */
import { useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';
import './ChatWindow.css';

function ChatWindow({ messages, loading }) {
  const bottomRef = useRef(null);

  // Auto-scroll to bottom on new messages, but NOT on initial empty state
  useEffect(() => {
    if (messages.length > 0 || loading) {
      // Small timeout to allow DOM to update before scrolling
      setTimeout(() => {
        if (bottomRef.current) {
          bottomRef.current.scrollIntoView({ behavior: 'smooth' });
        }
      }, 50);
    }
  }, [messages, loading]);

const handleSuggestionClick = (text) => {
  // Dispatch a custom event so Chat.jsx can pick it up if needed
  window.dispatchEvent(new CustomEvent('suggestion-click', { detail: text }));
};

return (
  <div className="chat-window">
    {messages.length === 0 && !loading ? (
      <div className="chat-window__empty">
        <div className="chat-window__empty-icon">
          <i className='bx bx-heart-circle'></i>
        </div>
        <h2>How can I help you today?</h2>
        <p>Ask about symptoms, conditions, nutrition, first aid, or general health advice.</p>
        <div className="chat-window__suggestions">
          {[
            'What causes frequent headaches?',
            'How can I improve my sleep quality?',
            'What are the symptoms of diabetes?',
            'First aid for minor burns',
          ].map((s) => (
            <button
              key={s}
              className="chat-window__suggestion"
              onClick={() => handleSuggestionClick(s)}
            >
              {s}
            </button>
          ))}
        </div>
      </div>
    ) : (
      <div className="chat-window__messages">
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}

        {loading && (
          <div className="chat-window__typing-skeleton">
            <div className="skeleton-avatar"></div>
            <div className="skeleton-lines">
              <div className="skeleton-line medium"></div>
              <div className="skeleton-line long"></div>
              <div className="skeleton-line short"></div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    )}
  </div>
);
}

export default ChatWindow;
