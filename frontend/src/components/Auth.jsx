import { useState } from 'react';

export default function Auth({ onLoginSuccess, mode = 'user' }) {
  const isAdminMode = mode === 'admin';
  const [isLogin, setIsLogin] = useState(isAdminMode ? true : true);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const url = isLogin ? '/api/auth/login' : '/api/auth/register';
    const body = isLogin 
      ? JSON.stringify({ email, password })
      : JSON.stringify({ email, password, name });

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Authentication failed');
      }

      // Admin mode: reject non-admin accounts
      if (isAdminMode && data.role !== 'admin') {
        throw new Error('Access denied. This portal is for administrators only.');
      }

      // Save token and user info
      localStorage.setItem('auth_token', data.access_token);
      localStorage.setItem('user_name', data.name);
      localStorage.setItem('user_role', data.role || 'user');
      
      onLoginSuccess({ name: data.name, token: data.access_token, role: data.role || 'user' });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-brand">
        <h1>ProfFinder</h1>
        <p>{isAdminMode ? 'Administrator Control Panel' : 'AI-powered professor matching for graduate school applications'}</p>
      </div>

      <div className={`auth-card ${isAdminMode ? 'admin-mode' : ''} slide-up`}>
        {isAdminMode && (
          <div style={{ textAlign: 'center' }}>
            <span className="admin-badge">🛡️ Admin Portal</span>
          </div>
        )}
        
        <h2 className="auth-title">
          {isAdminMode ? 'Admin Sign In' : (isLogin ? 'Welcome Back' : 'Create Account')}
        </h2>
        <p className="auth-subtitle">
          {isAdminMode 
            ? 'Enter your administrator credentials'
            : (isLogin ? 'Log in to continue your search' : 'Start finding your perfect professor')}
        </p>

        {error && (
          <div className="auth-error">
            <span>⚠️</span> {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {!isLogin && !isAdminMode && (
            <div className="auth-input-group">
              <label>Full Name</label>
              <span className="auth-input-icon">👤</span>
              <input 
                type="text" 
                value={name} 
                onChange={e => setName(e.target.value)} 
                required={!isLogin}
                placeholder="John Doe"
              />
            </div>
          )}
          
          <div className="auth-input-group">
            <label>Email Address</label>
            <span className="auth-input-icon">✉️</span>
            <input 
              type="email" 
              value={email} 
              onChange={e => setEmail(e.target.value)} 
              required
              placeholder={isAdminMode ? 'admin@proffinder.com' : 'john@example.com'}
            />
          </div>

          <div className="auth-input-group">
            <label>Password</label>
            <span className="auth-input-icon">🔒</span>
            <input 
              type={showPassword ? 'text' : 'password'}
              value={password} 
              onChange={e => setPassword(e.target.value)} 
              required
              placeholder="••••••••"
            />
            <button 
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              style={{ 
                position: 'absolute', right: '14px', top: '40px',
                background: 'none', border: 'none', color: 'var(--text-muted)',
                cursor: 'pointer', fontSize: '0.8rem', fontFamily: 'Inter, sans-serif'
              }}
            >
              {showPassword ? 'Hide' : 'Show'}
            </button>
          </div>

          <button 
            type="submit" 
            className="btn btn-primary auth-submit" 
            disabled={loading}
          >
            {loading ? (
              <><span className="spinner"></span> Please wait...</>
            ) : (
              isAdminMode ? '🛡️ Access Admin Panel' : (isLogin ? 'Log In' : 'Create Account')
            )}
          </button>
        </form>

        {!isAdminMode && (
          <div className="auth-toggle">
            {isLogin ? "Don't have an account? " : "Already have an account? "}
            <button onClick={() => { setIsLogin(!isLogin); setError(null); }}>
              {isLogin ? 'Sign up' : 'Log in'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
