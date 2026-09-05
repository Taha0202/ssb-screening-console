import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Header from './components/Header';
import LoginPage from './pages/LoginPage';
import ScreeningPage from './pages/ScreeningPage';
import ReviewPage from './pages/ReviewPage';
import AuditPage from './pages/AuditPage';

export default function App() {
  const [user, setUser] = useState(() => {
    try {
      // Check if user previously logged in
      const saved = localStorage.getItem('ssb_officer');
      if (saved) return JSON.parse(saved);

      // If user explicitly clicked Log Out in this session, keep them at login
      if (sessionStorage.getItem('ssb_logged_out') === 'true') {
        return null;
      }

      // Default demo officer state so the workstation is immediately functional
      const defaultOfficer = {
        id: 'off_001',
        badge_id: 'SSB-7741',
        full_name: 'Inspector R. K. Sharma',
        role: 'OFFICER',
        checkpoint_location: 'Raxaul Checkpoint Unit A'
      };
      localStorage.setItem('ssb_officer', JSON.stringify(defaultOfficer));
      return defaultOfficer;
    } catch (e) {
      return null;
    }
  });

  return (
    <Router>
      <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans selection:bg-blue-100 selection:text-blue-900">
        <Header user={user} setUser={setUser} />
        <main className="flex-1">
          <Routes>
            <Route
              path="/login"
              element={user ? <Navigate to="/scan" replace /> : <LoginPage setUser={setUser} />}
            />
            <Route
              path="/scan"
              element={user ? <ScreeningPage user={user} /> : <Navigate to="/login" replace />}
            />
            <Route
              path="/review/:logId"
              element={user ? <ReviewPage user={user} /> : <Navigate to="/login" replace />}
            />
            <Route
              path="/audit"
              element={user ? <AuditPage user={user} /> : <Navigate to="/login" replace />}
            />
            <Route path="*" element={<Navigate to={user ? "/scan" : "/login"} replace />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}
