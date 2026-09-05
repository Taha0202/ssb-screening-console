import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  loginOfficer,
  getCheckpoints,
  DEFAULT_CHECKPOINTS,
  DEMO_PERSONAS,
  getApiBaseUrl,
  setCustomApiUrl,
  getSystemHealth
} from '../services/api';

export default function LoginPage({ setUser }) {
  const [badgeId, setBadgeId] = useState('SSB-7741');
  const [password, setPassword] = useState('officer123');
  const [checkpoint, setCheckpoint] = useState(DEFAULT_CHECKPOINTS[0].name);
  const [checkpointsList, setCheckpointsList] = useState(DEFAULT_CHECKPOINTS);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showDemoProfiles, setShowDemoProfiles] = useState(true);

  // Backend connection settings
  const [showApiConfig, setShowApiConfig] = useState(false);
  const [apiUrlInput, setApiUrlInput] = useState(getApiBaseUrl());
  const [connectionStatus, setConnectionStatus] = useState('checking'); // 'connected', 'offline', 'checking'
  const navigate = useNavigate();

  // Test backend connectivity on mount
  useEffect(() => {
    let isMounted = true;
    getSystemHealth()
      .then((health) => {
        if (isMounted) {
          setConnectionStatus(health.status === 'ONLINE' ? 'connected' : 'offline');
        }
      })
      .catch(() => {
        if (isMounted) setConnectionStatus('offline');
      });

    getCheckpoints()
      .then((data) => {
        if (isMounted && Array.isArray(data) && data.length > 0) {
          setCheckpointsList(data);
          if (!checkpoint) {
            setCheckpoint(data[0].name || data[0].location || DEFAULT_CHECKPOINTS[0].name);
          }
        }
      })
      .catch(() => {
        if (isMounted) setCheckpointsList(DEFAULT_CHECKPOINTS);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const handleLogin = async (e, customBadge = null, customPass = null, customLoc = null) => {
    if (e) e.preventDefault();
    setError('');
    setLoading(true);

    const targetBadge = customBadge || badgeId;
    const targetPass = customPass || password;
    const targetLoc = customLoc || checkpoint || 'Raxaul Checkpoint Unit A';

    try {
      const data = await loginOfficer(targetBadge, targetPass);
      const userProfile = {
        ...data.user,
        checkpoint_location: targetLoc || data.user?.checkpoint_location || 'Raxaul Checkpoint Unit A'
      };
      sessionStorage.removeItem('ssb_logged_out');
      localStorage.setItem('ssb_officer', JSON.stringify(userProfile));
      setUser(userProfile);
      navigate('/scan', { replace: true });
    } catch (err) {
      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else if (!err.response) {
        setError('Backend is waking up or offline. You can use any Demo Account below for instant access.');
      } else {
        setError('Authentication failed. Please check your credentials.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = (persona) => {
    setBadgeId(persona.badge);
    setPassword(persona.pass);
    setCheckpoint(persona.loc);
    handleLogin(null, persona.badge, persona.pass, persona.loc);
  };

  const handleSaveApiUrl = async () => {
    setCustomApiUrl(apiUrlInput);
    setConnectionStatus('checking');
    try {
      const health = await getSystemHealth();
      setConnectionStatus(health.status === 'ONLINE' ? 'connected' : 'offline');
    } catch {
      setConnectionStatus('offline');
    }
  };

  const inputStyle = {
    width: '100%', padding: '8px 12px', fontSize: '13px',
    border: '1px solid #d9dee7', borderRadius: '4px',
    backgroundColor: '#fff', color: '#1f2937', outline: 'none',
    fontFamily: "'Inter', system-ui, sans-serif",
  };

  return (
    <div style={{
      minHeight: 'calc(100vh - 56px)', display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '24px 16px', backgroundColor: '#f7f8fa', fontFamily: "'Inter', system-ui, sans-serif",
    }}>
      <div style={{
        maxWidth: '420px', width: '100%', backgroundColor: '#fff',
        border: '1px solid #d9dee7', borderRadius: '8px', padding: '32px 28px',
        boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
      }}>
        {/* Branding */}
        <div style={{ textAlign: 'center', marginBottom: '22px' }}>
          <div style={{
            width: '42px', height: '42px', borderRadius: '8px',
            backgroundColor: '#1f4e79', color: '#fff',
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '13px', fontWeight: 700, letterSpacing: '0.5px', marginBottom: '10px',
          }}>SSB</div>
          <h1 style={{ fontSize: '17px', fontWeight: 600, color: '#1f2937', margin: '0 0 2px' }}>
            Document Screening System
          </h1>
          <p style={{ fontSize: '12px', color: '#64748b', margin: 0 }}>
            Sashastra Seema Bal · Officer Authentication
          </p>
        </div>

        {error && (
          <div style={{
            padding: '10px 12px', backgroundColor: '#fef2f2', border: '1px solid #fee2e2',
            borderRadius: '6px', color: '#991b1b', fontSize: '12px', marginBottom: '16px',
            lineHeight: 1.4
          }}>
            {error}
          </div>
        )}

        <form onSubmit={handleLogin}>
          <div style={{ marginBottom: '14px' }}>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: 500, color: '#334155', marginBottom: '4px' }}>
              Badge ID
            </label>
            <input
              type="text"
              required
              value={badgeId}
              onChange={(e) => setBadgeId(e.target.value)}
              placeholder="e.g. SSB-7741"
              style={inputStyle}
            />
          </div>

          <div style={{ marginBottom: '14px' }}>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: 500, color: '#334155', marginBottom: '4px' }}>
              Password
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              style={inputStyle}
            />
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: 500, color: '#334155', marginBottom: '4px' }}>
              Checkpoint
            </label>
            <select
              value={checkpoint}
              onChange={(e) => setCheckpoint(e.target.value)}
              style={{ ...inputStyle, cursor: 'pointer' }}
            >
              {checkpointsList.map((cp) => (
                <option key={cp.id || cp.checkpoint_code} value={cp.name || cp.location}>
                  {cp.name || cp.location} {cp.checkpoint_code ? `(${cp.checkpoint_code})` : ''}
                </option>
              ))}
            </select>
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%', padding: '10px 16px', fontSize: '13px', fontWeight: 600,
              backgroundColor: '#1f4e79', color: '#fff', border: 'none',
              borderRadius: '6px', cursor: 'pointer',
              fontFamily: "'Inter', system-ui, sans-serif",
              opacity: loading ? 0.7 : 1,
              transition: 'background-color 0.15s ease'
            }}
          >
            {loading ? 'Authenticating…' : 'Sign in to Workstation'}
          </button>
        </form>

        {/* Demo profiles */}
        <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid #e2e8f0' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
            <span style={{ fontSize: '11px', fontWeight: 600, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              One-Click Demo Personas
            </span>
            <button
              type="button"
              onClick={() => setShowDemoProfiles(!showDemoProfiles)}
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                fontSize: '11px', color: '#64748b'
              }}
            >
              {showDemoProfiles ? 'Hide' : 'Show'}
            </button>
          </div>

          {showDemoProfiles && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              {DEMO_PERSONAS.map((persona) => (
                <button
                  key={persona.badge}
                  type="button"
                  onClick={() => handleQuickLogin(persona)}
                  disabled={loading}
                  title={`Click for instant demo login as ${persona.name}`}
                  style={{
                    textAlign: 'left', padding: '8px 10px', width: '100%',
                    border: '1px solid #e2e8f0', borderRadius: '6px',
                    backgroundColor: '#f8fafc', cursor: 'pointer', fontSize: '11px',
                    color: '#334155', fontFamily: "'Inter', system-ui, sans-serif",
                    display: 'flex', flexDirection: 'column', gap: '2px',
                    transition: 'all 0.15s ease'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.borderColor = '#1f4e79'}
                  onMouseLeave={(e) => e.currentTarget.style.borderColor = '#e2e8f0'}
                >
                  <div style={{ fontWeight: 600, color: '#1f2937' }}>{persona.label}</div>
                  <div style={{ fontSize: '10px', color: '#64748b' }}>{persona.badge}</div>
                  <div style={{ fontSize: '10px', color: '#0284c7', fontWeight: 500, marginTop: '2px' }}>
                    Instant Login →
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Backend API status & URL drawer */}
        <div style={{ marginTop: '16px', paddingTop: '12px', borderTop: '1px dashed #e2e8f0' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: '#64748b' }}>
              <span style={{
                width: '7px', height: '7px', borderRadius: '50%',
                backgroundColor: connectionStatus === 'connected' ? '#10b981' : connectionStatus === 'checking' ? '#f59e0b' : '#ef4444'
              }}></span>
              <span>
                {connectionStatus === 'connected' ? 'Backend Online' : connectionStatus === 'checking' ? 'Checking Backend…' : 'Offline / Standalone Mode'}
              </span>
            </div>
            <button
              type="button"
              onClick={() => setShowApiConfig(!showApiConfig)}
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                fontSize: '11px', color: '#1f4e79', textDecoration: 'underline'
              }}
            >
              {showApiConfig ? 'Close' : 'Config API'}
            </button>
          </div>

          {showApiConfig && (
            <div style={{ marginTop: '10px', padding: '10px', backgroundColor: '#f1f5f9', borderRadius: '6px', fontSize: '11px' }}>
              <label style={{ display: 'block', fontWeight: 500, color: '#334155', marginBottom: '4px' }}>
                FastAPI Backend URL:
              </label>
              <div style={{ display: 'flex', gap: '6px' }}>
                <input
                  type="text"
                  value={apiUrlInput}
                  onChange={(e) => setApiUrlInput(e.target.value)}
                  placeholder="https://your-backend.onrender.com/api/v1"
                  style={{ ...inputStyle, padding: '5px 8px', fontSize: '11px' }}
                />
                <button
                  type="button"
                  onClick={handleSaveApiUrl}
                  style={{
                    padding: '5px 10px', backgroundColor: '#1f4e79', color: '#fff',
                    border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 500
                  }}
                >
                  Save
                </button>
              </div>
              <p style={{ margin: '6px 0 0', color: '#64748b', fontSize: '10px' }}>
                Leave empty or /api/v1 for local/relative proxy. Set to your Render URL when testing remote API.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
