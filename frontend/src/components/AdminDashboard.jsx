import { useState, useEffect } from 'react';
import ProfessorTable from './ProfessorTable';
import { apiUrl } from '../services/api';

export default function AdminDashboard({ token }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Edit State
  const [editingUser, setEditingUser] = useState(null);
  const [editForm, setEditForm] = useState({ name: '', email: '', role: '' });
  const [saving, setSaving] = useState(false);

  // Drill-down State
  const [selectedUser, setSelectedUser] = useState(null);
  const [userSessions, setUserSessions] = useState([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [selectedSession, setSelectedSession] = useState(null);

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const res = await fetch(apiUrl('/api/auth/users'), {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Failed to fetch users');
      const data = await res.json();
      setUsers(data || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchUserSessions = async (userId) => {
    setSessionsLoading(true);
    try {
      const res = await fetch(apiUrl(`/api/admin/sessions/${userId}`), {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Failed to fetch user sessions');
      const data = await res.json();
      setUserSessions(data.sessions || []);
    } catch (err) {
      setUserSessions([]);
    } finally {
      setSessionsLoading(false);
    }
  };

  const handleDelete = async (userId) => {
    if (!window.confirm("Are you sure you want to delete this user?")) return;
    try {
      const res = await fetch(apiUrl(`/api/auth/users/${userId}`), {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Failed to delete user');
      setUsers(users.filter(u => u.id !== userId));
    } catch (err) {
      alert(err.message);
    }
  };

  const handleEdit = (user) => {
    setEditingUser(user.id);
    setEditForm({ name: user.name, email: user.email, role: user.role });
  };

  const saveEdit = async (userId) => {
    setSaving(true);
    try {
      const res = await fetch(apiUrl(`/api/auth/users/${userId}`), {
        method: 'PUT',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(editForm)
      });
      if (!res.ok) throw new Error('Failed to update user');
      const updatedUser = await res.json();
      setUsers(users.map(u => u.id === userId ? { ...u, ...updatedUser } : u));
      setEditingUser(null);
    } catch (err) {
      alert(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleViewUser = (user) => {
    setSelectedUser(user);
    setSelectedSession(null);
    fetchUserSessions(user.id);
  };

  const filteredUsers = users.filter(u =>
    u.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    u.email.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (loading) return <div className="loading-state fade-in"><span className="spinner"></span> Loading users...</div>;
  if (error) return <div className="error-message">Error: {error}</div>;

  // ── Session Detail View ─────────────────────────────
  if (selectedSession) {
    return (
      <div className="dashboard-container fade-in">
        <button className="btn btn-secondary btn-sm" onClick={() => setSelectedSession(null)} style={{ marginBottom: '16px' }}>
          ← Back to {selectedUser.name}'s Sessions
        </button>
        <div className="card" style={{ marginBottom: '24px' }}>
          <h3 style={{ marginBottom: '12px' }}>📋 Session Details</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
            <p><strong>Field:</strong> {selectedSession.target_field}</p>
            <p><strong>Degree:</strong> {selectedSession.degree_type}</p>
            <p><strong>Countries:</strong> {selectedSession.target_countries?.join(', ')}</p>
            <p><strong>Date:</strong> {new Date(selectedSession.created_at).toLocaleString()}</p>
          </div>
        </div>
        
        {selectedSession.professors && selectedSession.professors.length > 0 ? (
          <ProfessorTable 
            professors={selectedSession.professors} 
            requirements={{}} 
            onDraftEmail={() => {}} 
          />
        ) : (
          <div className="card empty-state">
            <div className="empty-state-icon">📭</div>
            <h3>No professors in this session</h3>
          </div>
        )}
      </div>
    );
  }

  // ── User Session List View ──────────────────────────
  if (selectedUser) {
    return (
      <div className="dashboard-container fade-in">
        <button className="btn btn-secondary btn-sm" onClick={() => { setSelectedUser(null); setUserSessions([]); }} style={{ marginBottom: '16px' }}>
          ← Back to Users
        </button>
        
        <div className="card" style={{ marginBottom: '24px' }}>
          <h3 style={{ marginBottom: '8px' }}>👤 {selectedUser.name}</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>{selectedUser.email}</p>
          <span className={`role-badge ${selectedUser.role}`}>{selectedUser.role}</span>
        </div>

        <h3 className="dashboard-title">📚 Search Sessions ({userSessions.length})</h3>
        
        {sessionsLoading ? (
          <div className="loading-state"><span className="spinner"></span> Loading sessions...</div>
        ) : userSessions.length === 0 ? (
          <div className="card empty-state">
            <div className="empty-state-icon">🔍</div>
            <h3>No search sessions found</h3>
            <p>This user hasn't performed any searches yet.</p>
          </div>
        ) : (
          <div className="sessions-grid">
            {userSessions.map(session => (
              <div key={session.session_id} className="card session-card slide-up" onClick={() => setSelectedSession(session)}>
                <div className="session-header">
                  <h4 style={{ color: 'var(--accent-blue)' }}>{session.target_field}</h4>
                  <span className="session-date">{new Date(session.created_at).toLocaleDateString()}</span>
                </div>
                <div className="session-body">
                  <p><strong>🌍</strong> {session.target_countries?.join(', ')}</p>
                  <p><strong>🎓</strong> {session.degree_type}</p>
                  <p><strong>👨‍🏫</strong> {session.professors?.length || 0} professors found</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // ── Main Admin Panel ────────────────────────────────
  const adminCount = users.filter(u => u.role === 'admin').length;
  const userCount = users.filter(u => u.role === 'user').length;

  return (
    <div className="dashboard-container fade-in">
      <h2 className="dashboard-title">🛡️ Admin Dashboard</h2>
      
      {/* Stats Bar */}
      <div className="admin-stats-bar">
        <div className="admin-stat-card">
          <div className="admin-stat-value">{users.length}</div>
          <div className="admin-stat-label">Total Users</div>
        </div>
        <div className="admin-stat-card">
          <div className="admin-stat-value">{adminCount}</div>
          <div className="admin-stat-label">Admins</div>
        </div>
        <div className="admin-stat-card">
          <div className="admin-stat-value">{userCount}</div>
          <div className="admin-stat-label">Regular Users</div>
        </div>
      </div>

      {/* Search Bar */}
      <div className="admin-search-bar">
        <input 
          type="text" 
          placeholder="🔍 Search users by name or email..." 
          value={searchQuery} 
          onChange={e => setSearchQuery(e.target.value)}
        />
      </div>

      {/* Users Table */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <table className="admin-table">
          <thead>
            <tr>
              <th>User</th>
              <th>Email</th>
              <th>Role</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.map(user => (
              <tr key={user.id}>
                <td>
                  {editingUser === user.id ? (
                    <input 
                      value={editForm.name} 
                      onChange={e => setEditForm({...editForm, name: e.target.value})} 
                      style={{ width: '100%' }}
                    />
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <div className="user-avatar">{user.name?.charAt(0)?.toUpperCase()}</div>
                      <strong>{user.name}</strong>
                    </div>
                  )}
                </td>
                <td>
                  {editingUser === user.id ? (
                    <input 
                      value={editForm.email} 
                      onChange={e => setEditForm({...editForm, email: e.target.value})} 
                      style={{ width: '100%' }}
                    />
                  ) : (
                    <span style={{ color: 'var(--text-secondary)' }}>{user.email}</span>
                  )}
                </td>
                <td>
                  {editingUser === user.id ? (
                    <select 
                      value={editForm.role}
                      onChange={e => setEditForm({...editForm, role: e.target.value})}
                    >
                      <option value="user">User</option>
                      <option value="admin">Admin</option>
                    </select>
                  ) : (
                    <span className={`role-badge ${user.role}`}>{user.role}</span>
                  )}
                </td>
                <td style={{ textAlign: 'right' }}>
                  {editingUser === user.id ? (
                    <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                      <button className="btn btn-primary btn-sm" onClick={() => saveEdit(user.id)} disabled={saving}>
                        {saving ? 'Saving...' : '✓ Save'}
                      </button>
                      <button className="btn btn-secondary btn-sm" onClick={() => setEditingUser(null)}>Cancel</button>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                      <button className="btn btn-secondary btn-sm" onClick={() => handleViewUser(user)}>
                        👁️ View
                      </button>
                      <button className="btn btn-secondary btn-sm" onClick={() => handleEdit(user)}>
                        ✏️ Edit
                      </button>
                      <button 
                        className="btn btn-sm"
                        style={{ border: '1px solid rgba(239,68,68,0.3)', color: 'var(--accent-red)', background: 'rgba(239,68,68,0.06)' }}
                        onClick={() => handleDelete(user.id)}
                      >
                        🗑️
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filteredUsers.length === 0 && (
          <div className="empty-state">
            <div className="empty-state-icon">👥</div>
            <h3>No users found</h3>
            <p>{searchQuery ? 'Try a different search term.' : 'No users have registered yet.'}</p>
          </div>
        )}
      </div>
    </div>
  );
}
