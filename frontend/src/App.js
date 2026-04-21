import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from '@/pages/Dashboard';
import Statements from '@/pages/Statements';
import ImportExport from '@/pages/ImportExport';
import MissedOpportunitiesPage from '@/pages/MissedOpportunitiesPage';
import Settings from '@/pages/Settings';
import Statistics from '@/pages/Statistics';
import '@/App.css';

function AppRouter() {
  return (
    <Routes>
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/import-export" element={<ImportExport />} />
      <Route path="/missed-opportunities" element={<MissedOpportunitiesPage />} />
      <Route path="/statements" element={<Statements />} />
      <Route path="/settings" element={<Settings />} />
      <Route path="/statistics" element={<Statistics />} />
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AppRouter />
      </BrowserRouter>
    </div>
  );
}

export default App;
