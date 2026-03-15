/**
 * ProfFinder — SearchForm Component
 * CV upload + search parameters form
 */

import { useState, useRef } from 'react';

const COUNTRIES = [
  'USA', 'Canada', 'UK', 'Germany', 'Australia', 'Netherlands',
  'Sweden', 'Switzerland', 'Japan', 'South Korea', 'France',
  'Finland', 'Norway', 'Denmark', 'Singapore', 'Ireland',
];

export default function SearchForm({ onSearch, isSearching }) {
  const [cvFile, setCvFile] = useState(null);
  const [targetField, setTargetField] = useState('');
  const [degreeType, setDegreeType] = useState('PhD');
  const [selectedCountries, setSelectedCountries] = useState([]);
  const [intakeSessions, setIntakeSessions] = useState('Fall 2026');
  const [ieltsScore, setIeltsScore] = useState('');
  const [greScore, setGreScore] = useState('');
  const fileInputRef = useRef(null);

  const toggleCountry = (country) => {
    setSelectedCountries(prev =>
      prev.includes(country)
        ? prev.filter(c => c !== country)
        : [...prev, country]
    );
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!cvFile || !targetField || selectedCountries.length === 0) return;

    const formData = new FormData();
    formData.append('cv_file', cvFile);
    formData.append('target_field', targetField);
    formData.append('degree_type', degreeType);
    formData.append('target_countries', selectedCountries.join(','));
    formData.append('intake_sessions', intakeSessions);
    formData.append('is_international', true);
    if (ieltsScore) formData.append('ielts_score', parseFloat(ieltsScore));
    if (greScore) formData.append('gre_score', parseInt(greScore));

    onSearch(formData);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && (file.name.endsWith('.pdf') || file.name.endsWith('.docx'))) {
      setCvFile(file);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="slide-up">
      {/* CV Upload */}
      <div className="card">
        <div className="card-title">
          <span className="icon">📄</span> Upload Your CV
        </div>
        <div
          className={`upload-zone ${cvFile ? 'active' : ''}`}
          onClick={() => fileInputRef.current?.click()}
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
        >
          <span className="icon">{cvFile ? '✅' : '📁'}</span>
          {cvFile ? (
            <>
              <p>File selected:</p>
              <p className="filename">{cvFile.name}</p>
            </>
          ) : (
            <>
              <p><strong>Click or drag</strong> your CV here</p>
              <p style={{ fontSize: '0.85rem', marginTop: '4px' }}>Supports PDF and DOCX</p>
            </>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.doc"
            onChange={(e) => setCvFile(e.target.files?.[0] || null)}
            style={{ display: 'none' }}
            id="cv-upload"
          />
        </div>
      </div>

      {/* Search Parameters */}
      <div className="card">
        <div className="card-title">
          <span className="icon">🎯</span> Search Parameters
        </div>

        <div className="form-row">
          <div className="form-group">
            <label htmlFor="target-field">Target Field of Study</label>
            <input
              id="target-field"
              type="text"
              value={targetField}
              onChange={(e) => setTargetField(e.target.value)}
              placeholder="e.g. Artificial Intelligence, Bioinformatics"
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="degree-type">Degree Type</label>
            <select
              id="degree-type"
              value={degreeType}
              onChange={(e) => setDegreeType(e.target.value)}
            >
              <option value="PhD">PhD</option>
              <option value="MSc">MSc (Thesis-based)</option>
            </select>
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label htmlFor="intake-sessions">Intake Session(s)</label>
            <input
              id="intake-sessions"
              type="text"
              value={intakeSessions}
              onChange={(e) => setIntakeSessions(e.target.value)}
              placeholder="e.g. Fall 2026, Spring 2027"
            />
          </div>
          <div className="form-group">
            <label htmlFor="ielts-score">IELTS Score (optional)</label>
            <input
              id="ielts-score"
              type="number"
              step="0.5"
              min="0"
              max="9"
              value={ieltsScore}
              onChange={(e) => setIeltsScore(e.target.value)}
              placeholder="e.g. 7.5"
            />
          </div>
          <div className="form-group">
            <label htmlFor="gre-score">GRE Score (optional)</label>
            <input
              id="gre-score"
              type="number"
              min="260"
              max="340"
              value={greScore}
              onChange={(e) => setGreScore(e.target.value)}
              placeholder="e.g. 320"
            />
          </div>
        </div>

        {/* Country Selection */}
        <div className="form-group">
          <label>Target Countries (select one or more)</label>
          <div style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '8px',
            marginTop: '6px',
          }}>
            {COUNTRIES.map(country => (
              <button
                key={country}
                type="button"
                onClick={() => toggleCountry(country)}
                className={`btn btn-sm ${selectedCountries.includes(country) ? 'btn-primary' : 'btn-secondary'}`}
                style={{ transition: 'all 0.2s ease' }}
              >
                {country}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Submit */}
      <button
        type="submit"
        className="btn btn-primary"
        disabled={isSearching || !cvFile || !targetField || selectedCountries.length === 0}
        style={{ width: '100%', justifyContent: 'center', fontSize: '1.05rem', padding: '16px' }}
        id="search-btn"
      >
        {isSearching ? (
          <>
            <span className="spinner"></span>
            Searching professors...
          </>
        ) : (
          <>🔍 Find Professors</>
        )}
      </button>
    </form>
  );
}
