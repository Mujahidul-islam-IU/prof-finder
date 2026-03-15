/**
 * ProfFinder — MailDrafter Component
 * Modal for generating and copying cold email drafts.
 */

import { useState } from 'react';
import { draftEmail } from '../services/api';

export default function MailDrafter({ professor, onClose }) {
  const [draft, setDraft] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);
  const [researchSummary, setResearchSummary] = useState('');
  const [strongestPub, setStrongestPub] = useState('');
  const [selectedPapers, setSelectedPapers] = useState(
    professor.top_matched_papers?.filter(p => p.is_top_match).map(p => p.title) || []
  );

  const handleGenerate = async () => {
    if (!researchSummary.trim()) {
      setError('Please provide your research summary.');
      return;
    }
    setIsLoading(true);
    setError(null);

    try {
      const result = await draftEmail({
        professor_name: professor.name,
        department: professor.department || '',
        university: professor.university,
        selected_paper_titles: selectedPapers,
        selected_paper_abstracts: professor.top_matched_papers
          ?.filter(p => selectedPapers.includes(p.title))
          .map(p => p.abstract || '') || [],
        student_research_summary: researchSummary,
        strongest_publication: strongestPub || null,
        degree_type: 'PhD',
        intake_session: 'Fall 2026',
      });
      setDraft(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopy = () => {
    if (draft) {
      const fullEmail = `Subject: ${draft.subject}\n\n${draft.body}`;
      navigator.clipboard.writeText(fullEmail);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const togglePaper = (title) => {
    setSelectedPapers(prev =>
      prev.includes(title) ? prev.filter(t => t !== title) : [...prev, title]
    );
  };

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <h2>✉️ Cold Email Draft</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div style={{ marginBottom: '16px', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
          Draft for <strong style={{ color: 'var(--accent-blue)' }}>{professor.name}</strong> at {professor.university}
        </div>

        {/* Paper Selection */}
        <div className="form-group">
          <label>Select papers to reference (1-3)</label>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {professor.top_matched_papers?.map((paper, i) => (
              <label
                key={i}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '8px',
                  padding: '8px 12px',
                  background: selectedPapers.includes(paper.title)
                    ? 'rgba(59, 130, 246, 0.1)' : 'var(--bg-secondary)',
                  border: `1px solid ${selectedPapers.includes(paper.title) ? 'var(--accent-blue)' : 'var(--border)'}`,
                  borderRadius: 'var(--radius-sm)',
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                  transition: 'all 0.2s ease',
                }}
              >
                <input
                  type="checkbox"
                  checked={selectedPapers.includes(paper.title)}
                  onChange={() => togglePaper(paper.title)}
                  style={{ marginTop: '2px' }}
                />
                <span>
                  {paper.title}
                  {paper.year ? ` (${paper.year})` : ''}
                  <span className="cosine-score" style={{ marginLeft: '6px' }}>
                    {(paper.cosine_score * 100).toFixed(0)}%
                  </span>
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* Student Research Summary */}
        <div className="form-group">
          <label htmlFor="research-summary">Your Research Summary</label>
          <textarea
            id="research-summary"
            value={researchSummary}
            onChange={(e) => setResearchSummary(e.target.value)}
            placeholder="Briefly describe your research interests, methodology, and any specific problems you've worked on..."
            rows={4}
            style={{ resize: 'vertical' }}
          />
        </div>

        <div className="form-group">
          <label htmlFor="strongest-pub">Your Strongest Publication (optional)</label>
          <input
            id="strongest-pub"
            type="text"
            value={strongestPub}
            onChange={(e) => setStrongestPub(e.target.value)}
            placeholder="Title of your best paper (if any)"
          />
        </div>

        {/* Generate Button */}
        {!draft && (
          <button
            className="btn btn-primary"
            onClick={handleGenerate}
            disabled={isLoading || selectedPapers.length === 0}
            style={{ width: '100%', justifyContent: 'center' }}
            id="generate-email-btn"
          >
            {isLoading ? (
              <><span className="spinner"></span> Drafting email...</>
            ) : (
              <>🤖 Generate Draft Email</>
            )}
          </button>
        )}

        {error && (
          <div style={{ color: 'var(--accent-red)', marginTop: '12px', fontSize: '0.9rem' }}>
            ❌ {error}
          </div>
        )}

        {/* Email Preview */}
        {draft && (
          <div className="fade-in">
            <div className="email-preview">
              <div className="email-subject">Subject: {draft.subject}</div>
              <div className="email-body">{draft.body}</div>
              <div className="word-count">{draft.word_count} words</div>
            </div>
            <button
              className="btn btn-primary copy-btn"
              onClick={handleCopy}
              id="copy-email-btn"
            >
              {copied ? '✅ Copied!' : '📋 Copy to Clipboard'}
            </button>
            <p style={{ textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '8px' }}>
              ⚠️ Review and personalize before sending. This system NEVER sends emails automatically.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
