import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Header from './components/Header';
import LoginPage from './pages/LoginPage';
import ScreeningPage from './pages/ScreeningPage';
import ReviewPage from './pages/ReviewPage';
import AuditPage from './pages/AuditPage';

export default function App() {
  const [user, setUser] = useState(null);

  useEffect(() => {
    const saved = localStorage.getItem('ssb_officer');
    if (saved) {
      try {
        setUser(JSON.parse(saved));
      } catch (e) {}
    } else {
      // Default demo officer state if none in localStorage
      setUser({
        id: 'off_001',
        badge_id: 'SSB-7741',
        full_name: 'Inspector R. K. Sharma',
        role: 'OFFICER',
        checkpoint_location: 'Raxaul Checkpoint (Indo-Nepal)'
      });
    }
  }, []);

  return (
    <Router>
      <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans selection:bg-blue-100 selection:text-blue-900">
        <Header user={user} setUser={setUser} />
        <main className="flex-1">
          <Routes>
            <Route path="/login" element={<LoginPage setUser={setUser} />} />
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
