import axios from 'axios';

const rawUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1';
export const sanitizeApiUrl = (url) => {
  if (!url || url === '/api/v1') return '/api/v1';
  let cleaned = url.trim();
  while (/^(https?:\/\/){2,}/i.test(cleaned)) {
    cleaned = cleaned.replace(/^(https?:\/\/)+/i, 'https://');
  }
  if (!cleaned.startsWith('http://') && !cleaned.startsWith('https://') && !cleaned.startsWith('/')) {
    cleaned = 'https://' + cleaned;
  }
  return cleaned.replace(/\/+$/, '');
};

const API_BASE_URL = sanitizeApiUrl(rawUrl);

export const api = axios.create({
  baseURL: API_BASE_URL,
});

export const loginOfficer = async (badgeId, password) => {
  const response = await api.post('/auth/login', { badge_id: badgeId, password });
  return response.data;
};

export const getSystemStatus = async () => {
  const response = await api.get('/system/status');
  return response.data;
};

export const getSystemHealth = async () => {
  const response = await api.get('/system/health');
  return response.data;
};

export const getCheckpoints = async (params = {}) => {
  const response = await api.get('/checkpoints', { params });
  return response.data;
};

export const getOfficers = async (params = {}) => {
  const response = await api.get('/officers', { params });
  return response.data;
};

export const uploadDocument = async (formData) => {
  const response = await api.post('/screening/upload-document', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const analyzeForensics = async (formData) => {
  const response = await api.post('/screening/analyze-forensics', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const verifyFace = async (formData) => {
  const response = await api.post('/screening/verify-face', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const evaluateRisk = async (payload) => {
  const response = await api.post('/screening/evaluate-risk', payload);
  return response.data;
};

export const recordDecision = async (screeningId, decision, notes) => {
  const response = await api.post('/screening/record-decision', {
    screening_id: screeningId,
    officer_decision: decision,
    officer_notes: notes,
  });
  return response.data;
};

export const submitDecision = recordDecision;

export const scanDocument = async (formData) => {
  const response = await api.post('/screening/scan', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const getAuditLogs = async (params = {}) => {
  const response = await api.get('/audit/logs', { params });
  return response.data;
};

export const getAuditLogById = async (logId) => {
  const response = await api.get(`/audit/logs/${logId}`);
  return response.data;
};

export const getScreeningHistory = async (screeningId) => {
  const response = await api.get(`/screening/history/${screeningId}`);
  return response.data;
};

export const verifyAuditChain = async () => {
  const response = await api.get('/audit/verify-chain');
  return response.data;
};

export const exportAuditLogsCsv = async (params = {}) => {
  const response = await api.get('/audit/export', {
    params,
    responseType: 'blob',
  });
  const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8;' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  link.setAttribute('download', `ssb_audit_logs_${timestamp}.csv`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};
