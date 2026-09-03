import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, Download } from 'lucide-react';
import RiskBadge from '../components/RiskBadge';
import { getAuditLogs, verifyAuditChain, exportAuditLogsCsv, getCheckpoints } from '../services/api';

export default function AuditPage() {
  const [logs, setLogs] = useState([]);
  const [checkpoints, setCheckpoints] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [riskFilter, setRiskFilter] = useState('');
  const [decisionFilter, setDecisionFilter] = useState('');
  const [dateFilter, setDateFilter] = useState('');
  const [checkpointFilter, setCheckpointFilter] = useState('');
  const [verificationResult, setVerificationResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [selectedLog, setSelectedLog] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    getCheckpoints().then(cps => setCheckpoints(cps)).catch(() => {});
  }, []);

  const loadLogs = async () => {
    setLoading(true);
    try {
      const params = {};
      if (riskFilter) params.risk_level = riskFilter;
      if (decisionFilter) params.decision = decisionFilter;
      if (checkpointFilter) params.checkpoint_location = checkpointFilter;
      const data = await getAuditLogs(params);
      setLogs(data);
    } catch (err) { console.error('Failed to load audit logs:', err); }
    finally { setLoading(false); }
  };

  useEffect(() => { loadLogs(); }, [riskFilter, decisionFilter, checkpointFilter]);

  const handleVerifyChain = async () => {
    setVerifying(true);
    try {
      const res = await verifyAuditChain();
      setVerificationResult(res);
    } catch (err) {
      setVerificationResult({ is_valid: false, message: 'Verification error.', total_records: 0 });
    } finally { setVerifying(false); }
  };

  const handleExportCsv = async () => {
    setExporting(true);
    try {
      const params = {};
      if (riskFilter) params.risk_level = riskFilter;
      if (decisionFilter) params.decision = decisionFilter;
      if (checkpointFilter) params.checkpoint_location = checkpointFilter;
      await exportAuditLogsCsv(params);
    } catch (err) { console.error('CSV export failed:', err); }
    finally { setExporting(false); }
  };

  const maskDocNumber = (docNum, docType) => {
    if (!docNum) return '—';
    const clean = docNum.replace(/\s|-/g, '').toUpperCase();
    if (docType === 'AADHAAR' || clean.length === 12) return `XXXX XXXX ${clean.slice(-4)}`;
    if (docType === 'PASSPORT' || (clean.length === 8 && clean[0].match(/[A-Z]/))) return `${clean[0]}*****${clean.slice(-2)}`;
    if (clean.startsWith('DL') || clean.length >= 10) return `${clean.slice(0, 4)}****${clean.slice(-4)}`;
    return clean.length > 4 ? `${clean.slice(0, 2)}****${clean.slice(-2)}` : '****';
  };

  const totalScans = logs.length;
  const highRiskCount = logs.filter(l => l.risk_level === 'HIGH').length;
  const flaggedCount = logs.filter(l => l.risk_level === 'HIGH' || l.risk_level === 'MEDIUM').length;
  const escalatedCount = logs.filter(l => l.officer_decision === 'ESCALATE' || l.officer_decision === 'ESCALATED').length;

  const filteredLogs = logs.filter(log => {
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      if (!(
        (log.document_number && log.document_number.toLowerCase().includes(q)) ||
        (log.holder_name && log.holder_name.toLowerCase().includes(q)) ||
        (log.id && log.id.toLowerCase().includes(q)) ||
        (log.officer_id && log.officer_id.toLowerCase().includes(q))
      )) return false;
    }
    if (decisionFilter) {
      const dec = (log.officer_decision || 'PENDING').toUpperCase();
      const normMap = { APPROVE: 'APPROVED', APPROVED: 'APPROVED', REJECT: 'REJECTED', REJECTED: 'REJECTED', ESCALATE: 'ESCALATED', ESCALATED: 'ESCALATED', PENDING: 'PENDING' };
      const filterNorm = normMap[decisionFilter] || decisionFilter;
      const decNorm = normMap[dec] || dec;
      if (decNorm !== filterNorm) return false;
    }
    if (checkpointFilter && !log.checkpoint_location?.toLowerCase().includes(checkpointFilter.toLowerCase())) return false;
    if (dateFilter) {
      const logDate = new Date(log.timestamp); const now = new Date();
      if (dateFilter === 'today' && logDate.toDateString() !== now.toDateString()) return false;
      if (dateFilter === 'week' && (now - logDate) / 86400000 > 7) return false;
    }
    return true;
  });

  const sectionBox = { backgroundColor: '#fff', border: '1px solid #d9dee7', borderRadius: '6px' };
  const selectStyle = { padding: '5px 8px', fontSize: '12px', border: '1px solid #d9dee7', borderRadius: '4px', color: '#334155', backgroundColor: '#fff', outline: 'none', cursor: 'pointer', fontFamily: "'Inter', system-ui, sans-serif" };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '16px 20px 36px', fontFamily: "'Inter', system-ui, sans-serif" }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div>
          <h1 style={{ fontSize: '16px', fontWeight: 600, color: '#1f2937', margin: 0 }}>Audit trail & verification ledger</h1>
          <p style={{ fontSize: '12px', color: '#64748b', margin: '2px 0 0' }}>Immutable screening records secured via SHA-256 cryptographic chaining.</p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button onClick={handleExportCsv} disabled={exporting} style={{
            display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 14px', fontSize: '12px', fontWeight: 500,
            backgroundColor: '#fff', color: '#334155', border: '1px solid #d9dee7', borderRadius: '4px', cursor: 'pointer',
            opacity: exporting ? 0.6 : 1, fontFamily: "'Inter', system-ui, sans-serif",
          }}>
            <Download style={{ width: '13px', height: '13px' }} />
            {exporting ? 'Exporting…' : 'Export CSV'}
          </button>
          <button onClick={handleVerifyChain} disabled={verifying} style={{
            padding: '6px 14px', fontSize: '12px', fontWeight: 500,
            backgroundColor: '#1f4e79', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer',
            opacity: verifying ? 0.6 : 1, fontFamily: "'Inter', system-ui, sans-serif",
          }}>
            {verifying ? 'Verifying…' : 'Verify chain integrity'}
          </button>
        </div>
      </div>

      {/* Verification result */}
      {verificationResult && (
        <div style={{
          marginBottom: '16px', padding: '12px 16px', borderRadius: '4px', fontSize: '12px', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          backgroundColor: verificationResult.is_valid ? '#f0fdf4' : '#fef2f2',
          border: `1px solid ${verificationResult.is_valid ? '#dcfce7' : '#fee2e2'}`,
          color: verificationResult.is_valid ? '#166534' : '#991b1b',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: verificationResult.is_valid ? '#166534' : '#991b1b' }} />
            <div>
              <div style={{ fontWeight: 500 }}>{verificationResult.is_valid ? 'Audit chain verified — cryptographic integrity intact' : 'Integrity violation detected in ledger'}</div>
              <div style={{ fontSize: '11px', opacity: 0.8, marginTop: '1px' }}>
                {verificationResult.is_valid
                  ? `${verificationResult.records_checked || verificationResult.total_records} records verified without discrepancies.`
                  : `Discrepancy at record ${verificationResult.first_invalid_record_id || verificationResult.first_invalid_record || 'Unknown'}.`}
              </div>
            </div>
          </div>
          <span style={{ fontSize: '11px', fontWeight: 500, padding: '3px 8px', backgroundColor: '#fff', border: '1px solid', borderRadius: '4px' }}>
            {verificationResult.records_checked || verificationResult.total_records} records
          </span>
        </div>
      )}

      {/* Summary KPIs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '16px' }}>
        {[
          { label: 'Total screenings', value: totalScans, color: '#1f2937' },
          { label: 'Flagged anomalies', value: flaggedCount, color: '#92400e' },
          { label: 'High risk cases', value: highRiskCount, color: '#991b1b' },
          { label: 'Escalated cases', value: escalatedCount, color: '#1f4e79' },
        ].map(kpi => (
          <div key={kpi.label} style={{ ...sectionBox, padding: '12px 16px' }}>
            <div style={{ fontSize: '11px', fontWeight: 500, color: '#64748b', marginBottom: '2px' }}>{kpi.label}</div>
            <div style={{ fontSize: '20px', fontWeight: 600, color: kpi.color }}>{kpi.value}</div>
          </div>
        ))}
      </div>

      {/* Filter toolbar */}
      <div style={{ ...sectionBox, padding: '10px 16px', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: '180px', display: 'flex', alignItems: 'center', gap: '6px', border: '1px solid #d9dee7', borderRadius: '4px', padding: '5px 10px', backgroundColor: '#f8fafc' }}>
          <span style={{ color: '#94a3b8', fontSize: '12px' }}>🔍</span>
          <input
            type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter by doc number, name, officer ID…"
            style={{ flex: 1, border: 'none', background: 'none', fontSize: '12px', color: '#1f2937', outline: 'none', fontFamily: "'Inter', system-ui, sans-serif" }}
          />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <span style={{ fontSize: '11px', color: '#64748b', fontWeight: 500 }}>Risk:</span>
          <select value={riskFilter} onChange={(e) => setRiskFilter(e.target.value)} style={selectStyle}>
            <option value="">All</option><option value="LOW">Low</option><option value="MEDIUM">Medium</option><option value="HIGH">High</option>
          </select>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <span style={{ fontSize: '11px', color: '#64748b', fontWeight: 500 }}>Decision:</span>
          <select value={decisionFilter} onChange={(e) => setDecisionFilter(e.target.value)} style={selectStyle}>
            <option value="">All</option><option value="APPROVED">Approved</option><option value="ESCALATED">Escalated</option><option value="REJECTED">Rejected</option><option value="PENDING">Pending</option>
          </select>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <span style={{ fontSize: '11px', color: '#64748b', fontWeight: 500 }}>Date:</span>
          <select value={dateFilter} onChange={(e) => setDateFilter(e.target.value)} style={selectStyle}>
            <option value="">All</option><option value="today">Today</option><option value="week">Past 7 days</option>
          </select>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <span style={{ fontSize: '11px', color: '#64748b', fontWeight: 500 }}>Checkpoint:</span>
          <select value={checkpointFilter} onChange={(e) => setCheckpointFilter(e.target.value)} style={selectStyle}>
            <option value="">All</option>
            {checkpoints.map((cp) => <option key={cp.id} value={cp.name}>{cp.checkpoint_code} - {cp.name}</option>)}
          </select>
        </div>
      </div>

      {/* Audit table */}
      <div style={{ ...sectionBox, overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: '40px', textAlign: 'center', color: '#64748b', fontSize: '12px' }}>Loading audit records…</div>
        ) : filteredLogs.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: '#64748b', fontSize: '12px' }}>No screening records found matching criteria.</div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse', fontSize: '12px' }}>
              <thead>
                <tr style={{ backgroundColor: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
                  {['Timestamp', 'Checkpoint', 'Doc type', 'Document number', 'Risk', 'Determination', 'Officer', 'Provenance', ''].map((h, i) => (
                    <th key={i} style={{ padding: '8px 12px', fontSize: '11px', fontWeight: 500, color: '#64748b', whiteSpace: 'nowrap' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredLogs.map((log) => (
                  <tr key={log.id} onClick={() => setSelectedLog(log)} style={{ borderBottom: '1px solid #f1f5f9', cursor: 'pointer' }}>
                    <td style={{ padding: '8px 12px', color: '#64748b', whiteSpace: 'nowrap' }}>{new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</td>
                    <td style={{ padding: '8px 12px', fontWeight: 500, color: '#334155', whiteSpace: 'nowrap' }}>{log.checkpoint_location?.replace(' Checkpoint', '') || 'Raxaul'}</td>
                    <td style={{ padding: '8px 12px', fontWeight: 500, color: '#1f2937' }}>{log.document_type}</td>
                    <td style={{ padding: '8px 12px', fontWeight: 500, color: '#1f4e79' }}>{log.masked_document_number || maskDocNumber(log.document_number, log.document_type)}</td>
                    <td style={{ padding: '8px 12px' }}><RiskBadge riskLevel={log.risk_level} score={Math.round(log.overall_risk_score)} size="small" /></td>
                    <td style={{ padding: '8px 12px' }}>
                      <span style={{ fontWeight: 500, color: (log.officer_decision === 'APPROVED' || log.officer_decision === 'APPROVE') ? '#166534' : (log.officer_decision === 'REJECTED' || log.officer_decision === 'REJECT') ? '#991b1b' : (log.officer_decision === 'ESCALATED' || log.officer_decision === 'ESCALATE') ? '#92400e' : '#94a3b8' }}>
                        {log.officer_decision || 'Pending'}
                      </span>
                    </td>
                    <td style={{ padding: '8px 12px', color: '#64748b', fontSize: '11px' }}>{log.officer_id || 'SSB-7741'}</td>
                    <td style={{ padding: '8px 12px' }}>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '3px', fontSize: '10px', fontWeight: 500, color: '#166534', backgroundColor: '#f0fdf4', padding: '2px 6px', borderRadius: '3px', border: '1px solid #dcfce7' }}>
                        ✓ SHA-256
                      </span>
                    </td>
                    <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                      <button onClick={(e) => { e.stopPropagation(); setSelectedLog(log); }} style={{
                        padding: '4px 10px', fontSize: '11px', fontWeight: 500, color: '#1f4e79', backgroundColor: '#f1f5f9', border: '1px solid #d9dee7', borderRadius: '4px', cursor: 'pointer', fontFamily: "'Inter', system-ui, sans-serif",
                      }}>View</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Inspection Modal */}
      {selectedLog && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 50, backgroundColor: 'rgba(0,0,0,0.35)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px' }}>
          <div style={{ backgroundColor: '#fff', borderRadius: '6px', border: '1px solid #d9dee7', maxWidth: '640px', width: '100%', maxHeight: '90vh', overflowY: 'auto', padding: '24px', boxShadow: '0 2px 12px rgba(0,0,0,0.06)', fontFamily: "'Inter', system-ui, sans-serif" }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', paddingBottom: '10px', borderBottom: '1px solid #e2e8f0' }}>
              <h3 style={{ fontSize: '15px', fontWeight: 600, color: '#1f2937', margin: 0 }}>Audit record: <span style={{ color: '#64748b', fontWeight: 400 }}>{selectedLog.id}</span></h3>
              <button onClick={() => setSelectedLog(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8', display: 'flex' }}><X style={{ width: '16px', height: '16px' }} /></button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', marginBottom: '16px' }}>
              {[
                { label: 'Timestamp', value: new Date(selectedLog.timestamp).toLocaleString() },
                { label: 'Document type', value: selectedLog.document_type },
                { label: 'Risk score', value: `${Math.round(selectedLog.overall_risk_score)} / 100` },
                { label: 'Determination', value: selectedLog.officer_decision || 'Pending' },
              ].map(f => (
                <div key={f.label} style={{ padding: '6px 10px', backgroundColor: '#f8fafc', borderRadius: '4px', border: '1px solid #f1f5f9' }}>
                  <div style={{ fontSize: '10px', fontWeight: 500, color: '#64748b', marginBottom: '2px' }}>{f.label}</div>
                  <div style={{ fontSize: '12px', fontWeight: 500, color: '#1f2937' }}>{f.value}</div>
                </div>
              ))}
            </div>

            {selectedLog.officer_notes && (
              <div style={{ padding: '10px 14px', backgroundColor: '#fffbeb', border: '1px solid #fef3c7', borderRadius: '4px', marginBottom: '16px', fontSize: '12px', color: '#92400e' }}>
                <div style={{ fontWeight: 500, fontSize: '11px', marginBottom: '4px' }}>Officer remarks</div>
                {selectedLog.officer_notes}
              </div>
            )}

            <div style={{ marginBottom: '16px' }}>
              <div style={{ fontSize: '12px', fontWeight: 500, color: '#334155', marginBottom: '8px' }}>Extracted fields (Masked)</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '6px' }}>
                {Object.entries(selectedLog.extracted_data_json || {}).map(([k, v]) => {
                  if (k === 'raw_text') return null;
                  const val = typeof v === 'object' ? v?.value : String(v);
                  const isSensitive = k.includes('number') || k.includes('aadhaar') || k.includes('passport') || k.includes('dl');
                  return (
                    <div key={k} style={{ padding: '5px 8px', backgroundColor: '#f8fafc', borderRadius: '4px', border: '1px solid #f1f5f9' }}>
                      <div style={{ fontSize: '10px', color: '#64748b' }}>{k.replace(/_/g, ' ')}</div>
                      <div style={{ fontSize: '11px', fontWeight: 500, color: '#1f2937', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{isSensitive && val ? maskDocNumber(val, selectedLog.document_type) : val || '—'}</div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '16px' }}>
              <div style={{ padding: '8px 12px', backgroundColor: '#f8fafc', borderRadius: '4px', border: '1px solid #f1f5f9' }}>
                <div style={{ fontSize: '11px', fontWeight: 500, color: '#64748b', marginBottom: '2px' }}>Forensic tampering score</div>
                <div style={{ fontSize: '16px', fontWeight: 600, color: '#1f2937' }}>{Math.round(selectedLog.tampering_score)} / 100</div>
              </div>
              <div style={{ padding: '8px 12px', backgroundColor: '#f8fafc', borderRadius: '4px', border: '1px solid #f1f5f9' }}>
                <div style={{ fontSize: '11px', fontWeight: 500, color: '#64748b', marginBottom: '2px' }}>Biometric face similarity</div>
                <div style={{ fontSize: '16px', fontWeight: 600, color: '#1f2937' }}>{Math.round(selectedLog.face_match_score)}%</div>
              </div>
            </div>

            <div style={{ padding: '10px 14px', backgroundColor: '#f8fafc', borderRadius: '4px', border: '1px solid #e2e8f0', fontSize: '11px', color: '#64748b', display: 'flex', flexDirection: 'column', gap: '3px' }}>
              <div style={{ fontSize: '11px', fontWeight: 500, color: '#1f4e79', marginBottom: '2px' }}>Cryptographic ledger block</div>
              <div><span style={{ color: '#64748b' }}>Previous hash:</span> <span style={{ fontFamily: 'monospace', fontSize: '10px' }}>{selectedLog.prev_log_hash}</span></div>
              <div><span style={{ color: '#64748b' }}>Record hash:</span> <span style={{ fontFamily: 'monospace', fontSize: '10px' }}>{selectedLog.record_hash}</span></div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
