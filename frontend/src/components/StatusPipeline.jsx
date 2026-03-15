/**
 * ProfFinder — StatusPipeline Component
 * Visual pipeline showing which agent is currently active.
 */

const AGENTS = [
  { id: 'A1', label: 'Profile Analysis', icon: '📄' },
  { id: 'A2', label: 'Country Ranking', icon: '🌍' },
  { id: 'A3', label: 'Professor Discovery', icon: '🔍' },
  { id: 'A4', label: 'Deep Profiling', icon: '📚' },
  { id: 'A5', label: 'QC & Verification', icon: '🛡️' },
];

export default function StatusPipeline({ currentAgent, statuses, isComplete }) {
  const currentIndex = AGENTS.findIndex(a => a.id === currentAgent);
  const latestStatus = statuses[statuses.length - 1];

  return (
    <div>
      <div className="pipeline">
        {AGENTS.map((agent, i) => {
          let cls = '';
          if (isComplete || i < currentIndex) cls = 'complete';
          else if (i === currentIndex) cls = 'active';

          return (
            <span key={agent.id}>
              {i > 0 && <span className="pipeline-connector" style={{ margin: '0 2px' }}>→</span>}
              <span className={`pipeline-step ${cls}`}>
                {agent.icon} {agent.label}
              </span>
            </span>
          );
        })}
      </div>

      {latestStatus && !isComplete && (
        <div className="loading-card">
          <span className="spinner"></span>
          <span>
            <strong>[{latestStatus.agent}]</strong> {latestStatus.message}
            {latestStatus.progress && ` (${latestStatus.progress})`}
          </span>
        </div>
      )}

      {isComplete && (
        <div className="loading-card" style={{ color: 'var(--accent-green)' }}>
          ✅ <strong>Search complete!</strong> Scroll down to review your results.
        </div>
      )}
    </div>
  );
}
