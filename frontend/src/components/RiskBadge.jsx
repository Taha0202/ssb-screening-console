import React from 'react';

export default function RiskBadge({ riskLevel, score, size = 'default' }) {
  const isSmall = size === 'small';
  const fontSize = isSmall ? '11px' : '12px';
  const padding = isSmall ? '2px 8px' : '4px 10px';

  const config = {
    LOW: { bg: '#f0fdf4', color: '#166534', border: '#dcfce7', dot: '#22c55e', label: 'Low' },
    MEDIUM: { bg: '#fffbeb', color: '#92400e', border: '#fef3c7', dot: '#f59e0b', label: 'Medium' },
    HIGH: { bg: '#fef2f2', color: '#991b1b', border: '#fee2e2', dot: '#ef4444', label: 'High' },
  };

  const c = config[riskLevel] || config.HIGH;

  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '5px',
      backgroundColor: c.bg, color: c.color, border: `1px solid ${c.border}`,
      fontWeight: 500, borderRadius: '4px', padding, fontSize,
      fontFamily: "'Inter', system-ui, sans-serif",
    }}>
      <span style={{
        width: '6px', height: '6px', borderRadius: '50%',
        backgroundColor: c.dot, flexShrink: 0,
      }} />
      {c.label}{score != null && ` · ${score}`}
    </span>
  );
}
