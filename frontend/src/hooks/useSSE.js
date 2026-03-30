/**
 * ProfFinder — useSSE Hook
 * Connects to the SSE search endpoint, collects professor results + status updates.
 */

import { useState, useCallback, useRef } from 'react';
import { apiUrl } from '../services/api';

export function useSSE(token) {
  const [professors, setProfessors] = useState([]);
  const [statuses, setStatuses] = useState([]);
  const [requirements, setRequirements] = useState({});
  const [isSearching, setIsSearching] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState(null);
  const [currentAgent, setCurrentAgent] = useState('');
  const eventSourceRef = useRef(null);

  const startSearch = useCallback(async (formData) => {
    // Reset state
    setProfessors([]);
    setStatuses([]);
    setRequirements({});
    setIsSearching(true);
    setIsComplete(false);
    setSummary(null);
    setError(null);
    setCurrentAgent('A1');

    try {
      if (token) {
        formData.append('token', token);
      }

      // POST the form data and get SSE stream
      const response = await fetch(apiUrl('/api/search'), {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data:')) {
            const jsonStr = line.slice(5).trim();
            if (!jsonStr) continue;

            try {
              const event = JSON.parse(jsonStr);

              switch (event.event_type) {
                case 'professor_result':
                  setProfessors(prev => {
                    // Deduplicate by name+university
                    const key = `${event.professor.name}-${event.professor.university}`;
                    const exists = prev.some(
                      p => `${p.name}-${p.university}` === key
                    );
                    if (exists) return prev;
                    return [...prev, event.professor];
                  });
                  if (event.requirements) {
                    setRequirements(prev => ({
                      ...prev,
                      [event.professor.university]: event.requirements,
                    }));
                  }
                  break;

                case 'status':
                  setStatuses(prev => [...prev.slice(-20), event]);
                  setCurrentAgent(event.agent || '');
                  break;

                case 'complete':
                  setSummary(event);
                  setIsComplete(true);
                  setIsSearching(false);
                  break;

                case 'error':
                  setError(event.message);
                  setIsSearching(false);
                  break;
              }
            } catch (e) {
              // Skip malformed JSON
            }
          }
        }
      }

      // Stream ended
      if (!isComplete) {
        setIsSearching(false);
      }
    } catch (err) {
      setError(err.message);
      setIsSearching(false);
    }
  }, [token]);

  const cancelSearch = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    setIsSearching(false);
  }, []);

  return {
    professors,
    statuses,
    requirements,
    isSearching,
    isComplete,
    summary,
    error,
    currentAgent,
    startSearch,
    cancelSearch,
  };
}
