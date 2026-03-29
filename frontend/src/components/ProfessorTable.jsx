/**
 * ProfFinder — ProfessorTable Component (v2)
 * Interactive results with multi-dimensional scoring (Bio Fit / ML Fit),
 * research tags, match reasoning, and expandable professor cards.
 */

import { useMemo, useState } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
} from '@tanstack/react-table';

function TierBadge({ tier }) {
  const cls = tier === 'High Chance' ? 'high-chance'
    : tier === 'Good Chance' ? 'good-chance'
    : 'try-your-luck';
  const icon = tier === 'High Chance' ? '🎯' : tier === 'Good Chance' ? '✅' : '🍀';
  return <span className={`tier-badge ${cls}`}>{icon} {tier}</span>;
}

function ScoreBar({ score }) {
  const cls = score >= 75 ? 'high' : score >= 50 ? 'good' : 'try';
  return (
    <div className="score-bar-container">
      <span className="score-value" style={{ color: `var(--tier-${cls})` }}>{score}</span>
      <div className="score-bar">
        <div className={`score-bar-fill ${cls}`} style={{ width: `${score}%` }} />
      </div>
    </div>
  );
}

function MultiScoreBars({ bio, ml }) {
  return (
    <div className="multi-score-bars">
      <div className="mini-score-row">
        <span className="mini-score-label">Bio</span>
        <div className="mini-score-bar">
          <div className="mini-score-fill bio" style={{ width: `${bio}%` }} />
        </div>
        <span className="mini-score-value bio-color">{bio}%</span>
      </div>
      <div className="mini-score-row">
        <span className="mini-score-label">ML</span>
        <div className="mini-score-bar">
          <div className="mini-score-fill ml" style={{ width: `${ml}%` }} />
        </div>
        <span className="mini-score-value ml-color">{ml}%</span>
      </div>
    </div>
  );
}

function ResearchTags({ tags }) {
  if (!tags || tags.length === 0) return null;
  const tagColors = ['tag-green', 'tag-purple', 'tag-blue', 'tag-amber', 'tag-cyan'];
  return (
    <div className="research-tags">
      {tags.slice(0, 4).map((tag, i) => (
        <span key={i} className={`research-tag ${tagColors[i % tagColors.length]}`}>
          {tag}
        </span>
      ))}
    </div>
  );
}

function FundingBadge({ status }) {
  if (status === 'funded') {
    return <span className="funding-badge funded">💰 Funded</span>;
  }
  return <span className="funding-badge unknown">❓ Unknown</span>;
}

function PaperList({ papers }) {
  if (!papers || papers.length === 0) return <span style={{ color: 'var(--text-muted)' }}>—</span>;
  return (
    <div className="paper-list">
      {papers.filter(p => p.is_top_match).slice(0, 3).map((paper, i) => (
        <div key={i} className="paper-pill">
          <span className="cosine-score">{(paper.cosine_score * 100).toFixed(0)}%</span>
          <span style={{ color: 'var(--text-secondary)', fontSize: '0.82rem' }}>
            {paper.title.length > 55 ? paper.title.slice(0, 55) + '…' : paper.title}
            {paper.year ? ` (${paper.year})` : ''}
          </span>
        </div>
      ))}
    </div>
  );
}

