import { useState, useEffect } from 'react';
import ProfessorTable from './ProfessorTable';

export default function Dashboard({ token }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedSession, setSelectedSession] = useState(null);

  useEffect(() => {
    fetchSessions();
  }, []);

  const fetchSessions = async () => {
    try {
      const res = await fetch('/api/sessions', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (!res.ok) throw new Error('Failed to fetch sessions');
      const data = await res.json();
      setSessions(data.sessions || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="loading-state fade-in"><span className="spinner"></span> Loading your history...</div>;
  if (error) return <div className="error-message">Error: {error}</div>;

  if (selectedSession) {
    return (
      <div className="dashboard-container fade-in">
        <button 
          className="btn btn-secondary btn-sm" 
          onClick={() => setSelectedSession(null)}
          style={{ marginBottom: '16px' }}
        >
          ← Back to Dashboard
        </button>
        <div className="card" style={{ marginBottom: '24px' }}>
          <h3 style={{ marginBottom: '12px' }}>📋 Search Parameters</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
            <p><strong>🔬 Field:</strong> {selectedSession.target_field}</p>
            <p><strong>🎓 Degree:</strong> {selectedSession.degree_type}</p>
            <p><strong>🌍 Countries:</strong> {selectedSession.target_countries?.join(', ')}</p>
            <p><strong>📅 Date:</strong> {new Date(selectedSession.created_at).toLocaleString()}</p>
          </div>
        </div>
        
        {selectedSession.professors && selectedSession.professors.length > 0 ? (
          <ProfessorTable 
            professors={selectedSession.professors} 
            requirements={{}} 
            onDraftEmail={(prof) => alert(`Email drafting from history is coming soon!`)} 
          />
        ) : (
          <div className="card empty-state">
            <div className="empty-state-icon">📭</div>
            <h3>No professors found in this session</h3>
            <p>This search may still be processing.</p>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="dashboard-container fade-in">
      <h2 className="dashboard-title">📚 Your Search History</h2>
      
      {sessions.length === 0 ? (
        <div className="card empty-state slide-up">
          <div className="empty-state-icon">🕵️‍♂️</div>
          <h3>No searches yet</h3>
          <p>Head to the "New Search" tab to start finding your perfect professor!</p>
        </div>
      ) : (
        <div className="sessions-grid">
          {sessions.map(session => (
            <div 
              key={session.id || session.session_id} 
              className="card session-card slide-up" 
              onClick={() => setSelectedSession(session)}
            >
              <div className="session-header">
                <h4 style={{ color: 'var(--accent-blue)', fontWeight: 700 }}>{session.target_field}</h4>
                <span className="session-date">{new Date(session.created_at).toLocaleDateString()}</span>
              </div>
              <div className="session-body">
                <p>🌍 {session.target_countries?.join(', ')}</p>
                <p>🎓 {session.degree_type}</p>
                <p>👨‍🏫 {session.professors?.length || 0} professors found</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
