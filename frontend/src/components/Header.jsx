import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { LogOut, MapPin } from 'lucide-react';
import { getSystemStatus, getCheckpoints, DEFAULT_CHECKPOINTS } from '../services/api';
import SystemDiagnosticsModal from './SystemDiagnosticsModal';

export default function Header({ user, setUser }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [sysStatus, setSysStatus] = useState(null);
  const [isDiagOpen, setIsDiagOpen] = useState(false);
  const [checkpoints, setCheckpoints] = useState(DEFAULT_CHECKPOINTS);
  const [selectedCp, setSelectedCp] = useState(DEFAULT_CHECKPOINTS[0]);

  useEffect(() => {
    getSystemStatus()
      .then((data) => setSysStatus(data))
      .catch((err) => {
        console.warn('System status probe fallback:', err);
      });

    getCheckpoints()
      .then((cps) => {
        if (Array.isArray(cps) && cps.length > 0) {
          setCheckpoints(cps);
          if (user && user.checkpoint_id) {
            const current = cps.find(c => c.id === user.checkpoint_id);
            if (current) setSelectedCp(current);
          } else if (cps.length > 0) {
            setSelectedCp(cps[0]);
          }
        }
      })
      .catch(() => {});
  }, [user]);

  const handleCheckpointChange = (e) => {
    const cpId = e.target.value;
    const found = checkpoints.find(c => c.id === cpId);
    if (found) {
      setSelectedCp(found);
      const updatedUser = {
        ...user,
        checkpoint_id: found.id,
        checkpoint_location: found.name
      };
      setUser(updatedUser);
      localStorage.setItem('ssb_officer', JSON.stringify(updatedUser));
    }
  };

  const handleLogout = () => {
    sessionStorage.setItem('ssb_logged_out', 'true');
    localStorage.removeItem('ssb_officer');
    setUser(null);
    navigate('/login');
  };

  const isScanActive = location.pathname.startsWith('/scan') || location.pathname.startsWith('/review');
  const isAuditActive = location.pathname.startsWith('/audit');
  const isSupervisor = user?.role === 'SUPERVISOR' || user?.role === 'ADMIN';

  return (
    <>
      <header style={{
        height: '56px',
        backgroundColor: '#fff',
        borderBottom: '1px solid #d9dee7',
        color: '#1f2937',
        padding: '0 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'sticky',
        top: 0,
        zIndex: 40,
        fontFamily: "'Inter', system-ui, sans-serif",
      }}>
        {/* Left: Branding */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '32px', height: '32px',
            borderRadius: '6px',
            backgroundColor: '#1f4e79',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#fff',
            fontSize: '11px',
            fontWeight: 700,
            letterSpacing: '0.5px',
            flexShrink: 0,
          }}>
            SSB
          </div>
          <div style={{ lineHeight: 1.3 }}>
            <div style={{ fontSize: '13px', fontWeight: 600, color: '#1f2937' }}>
              Sashastra Seema Bal
            </div>
            <div style={{ fontSize: '11px', color: '#64748b', fontWeight: 400 }}>
              MHA · Identity & Document Screening
            </div>
          </div>
        </div>

        {/* Center: Navigation */}
        {user && (
          <nav style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Link
              to="/scan"
              style={{
                padding: '8px 16px',
                fontSize: '13px',
                fontWeight: 500,
                color: isScanActive ? '#1f4e79' : '#64748b',
                borderBottom: isScanActive ? '2px solid #1f4e79' : '2px solid transparent',
                textDecoration: 'none',
              }}
            >
              Screening
            </Link>
            <Link
              to="/audit"
              style={{
                padding: '8px 16px',
                fontSize: '13px',
                fontWeight: 500,
                color: isAuditActive ? '#1f4e79' : '#64748b',
                borderBottom: isAuditActive ? '2px solid #1f4e79' : '2px solid transparent',
                textDecoration: 'none',
              }}
            >
              Audit Trail
            </Link>
          </nav>
        )}

        {/* Right: Officer info */}
        {user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            {/* System status — very subtle */}
            <button
              onClick={() => setIsDiagOpen(true)}
              style={{
                display: 'flex', alignItems: 'center', gap: '5px',
                fontSize: '11px', color: '#64748b', fontWeight: 400,
                background: '#fff', border: '1px solid #d9dee7', borderRadius: '4px',
                padding: '4px 10px', cursor: 'pointer',
                fontFamily: "'Inter', system-ui, sans-serif",
              }}
              title="System Diagnostics"
            >
              <span style={{
                width: '6px', height: '6px', borderRadius: '50%',
                backgroundColor: '#166534', flexShrink: 0,
              }} />
              Offline
            </button>

            {/* Checkpoint */}
            <div style={{
              display: 'flex', alignItems: 'center', gap: '4px',
              fontSize: '12px', color: '#64748b',
            }}>
              <MapPin style={{ width: '13px', height: '13px', color: '#94a3b8' }} />
              {isSupervisor && checkpoints.length > 0 ? (
                <select
                  value={selectedCp?.id || ''}
                  onChange={handleCheckpointChange}
                  style={{
                    background: 'none', border: 'none',
                    fontSize: '12px', color: '#374151', fontWeight: 500,
                    cursor: 'pointer', outline: 'none', maxWidth: '180px',
                    fontFamily: "'Inter', system-ui, sans-serif",
                  }}
                  title="Checkpoint Selector"
                >
                  {checkpoints.map((cp) => (
                    <option key={cp.id} value={cp.id}>
                      {cp.name}
                    </option>
                  ))}
                </select>
              ) : (
                <span style={{ fontWeight: 500, color: '#374151', maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {user.checkpoint_location || selectedCp?.name || 'Raxaul'}
                </span>
              )}
            </div>

            {/* Officer */}
            <div style={{
              borderLeft: '1px solid #d9dee7', paddingLeft: '14px',
              display: 'flex', alignItems: 'center', gap: '10px',
            }}>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '12px', fontWeight: 500, color: '#1f2937' }}>
                  {user.full_name || 'Inspector R. K. Sharma'}
                </div>
                <div style={{ fontSize: '11px', color: '#64748b' }}>
                  {user.badge_id || 'SSB-7741'} · {user.role || 'Officer'}
                </div>
              </div>

              <button
                onClick={handleLogout}
                title="Sign Out"
                style={{
                  padding: '5px',
                  color: '#64748b',
                  background: '#fff',
                  border: '1px solid #d9dee7',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}
              >
                <LogOut style={{ width: '13px', height: '13px' }} />
              </button>
            </div>
          </div>
        )}
      </header>

      <SystemDiagnosticsModal
        isOpen={isDiagOpen}
        onClose={() => setIsDiagOpen(false)}
      />
    </>
  );
}
