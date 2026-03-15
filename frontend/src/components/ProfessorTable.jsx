/**
 * ProfFinder — ProfessorTable Component
 * Interactive results table with TanStack Table, tier badges,
 * freshness indicators, and mail draft triggers.
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
  const cls = score >= 70 ? 'high' : score >= 45 ? 'good' : 'try';
  return (
    <div className="score-bar-container">
      <span className="score-value" style={{ color: `var(--tier-${cls})` }}>{score}</span>
      <div className="score-bar">
        <div className={`score-bar-fill ${cls}`} style={{ width: `${score}%` }} />
      </div>
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
            {paper.title.length > 60 ? paper.title.slice(0, 60) + '…' : paper.title}
            {paper.year ? ` (${paper.year})` : ''}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function ProfessorTable({ professors, requirements, onDraftEmail }) {
  const [sorting, setSorting] = useState([{ id: 'match_score', desc: true }]);
  const [globalFilter, setGlobalFilter] = useState('');
  const [tierFilter, setTierFilter] = useState('all');

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
      size: 160,
      cell: ({ getValue }) => <span style={{ fontWeight: 500 }}>{getValue()}</span>,
    },
    {
      accessorKey: 'name',
      header: '👤 Professor',
      size: 150,
      cell: ({ getValue, row }) => (
        <div>
          <span style={{ fontWeight: 600 }}>{getValue()}</span>
          {row.original.department && (
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {row.original.department}
            </div>
          )}
        </div>
      ),
    },
    {
      accessorKey: 'email',
      header: '📧 Email',
      size: 180,
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
      header: '📊 Score',
      size: 130,
      cell: ({ getValue }) => <ScoreBar score={getValue()} />,
    },
    {
      accessorKey: 'result_tier',
      header: 'Tier',
      size: 120,
      cell: ({ getValue }) => <TierBadge tier={getValue()} />,
    },
    {
      accessorKey: 'top_matched_papers',
      header: '📑 Top Matched Papers',
      size: 280,
      enableSorting: false,
      cell: ({ getValue }) => <PaperList papers={getValue()} />,
    },
    {
      accessorKey: 'funding_status',
      header: '💰 Funding',
      size: 100,
      cell: ({ getValue }) => <FundingBadge status={getValue()} />,
    },
    {
      id: 'actions',
      header: '✉️',
      size: 80,
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
            className={`stat-badge high ${tierFilter === 'High Chance' ? '' : ''}`}
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
              <tr key={row.id} className="slide-up">
                {row.getVisibleCells().map(cell => (
                  <td key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
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