function MatchInsight({ reasoning, warning, isExpanded, onToggle }) {
  if (!reasoning && !warning) return null;
  return (
    <div className="match-insight-wrapper">
      <button className="match-insight-toggle" onClick={onToggle}>
        {isExpanded ? '▾ Hide Details' : '▸ Why This Match?'}
      </button>
      {isExpanded && (
        <div className="match-insight-content slide-up">
          {reasoning && (
            <div className="match-reasoning-card">
              <div className="match-reasoning-header">✨ WHY THIS IS A MATCH</div>
              <p>{reasoning}</p>
            </div>
          )}
          {warning && (
            <div className="match-warning-card">
              <div className="match-warning-header">⚠️ WATCH OUT FOR</div>
              <p>{warning}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ProfessorTable({ professors, requirements, onDraftEmail }) {
  const [sorting, setSorting] = useState([{ id: 'match_score', desc: true }]);
  const [globalFilter, setGlobalFilter] = useState('');
  const [tierFilter, setTierFilter] = useState('all');
  const [expandedRows, setExpandedRows] = useState(new Set());

  const toggleRow = (name) => {
    setExpandedRows(prev => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const filteredData = useMemo(() => {
    if (tierFilter === 'all') return professors;
    return professors.filter(p => p.result_tier === tierFilter);
  }, [professors, tierFilter]);

  const columns = useMemo(() => [
    {
      accessorKey: 'country',
      header: '🌍 Country',
      size: 90,
      cell: ({ getValue }) => <span style={{ fontWeight: 500 }}>{getValue()}</span>,
    },
    {
      accessorKey: 'university',
      header: '🏛️ University',
      size: 150,
      cell: ({ getValue }) => <span style={{ fontWeight: 500 }}>{getValue()}</span>,
    },
    {
      accessorKey: 'name',
      header: '👤 Professor',
      size: 180,
      cell: ({ getValue, row }) => (
        <div>
          <span style={{ fontWeight: 600 }}>{getValue()}</span>
          {row.original.department && (
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '2px' }}>
              {row.original.department}
            </div>
          )}
          <ResearchTags tags={row.original.research_tags} />
        </div>
      ),
    },
    {
      accessorKey: 'email',
      header: '📧 Email',
      size: 170,
      cell: ({ getValue, row }) => {
        const email = getValue();
        if (!email) return <span style={{ color: 'var(--text-muted)' }}>Not found</span>;
        return (
          <div className="email-cell">
            <a href={`mailto:${email}`} style={{ color: 'var(--accent-cyan)', textDecoration: 'none', fontSize: '0.85rem' }}>
              {email}
            </a>
            {row.original.email_source === 'inferred' && (
              <span className="inferred-tag">⚠️ Inferred</span>
            )}
          </div>
        );
      },
    },
    {
      accessorKey: 'match_score',
      header: '📊 Overall',
      size: 110,
      cell: ({ getValue }) => <ScoreBar score={getValue()} />,
    },
    {
      id: 'fit_scores',
      header: '🧬 Bio / ML Fit',
      size: 150,
      enableSorting: false,
      cell: ({ row }) => (
        <MultiScoreBars
          bio={row.original.bio_fit_score || 0}
          ml={row.original.ml_fit_score || 0}
        />
      ),
    },
    {
      accessorKey: 'result_tier',
      header: 'Tier',
      size: 110,
      cell: ({ getValue }) => <TierBadge tier={getValue()} />,
    },
    {
      accessorKey: 'top_matched_papers',
      header: '📑 Top Papers',
      size: 250,
      enableSorting: false,
      cell: ({ getValue }) => <PaperList papers={getValue()} />,
    },
    {
      accessorKey: 'funding_status',
      header: '💰',
      size: 80,
      cell: ({ getValue }) => <FundingBadge status={getValue()} />,
    },
    {
      id: 'actions',
      header: '✉️',
      size: 70,
      cell: ({ row }) => (
        <button
          className="btn btn-sm btn-secondary"
          onClick={() => onDraftEmail(row.original)}
          title="Draft cold email"
        >
          ✉️ Draft
        </button>
      ),
    },
  ], [onDraftEmail]);

  const table = useReactTable({
    data: filteredData,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  // Count tiers
  const highCount = professors.filter(p => p.result_tier === 'High Chance').length;
  const goodCount = professors.filter(p => p.result_tier === 'Good Chance').length;
  const tryCount = professors.filter(p => p.result_tier === 'Try Your Luck').length;

  return (
    <div className="results-section fade-in">
      <div className="results-header">
        <h2 style={{ fontSize: '1.4rem', fontWeight: 700 }}>
          🎓 Professor Results ({professors.length})
        </h2>
        <div className="results-stats">
          <button
            className={`stat-badge high`}
            onClick={() => setTierFilter(tierFilter === 'High Chance' ? 'all' : 'High Chance')}
            style={{ cursor: 'pointer', border: tierFilter === 'High Chance' ? '2px solid var(--tier-high)' : '2px solid transparent' }}
          >
            🎯 High Chance: {highCount}
          </button>
          <button
            className={`stat-badge good`}
            onClick={() => setTierFilter(tierFilter === 'Good Chance' ? 'all' : 'Good Chance')}
            style={{ cursor: 'pointer', border: tierFilter === 'Good Chance' ? '2px solid var(--tier-good)' : '2px solid transparent' }}
          >
            ✅ Good Chance: {goodCount}
          </button>
          <button
            className={`stat-badge try`}
            onClick={() => setTierFilter(tierFilter === 'Try Your Luck' ? 'all' : 'Try Your Luck')}
            style={{ cursor: 'pointer', border: tierFilter === 'Try Your Luck' ? '2px solid var(--tier-try)' : '2px solid transparent' }}
          >
            🍀 Try Your Luck: {tryCount}
          </button>
        </div>
      </div>

      {/* Search filter */}
      <input
        type="text"
        value={globalFilter}
        onChange={(e) => setGlobalFilter(e.target.value)}
        placeholder="🔍 Filter results by name, university, country..."
        style={{ marginBottom: '16px', maxWidth: '400px' }}
        id="results-filter"
      />

      {/* Table */}
      <div className="card" style={{ padding: 0, overflow: 'auto' }}>
        <table className="prof-table">
          <thead>
            {table.getHeaderGroups().map(headerGroup => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map(header => (
                  <th
                    key={header.id}
                    onClick={header.column.getToggleSortingHandler()}
                    style={{
                      cursor: header.column.getCanSort() ? 'pointer' : 'default',
                      width: header.column.getSize(),
                    }}
                  >
                    {flexRender(header.column.columnDef.header, header.getContext())}
                    {header.column.getIsSorted() === 'asc' ? ' ↑' : header.column.getIsSorted() === 'desc' ? ' ↓' : ''}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map(row => (
              <tr key={row.id} className="slide-up" style={{ cursor: 'pointer' }}>
                {row.getVisibleCells().map(cell => (
                  <td key={cell.id} onClick={() => {
                    // Don't toggle expand for action buttons
                    if (cell.column.id !== 'actions') {
                      toggleRow(row.original.name);
                    }
                  }}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    {/* Show match insight inline under the professor name cell */}
                    {cell.column.id === 'name' && (
                      <MatchInsight
                        reasoning={row.original.match_reasoning}
                        warning={row.original.match_warning}
                        isExpanded={expandedRows.has(row.original.name)}
                        onToggle={(e) => { e.stopPropagation(); toggleRow(row.original.name); }}
                      />
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {filteredData.length === 0 && (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
            No professors found matching the filter.
          </div>
        )}
      </div>
    </div>
  );
}
