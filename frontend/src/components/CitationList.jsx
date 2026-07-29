/**
 * CitationList — displays source citations under an assistant message.
 */
import './CitationList.css';

function CitationList({ citations }) {
  if (!citations || citations.length === 0) return null;

  return (
    <div className="citations">
      <div className="citations__label">📚 Sources</div>
      <div className="citations__list">
        {citations.map((c, i) => (
          <a
            key={i}
            href={c.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="citations__item"
          >
            <span className="citations__name">
              {c.title || c.source_name}
            </span>
            <span className="citations__source">{c.source_name}</span>
          </a>
        ))}
      </div>
    </div>
  );
}

export default CitationList;
