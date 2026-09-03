import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { loginOfficer, getCheckpoints } from '../services/api';

export default function LoginPage({ setUser }) {
  const [badgeId, setBadgeId] = useState('SSB-7741');
  const [password, setPassword] = useState('officer123');
  const [checkpoint, setCheckpoint] = useState('Raxaul Checkpoint Unit A');
  const [checkpointsList, setCheckpointsList] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showDemoProfiles, setShowDemoProfiles] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    getCheckpoints()
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setCheckpointsList(data);
          setCheckpoint(data[0].name || data[0].location || 'Raxaul Checkpoint Unit A');
        }
      })
      .catch(() => {
        setCheckpointsList([
          { id: '1', checkpoint_code: 'CP-RAXAUL-01', name: 'Raxaul Checkpoint Unit A' },
          { id: '2', checkpoint_code: 'CP-RANIGANJ-01', name: 'Raniganj Integrated Checkpost' },
          { id: '3', checkpoint_code: 'CP-PANITANKI-01', name: 'Panitanki Land Port Unit' },
          { id: '4', checkpoint_code: 'CP-JAIGAON-01', name: 'Jaigaon Transit Gate' },
          { id: '5', checkpoint_code: 'CP-JOGBANI-01', name: 'Jogbani Screening Unit' }
        ]);
      });
  }, []);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await loginOfficer(badgeId, password);
      const userProfile = {
        ...data.user,
        checkpoint_location: checkpoint || data.user.checkpoint_location || 'Raxaul Checkpoint Unit A'
      };
      setUser(userProfile);
      localStorage.setItem('ssb_officer', JSON.stringify(userProfile));
      navigate('/scan');
    } catch (err) {
      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else if (!err.response) {
        setError('Server is waking up from sleep on Render free tier (~30-45s cold start). Please click Sign In again in a few seconds.');
      } else {
        setError('Authentication failed. Please check your credentials.');
      }
    } finally {
      setLoading(false);
    }
  };

  const setDemoAccount = (badge, pass, loc) => {
    setBadgeId(badge);
    setPassword(pass);
    if (loc) setCheckpoint(loc);
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
        maxWidth: '380px', width: '100%', backgroundColor: '#fff',
        border: '1px solid #d9dee7', borderRadius: '6px', padding: '32px 28px',
        boxShadow: '0 1px 4px rgba(0,0,0,0.03)',
      }}>
        {/* Branding */}
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div style={{
            width: '38px', height: '38px', borderRadius: '6px',
            backgroundColor: '#1f4e79', color: '#fff',
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '12px', fontWeight: 700, letterSpacing: '0.5px', marginBottom: '12px',
          }}>SSB</div>
          <h1 style={{ fontSize: '16px', fontWeight: 600, color: '#1f2937', margin: '0 0 2px' }}>
            Document Screening System
          </h1>
          <p style={{ fontSize: '12px', color: '#64748b', margin: 0 }}>
            Officer Authentication
          </p>
        </div>

        {error && (
          <div style={{
            padding: '8px 12px', backgroundColor: '#fef2f2', border: '1px solid #fee2e2',
            borderRadius: '4px', color: '#991b1b', fontSize: '12px', marginBottom: '14px',
          }}>{error}</div>
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

          <div style={{ marginBottom: '6px' }}>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: 500, color: '#334155', marginBottom: '4px' }}>
              Checkpoint
            </label>
            <select
              value={checkpoint}
              onChange={(e) => setCheckpoint(e.target.value)}
              style={{ ...inputStyle, cursor: 'pointer' }}
            >
              {checkpointsList.map((cp) => (
                <option key={cp.id} value={cp.name || cp.location}>
                  {cp.name || cp.location}
                </option>
              ))}
            </select>
          </div>

          <button type="submit" disabled={loading} style={{
            width: '100%', padding: '9px 16px', fontSize: '13px', fontWeight: 500,
            backgroundColor: '#1f4e79', color: '#fff', border: 'none',
            borderRadius: '4px', cursor: 'pointer', marginTop: '18px',
            fontFamily: "'Inter', system-ui, sans-serif",
            opacity: loading ? 0.6 : 1,
          }}>
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        {/* Demo accounts — subtle */}
        <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid #e2e8f0' }}>
          <button
            type="button"
            onClick={() => setShowDemoProfiles(!showDemoProfiles)}
            style={{
              width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              background: 'none', border: 'none', cursor: 'pointer', padding: 0,
              fontSize: '11px', fontWeight: 500, color: '#64748b', marginBottom: '8px',
              fontFamily: "'Inter', system-ui, sans-serif",
            }}
          >
            <span>Demo accounts</span>
            <span style={{ fontSize: '10px' }}>{showDemoProfiles ? '▲' : '▼'}</span>
          </button>

          {showDemoProfiles && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
              {[
                { label: 'Border Officer', badge: 'SSB-7741', pass: 'officer123', loc: 'Raxaul Checkpost Unit A (Sec-01)' },
                { label: 'Supervisor', badge: 'SSB-1002', pass: 'super123', loc: 'Raniganj Integrated Checkpost (Sec-02)' },
                { label: 'Senior Analyst', badge: 'SSB-5099', pass: 'analyst123', loc: 'Panitanki Land Port Unit (Sec-03)' },
                { label: 'Commandant', badge: 'SSB-0001', pass: 'admin123', loc: 'Raxaul Checkpost Unit A (Sec-01)' },
              ].map((persona) => (
                <button
                  key={persona.badge}
                  type="button"
                  onClick={() => setDemoAccount(persona.badge, persona.pass, persona.loc)}
                  style={{
                    textAlign: 'left', padding: '6px 10px', width: '100%',
                    border: '1px solid #e2e8f0', borderRadius: '4px',
                    backgroundColor: '#f8fafc', cursor: 'pointer', fontSize: '11px',
                    color: '#334155', fontFamily: "'Inter', system-ui, sans-serif",
                  }}
                >
                  <div style={{ fontWeight: 500, color: '#1f2937' }}>{persona.label}</div>
                  <div style={{ fontSize: '10px', color: '#64748b' }}>{persona.badge}</div>
                </button>
              ))}
            </div>
          )}
        </div>

        <div style={{ textAlign: 'center', marginTop: '16px', fontSize: '11px', color: '#94a3b8' }}>
          Local processing enabled · No external API required
        </div>
      </div>
    </div>
  );
}
