/**
 * MessageBubble — renders a single chat message (user or assistant).
 * Properly formats markdown responses with clean typography.
 */
import CitationList from './CitationList';
import './MessageBubble.css';

function MessageBubble({ message }) {
  const { role, content, citations, isError, isCheckin, model } = message;

  // Render markdown-like content to readable HTML
  const renderContent = (text) => {
    if (!text) return '';

    let html = text
      // Escape HTML
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      // Headers h3 and h4
      .replace(/^### (.+)$/gm, '<h4>$1</h4>')
      .replace(/^## (.+)$/gm, '<h3>$1</h3>')
      // Bold
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      // Italic
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      // Inline code
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      // Links [text](url)
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
      // Bullet lists
      .replace(/^[-•] (.+)$/gm, '<li>$1</li>');

    // Wrap consecutive <li> in <ul>
    html = html.replace(/(<li>.*?<\/li>)+/gs, (match) => `<ul>${match}</ul>`);

    // Paragraphs: double newline → paragraph break
    html = html
      .split(/\n\n+/)
      .map(block => block.trim())
      .filter(Boolean)
      .map(block => {
        // Don't wrap already-wrapped blocks
        if (/^<(h[2-4]|ul|ol|li|blockquote)/.test(block)) return block;
        return `<p>${block.replace(/\n/g, '<br>')}</p>`;
      })
      .join('');

    return html;
  };

  return (
    <div className={`message message--${role} ${isError ? 'message--error' : ''} ${isCheckin ? 'message--checkin' : ''}`}>
      <div className="message__avatar">
        {role === 'user' ? (
          <i className='bx bx-user'></i>
        ) : isCheckin ? (
          <i className='bx bx-notification'></i>
        ) : (
          <i className='bx bx-bot'></i>
        )}
      </div>

      <div className="message__body">
        <div
          className="message__content"
          dangerouslySetInnerHTML={{ __html: renderContent(content) }}
        />

        {citations && citations.length > 0 && (
          <CitationList citations={citations} />
        )}

        {role === 'assistant' && model && !isError && !isCheckin && (
          <div className="message__meta">
            <span className="message__model">
              <i className='bx bx-chip'></i>
              {model.includes('/') ? model.split('/').pop() : model}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

export default MessageBubble;
