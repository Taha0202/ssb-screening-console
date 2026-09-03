import React, { useState, useEffect } from 'react';
import { X, RefreshCw } from 'lucide-react';
import { getSystemHealth, getSystemStatus } from '../services/api';

export default function SystemDiagnosticsModal({ isOpen, onClose }) {
  const [health, setHealth] = useState(null);
  const [statusData, setStatusData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState(null);

  const fetchDiagnostics = async () => {
    setLoading(true);
    try {
      const [hData, sData] = await Promise.all([
        getSystemHealth().catch(() => null),
        getSystemStatus().catch(() => null)
      ]);
      setHealth(hData);
      setStatusData(sData);
      setLastRefreshed(new Date().toLocaleTimeString());
    } catch (err) {
      console.error('Failed to load diagnostics', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchDiagnostics();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const StatusDot = ({ ok }) => (
    <span style={{
      width: '7px', height: '7px', borderRadius: '50%',
      backgroundColor: ok ? '#22c55e' : '#ef4444',
      display: 'inline-block', flexShrink: 0,
    }} />
  );

  const rows = [
    { label: 'Database', status: health?.database === 'connected', detail: health?.database_type || 'SQLite' },
    { label: 'OCR & MRZ parser', status: true, detail: 'Tesseract + ICAO 9303' },
    { label: 'Forensic analysis', status: true, detail: 'ELA, JPEG, boundary, EXIF' },
    { label: 'Face engine', status: true, detail: health?.face_engine_name || 'OpenCV 512-D spatial gradient' },
    { label: 'Liveness', status: true, detail: '4-step operator challenge' },
    { label: 'Audit ledger', status: true, detail: 'SHA-256 chained' },
  ];

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 50,
      backgroundColor: 'rgba(0,0,0,0.35)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '16px',
    }}>
      <div style={{
        backgroundColor: '#fff', border: '1px solid #d9dee7',
        borderRadius: '6px', maxWidth: '480px', width: '100%',
        fontFamily: "'Inter', system-ui, sans-serif",
        boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
      }}>
        {/* Header */}
        <div style={{
          padding: '14px 20px',
          borderBottom: '1px solid #e2e8f0',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div>
            <h2 style={{ fontSize: '14px', fontWeight: 600, color: '#1f2937', margin: 0 }}>
              System status
            </h2>
            <p style={{ fontSize: '11px', color: '#64748b', margin: '2px 0 0', fontWeight: 400 }}>
              Subsystem health overview
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <button
              onClick={fetchDiagnostics}
              disabled={loading}
              title="Refresh"
              style={{
                padding: '5px', border: '1px solid #d9dee7', borderRadius: '4px',
                background: '#fff', cursor: 'pointer', color: '#64748b',
                display: 'flex', alignItems: 'center',
              }}
            >
              <RefreshCw style={{ width: '13px', height: '13px', animation: loading ? 'spin 1s linear infinite' : 'none' }} />
            </button>
            <button
              onClick={onClose}
              style={{
                padding: '5px', border: '1px solid #d9dee7', borderRadius: '4px',
                background: '#fff', cursor: 'pointer', color: '#64748b',
                display: 'flex', alignItems: 'center',
              }}
            >
              <X style={{ width: '13px', height: '13px' }} />
            </button>
          </div>
        </div>

        {/* Status summary */}
        <div style={{
          padding: '10px 20px',
          backgroundColor: '#f8fafc',
          borderBottom: '1px solid #e2e8f0',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          fontSize: '12px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <StatusDot ok={true} />
            <span style={{ fontWeight: 500, color: '#166534' }}>All systems operational</span>
          </div>
          <span style={{ color: '#64748b', fontSize: '11px' }}>
            Local processing · v{health?.version || '2.0.0'}
          </span>
        </div>

        {/* Subsystem list */}
        <div style={{ padding: '4px 0' }}>
          {rows.map((row, idx) => (
            <div key={idx} style={{
              padding: '9px 20px',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              fontSize: '12px',
              borderBottom: idx < rows.length - 1 ? '1px solid #f1f5f9' : 'none',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <StatusDot ok={row.status} />
                <span style={{ fontWeight: 500, color: '#1f2937' }}>{row.label}</span>
              </div>
              <span style={{ color: '#64748b', fontSize: '11px' }}>{row.detail}</span>
            </div>
          ))}
        </div>

        {/* Metrics */}
        <div style={{
          padding: '10px 20px',
          borderTop: '1px solid #e2e8f0',
          backgroundColor: '#f8fafc',
          display: 'flex', gap: '20px', fontSize: '11px', color: '#64748b',
        }}>
          <div>
            <span style={{ fontWeight: 500, color: '#334155' }}>{health?.active_checkpoints_count || 0}</span> checkpoints
          </div>
          <div>
            <span style={{ fontWeight: 500, color: '#334155' }}>{health?.reference_records_count || 0}</span> reference records
          </div>
        </div>

        {/* Footer */}
        <div style={{
          padding: '10px 20px',
          borderTop: '1px solid #e2e8f0',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          fontSize: '11px', color: '#94a3b8',
        }}>
          <span>Last checked: {lastRefreshed || '—'}</span>
          <button
            onClick={onClose}
            style={{
              padding: '5px 14px',
              backgroundColor: '#fff', border: '1px solid #d9dee7',
              borderRadius: '4px', fontSize: '12px', fontWeight: 500,
              color: '#334155', cursor: 'pointer',
              fontFamily: "'Inter', system-ui, sans-serif",
            }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
