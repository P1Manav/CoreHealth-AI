/**
 * MemorySidebar — shows profile, conditions, symptoms, and memory facts
 * for signed-in (strong-tier) users with view/edit/delete controls.
 */
import { useState, useEffect } from 'react';
import './MemorySidebar.css';

function MemorySidebar({ isOpen, apiBase, headers, onClose }) {
  const [tab, setTab] = useState('conditions');
  const [conditions, setConditions] = useState([]);
  const [symptoms, setSymptoms] = useState([]);
  const [facts, setFacts] = useState([]);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isOpen) {
      loadAll();
    }
  }, [isOpen]);

  const loadAll = async () => {
    if (!apiBase || !headers) return;
    setLoading(true);
    try {
      const [condResp, sympResp, factsResp, profResp] = await Promise.all([
        fetch(`${apiBase}/memory/conditions`, { headers }).then(r => r.json()),
        fetch(`${apiBase}/memory/symptoms`, { headers }).then(r => r.json()),
        fetch(`${apiBase}/memory/facts`, { headers }).then(r => r.json()),
        fetch(`${apiBase}/memory/profile`, { headers }).then(r => r.json()),
      ]);
      setConditions(condResp.conditions || []);
      setSymptoms(sympResp.symptoms || []);
      setFacts(factsResp.facts || []);
      setProfile(profResp.profile || null);
    } catch (err) {
      console.error('Memory load error:', err);
    } finally {
      setLoading(false);
    }
  };

  const deleteItem = async (type, id) => {
    try {
      await fetch(`${apiBase}/memory/${type}/${id}`, {
        method: 'DELETE',
        headers,
      });
      if (type === 'conditions') setConditions(c => c.filter(x => x.id !== id));
      else if (type === 'symptoms') setSymptoms(s => s.filter(x => x.id !== id));
      else if (type === 'facts') setFacts(f => f.filter(x => x.id !== id));
    } catch (err) {
      console.error('Delete error:', err);
    }
  };

  const wipeAll = async () => {
    if (!confirm('Delete ALL your health data? This cannot be undone.')) return;
    try {
      await fetch(`${apiBase}/memory/wipe`, { method: 'DELETE', headers });
      setConditions([]);
      setSymptoms([]);
      setFacts([]);
      setProfile(null);
    } catch (err) {
      console.error('Wipe error:', err);
    }
  };

  const statusLabel = (status) => {
    const map = { ongoing: 'Ongoing', resolved: 'Resolved', unknown: 'Unknown' };
    return map[status] || status;
  };

  const tabs = [
    { key: 'conditions', label: 'Conditions', icon: 'bx-first-aid', count: conditions.length },
    { key: 'symptoms', label: 'Symptoms', icon: 'bx-pulse', count: symptoms.length },
    { key: 'facts', label: 'Memory', icon: 'bx-brain', count: facts.length },
  ];

  return (
    <aside className={`memory-sidebar ${isOpen ? 'memory-sidebar--open' : ''}`}>
      <div className="memory-sidebar__header">
        <div className="memory-sidebar__header-title">
          <i className='bx bx-brain'></i>
          <h3>Health Memory</h3>
        </div>
        <button className="memory-sidebar__close" onClick={onClose} aria-label="Close">
          <i className='bx bx-x'></i>
        </button>
      </div>

      {/* Interaction Style */}
      {profile?.interaction_style && Object.values(profile.interaction_style).some(Boolean) && (
        <div className="memory-sidebar__profile">
          <span className="memory-sidebar__profile-label">Your Style</span>
          <div className="memory-sidebar__profile-tags">
            {profile.interaction_style.tends_to_worry === true && (
              <span className="memory-sidebar__tag">Tends to worry</span>
            )}
            {profile.interaction_style.prefers_reassurance === true && (
              <span className="memory-sidebar__tag">Prefers reassurance</span>
            )}
            {profile.interaction_style.asks_followups === true && (
              <span className="memory-sidebar__tag">Asks follow-ups</span>
            )}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="memory-sidebar__tabs">
        {tabs.map(t => (
          <button
            key={t.key}
            className={`memory-sidebar__tab ${tab === t.key ? 'memory-sidebar__tab--active' : ''}`}
            onClick={() => setTab(t.key)}
          >
            <i className={`bx ${t.icon}`}></i>
            {t.label}
            {t.count > 0 && <span className="memory-sidebar__tab-count">{t.count}</span>}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="memory-sidebar__content">
        {loading ? (
          <div className="memory-sidebar__loading">
            <div className="skeleton-line long" style={{ margin: '0.6rem 0' }}></div>
            <div className="skeleton-line medium" style={{ margin: '0.6rem 0' }}></div>
            <div className="skeleton-line short" style={{ margin: '0.6rem 0' }}></div>
          </div>
        ) : (
          <>
            {tab === 'conditions' && (
              <div className="memory-sidebar__list">
                {conditions.length === 0 ? (
                  <div className="memory-sidebar__empty">
                    <i className='bx bx-first-aid' style={{ fontSize: '2rem', marginBottom: '0.5rem' }}></i>
                    <p>No conditions tracked yet.</p>
                    <small>They'll appear as you chat about health.</small>
                  </div>
                ) : (
                  conditions.map(c => (
                    <div key={c.id} className="memory-sidebar__item">
                      <div className="memory-sidebar__item-info">
                        <span className="memory-sidebar__item-name">{c.name}</span>
                        <span className={`memory-sidebar__status memory-sidebar__status--${c.status}`}>
                          {statusLabel(c.status)}
                        </span>
                      </div>
                      <button
                        className="memory-sidebar__delete"
                        onClick={() => deleteItem('conditions', c.id)}
                        title="Delete"
                      >
                        <i className='bx bx-trash'></i>
                      </button>
                    </div>
                  ))
                )}
              </div>
            )}

            {tab === 'symptoms' && (
              <div className="memory-sidebar__list">
                {symptoms.length === 0 ? (
                  <div className="memory-sidebar__empty">
                    <i className='bx bx-pulse' style={{ fontSize: '2rem', marginBottom: '0.5rem' }}></i>
                    <p>No symptoms logged yet.</p>
                    <small>Tell me your symptoms and I'll track them.</small>
                  </div>
                ) : (
                  symptoms.map(s => (
                    <div key={s.id} className="memory-sidebar__item">
                      <div className="memory-sidebar__item-info">
                        <span className="memory-sidebar__item-name">{s.symptom}</span>
                        <span className={`memory-sidebar__status memory-sidebar__status--${s.status}`}>
                          {statusLabel(s.status)}
                        </span>
                      </div>
                      <button
                        className="memory-sidebar__delete"
                        onClick={() => deleteItem('symptoms', s.id)}
                        title="Delete"
                      >
                        <i className='bx bx-trash'></i>
                      </button>
                    </div>
                  ))
                )}
              </div>
            )}

            {tab === 'facts' && (
              <div className="memory-sidebar__list">
                {facts.length === 0 ? (
                  <div className="memory-sidebar__empty">
                    <i className='bx bx-brain' style={{ fontSize: '2rem', marginBottom: '0.5rem' }}></i>
                    <p>No memory facts yet.</p>
                    <small>I'll remember things you share about your health.</small>
                  </div>
                ) : (
                  facts.map(f => (
                    <div key={f.id} className="memory-sidebar__item">
                      <div className="memory-sidebar__item-info">
                        <span className="memory-sidebar__item-name">{f.fact}</span>
                        <span className="memory-sidebar__confidence">
                          {Math.round((f.confidence || 0.8) * 100)}% confidence
                        </span>
                      </div>
                      <button
                        className="memory-sidebar__delete"
                        onClick={() => deleteItem('facts', f.id)}
                        title="Delete"
                      >
                        <i className='bx bx-trash'></i>
                      </button>
                    </div>
                  ))
                )}
              </div>
            )}
          </>
        )}
      </div>

      {/* Danger zone */}
      <div className="memory-sidebar__footer">
        <button className="memory-sidebar__wipe" onClick={wipeAll}>
          <i className='bx bx-trash-alt'></i> Delete All My Data
        </button>
      </div>
    </aside>
  );
}

export default MemorySidebar;
