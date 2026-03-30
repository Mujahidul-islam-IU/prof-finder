import { useState, useEffect } from 'react';
import SearchForm from './components/SearchForm';
import ProfessorTable from './components/ProfessorTable';
import StatusPipeline from './components/StatusPipeline';
import MailDrafter from './components/MailDrafter';
import Auth from './components/Auth';
import Dashboard from './components/Dashboard';
import AdminDashboard from './components/AdminDashboard';
import { useSSE } from './hooks/useSSE';

export default function App() {
  // Detect if we're on the admin portal
  const isAdminPortal = window.location.pathname.startsWith('/admin');

  const [token, setToken] = useState(localStorage.getItem('auth_token'));
  const [userName, setUserName] = useState(localStorage.getItem('user_name'));
  const [userRole, setUserRole] = useState(localStorage.getItem('user_role') || 'user');
  const [view, setView] = useState('search'); // 'search' | 'dashboard' | 'admin'

  const handleLogin = ({ name, token, role }) => {
    setToken(token);
    setUserName(name);
    setUserRole(role);
    if (isAdminPortal) {
      setView('admin');
    } else {
      setView('search');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_name');
    localStorage.removeItem('user_role');
    setToken(null);
    setUserName(null);
    setUserRole('user');
    setView('search');
  };

  const {
    professors,
    statuses,
    requirements,
    isSearching,
    isComplete,
    summary,
    error,
    currentAgent,
    startSearch,
  } = useSSE(token);

  const [emailTarget, setEmailTarget] = useState(null);

  // ── Not logged in: Show Auth ──────────────────────────
  if (!token) {
    return <Auth onLoginSuccess={handleLogin} mode={isAdminPortal ? 'admin' : 'user'} />;
  }

  // ── Admin Portal (logged in as admin) ─────────────────
  if (isAdminPortal) {
    if (userRole !== 'admin') {
      handleLogout();
      return <Auth onLoginSuccess={handleLogin} mode="admin" />;
    }
    return (
      <div className="app-container">
        <nav className="nav-bar slide-down">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1 style={{ 
              fontSize: '1.4rem', margin: 0, fontWeight: 800,
              background: 'var(--gradient-brand)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent'
            }}>
              ProfFinder
            </h1>
            <span className="admin-badge" style={{ marginBottom: 0 }}>Admin</span>
          </div>
          <div className="user-menu">
            <div className="user-avatar">{userName?.charAt(0)?.toUpperCase()}</div>
            <span>{userName}</span>
            <button className="btn btn-sm btn-secondary" onClick={handleLogout}>
              Logout
            </button>
          </div>
        </nav>
        <AdminDashboard token={token} />
      </div>
    );
  }

  // ── User Portal (logged in) ───────────────────────────
  return (
    <div className="app-container">
      <nav className="nav-bar fade-in">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <h1 style={{ 
            fontSize: '1.4rem', margin: 0, fontWeight: 800,
            background: 'var(--gradient-brand)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent'
          }}>
            ProfFinder
          </h1>
        </div>
        <div className="nav-links">
          <button 
            className={`nav-link ${view === 'search' ? 'active' : ''}`}
            onClick={() => setView('search')}
          >
            🔍 New Search
          </button>
          <button 
            className={`nav-link ${view === 'dashboard' ? 'active' : ''}`}
            onClick={() => setView('dashboard')}
          >
            📚 Dashboard
          </button>
        </div>
        <div className="user-menu">
          <div className="user-avatar">{userName?.charAt(0)?.toUpperCase()}</div>
          <span>{userName}</span>
          <button className="btn btn-sm btn-secondary" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </nav>

      {view === 'dashboard' ? (
        <Dashboard token={token} />
      ) : (
        <>
          <header className="header">
            <p>AI-powered professor matching for graduate school applications</p>
          </header>

          {/* Search Form */}
          <SearchForm onSearch={startSearch} isSearching={isSearching} />

          {/* Agent Pipeline Status */}
          {(isSearching || isComplete) && (
            <StatusPipeline
              currentAgent={currentAgent}
              statuses={statuses}
              isComplete={isComplete}
            />
          )}

          {/* Error */}
          {error && (
            <div className="card" style={{ borderColor: 'rgba(239,68,68,0.3)', background: 'rgba(239,68,68,0.05)' }}>
              <div style={{ color: 'var(--accent-red)', fontWeight: 600 }}>
                ❌ Error: {error}
              </div>
            </div>
          )}

          {/* Completion Summary */}
          {isComplete && summary && (
            <div className="card fade-in" style={{ background: 'rgba(16,185,129,0.05)', borderColor: 'rgba(16,185,129,0.2)' }}>
              <div style={{ display: 'flex', gap: '24px', justifyContent: 'center', flexWrap: 'wrap' }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '2rem', fontWeight: 800 }}>{summary.total_professors}</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Total Found</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--tier-high)' }}>{summary.high_chance}</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>High Chance</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--tier-good)' }}>{summary.good_chance}</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Good Chance</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--tier-try)' }}>{summary.try_your_luck}</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Try Your Luck</div>
                </div>
              </div>
            </div>
          )}

          {/* Professor Results Table */}
          {professors.length > 0 && (
            <ProfessorTable
              professors={professors}
              requirements={requirements}
              onDraftEmail={(prof) => setEmailTarget(prof)}
            />
          )}

          {/* Mail Drafter Modal */}
          {emailTarget && (
            <MailDrafter
              professor={emailTarget}
              onClose={() => setEmailTarget(null)}
            />
          )}
        </>
      )}
    </div>
  );
}
