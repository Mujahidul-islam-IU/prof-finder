/**
 * ProfFinder — Main Application
 */

import { useState } from 'react';
import SearchForm from './components/SearchForm';
import ProfessorTable from './components/ProfessorTable';
import StatusPipeline from './components/StatusPipeline';
import MailDrafter from './components/MailDrafter';
import { useSSE } from './hooks/useSSE';

export default function App() {
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
  } = useSSE();

  const [emailTarget, setEmailTarget] = useState(null);

  return (
    <div className="app-container">
      {/* Header */}
      <header className="header">
        <h1>ProfFinder</h1>
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
        <div className="card" style={{ borderColor: 'var(--accent-red)', background: 'rgba(239,68,68,0.05)' }}>
          <div style={{ color: 'var(--accent-red)', fontWeight: 600 }}>
            ❌ Error: {error}
          </div>
        </div>
      )}

      {/* Completion Summary */}
      {isComplete && summary && (
        <div className="card fade-in" style={{ background: 'rgba(16,185,129,0.05)', borderColor: 'rgba(16,185,129,0.3)' }}>
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
    </div>
  );
}
