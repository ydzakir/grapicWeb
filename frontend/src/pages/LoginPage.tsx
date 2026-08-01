import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Activity, Lock, User as UserIcon, AlertCircle, Shield, Key, ExternalLink } from 'lucide-react';
import { apiClient } from '../services/apiClient';

export const LoginPage: React.FC = () => {
  const [authMode, setAuthMode] = useState<'local' | 'ldap'>('local');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Check for OIDC Callback code in URL
  useEffect(() => {
    const oidcCode = searchParams.get('code');
    if (oidcCode) {
      handleOidcCallback(oidcCode);
    }
  }, [searchParams]);

  const handleOidcCallback = async (code: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.post<any>('/auth/oidc/callback', { code });
      login(data.access_token, data.user);
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'OIDC Single Sign-On authentication failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleOidcAuthorize = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<any>('/auth/oidc/authorize');
      if (data.authorization_url) {
        window.location.href = data.authorization_url;
      }
    } catch (err: any) {
      setError('Could not initialize OIDC Single Sign-On URL.');
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      let data: any;
      if (authMode === 'ldap') {
        data = await apiClient.post<any>('/auth/ldap/login', { username, password });
      } else {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const resp = await fetch('/api/v1/auth/token', {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: formData.toString(),
          credentials: 'include',
        });

        if (!resp.ok) {
          const errData = await resp.json().catch(() => ({}));
          throw new Error(errData?.error?.message || errData?.detail || 'Invalid credentials');
        }
        data = await resp.json();
      }

      const token = data.access_token;
      // Fetch user profile using the HttpOnly cookie / bearer token
      const userResp = await fetch('/api/v1/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
        credentials: 'include',
      });
      const userData = await userResp.json();

      login(token, userData);
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <div className="login-logo">
            <Activity className="login-icon" />
          </div>
          <h2>Enterprise Infrastructure Monitoring</h2>
          <p>Multi-Driver SSO, LDAP / Active Directory &amp; RBAC Access System</p>
        </div>

        {error && (
          <div className="alert-error" role="alert">
            <AlertCircle className="alert-icon" />
            <span>{error}</span>
          </div>
        )}

        {/* Enterprise OIDC Single Sign-On Button */}
        <div className="sso-section" style={{ marginBottom: '16px' }}>
          <button
            type="button"
            className="btn-secondary btn-block"
            onClick={handleOidcAuthorize}
            disabled={loading}
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', padding: '10px' }}
          >
            <Shield className="icon-blue" size={18} />
            <span>Login with Enterprise OIDC / Single Sign-On</span>
            <ExternalLink size={14} />
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: '16px 0', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
          <div style={{ flex: 1, height: '1px', background: 'var(--border-subtle)' }} />
          <span>OR USE DIRECT LOGIN</span>
          <div style={{ flex: 1, height: '1px', background: 'var(--border-subtle)' }} />
        </div>

        {/* Driver Selector Tabs */}
        <div className="admin-tabs" style={{ marginBottom: '16px' }}>
          <button
            type="button"
            className={`tab-btn ${authMode === 'local' ? 'active' : ''}`}
            onClick={() => setAuthMode('local')}
            style={{ padding: '6px 12px', fontSize: '0.85rem' }}
          >
            <Key size={14} className="tab-icon" /> Local Fallback
          </button>
          <button
            type="button"
            className={`tab-btn ${authMode === 'ldap' ? 'active' : ''}`}
            onClick={() => setAuthMode('ldap')}
            style={{ padding: '6px 12px', fontSize: '0.85rem' }}
          >
            <Shield size={14} className="tab-icon" /> LDAP / Active Directory
          </button>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="username">
              {authMode === 'ldap' ? 'LDAP Username / Principal' : 'Username or Email'}
            </label>
            <div className="input-with-icon">
              <UserIcon className="input-icon" />
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder={authMode === 'ldap' ? 'ldapuser@company.internal' : 'admin@infra.com'}
                required
                disabled={loading}
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <div className="input-with-icon">
              <Lock className="input-icon" />
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                required
                disabled={loading}
              />
            </div>
          </div>

          <button type="submit" className="btn-primary btn-block" disabled={loading}>
            {loading ? 'Authenticating...' : `Sign In (${authMode === 'ldap' ? 'LDAP / AD' : 'Local'})`}
          </button>
        </form>

        <div className="login-footer">
          <p className="demo-hint">
            Development demo credentials are configured via <code>BOOTSTRAP_ADMIN_PASSWORD</code> in the backend environment.
          </p>
        </div>
      </div>
    </div>
  );
};
