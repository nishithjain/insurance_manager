import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from '@/pages/Dashboard';
import Statements from '@/pages/Statements';
import ImportExport from '@/pages/ImportExport';
import MissedOpportunitiesPage from '@/pages/MissedOpportunitiesPage';
import Settings from '@/pages/Settings';
import Statistics from '@/pages/Statistics';
import Login from '@/pages/Login';
import UserManagement from '@/pages/UserManagement';
import { AuthProvider } from '@/auth/AuthContext';
import ProtectedRoute from '@/auth/ProtectedRoute';
import '@/App.css';

function AppRouter() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<Login />} />

      {/* Authenticated */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/import-export"
        element={
          <ProtectedRoute>
            <ImportExport />
          </ProtectedRoute>
        }
      />
      <Route
        path="/missed-opportunities"
        element={
          <ProtectedRoute>
            <MissedOpportunitiesPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/statements"
        element={
          <ProtectedRoute>
            <Statements />
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <Settings />
          </ProtectedRoute>
        }
      />
      <Route
        path="/statistics"
        element={
          <ProtectedRoute>
            <Statistics />
          </ProtectedRoute>
        }
      />

      {/* Admin-only */}
      <Route
        path="/admin/users"
        element={
          <ProtectedRoute requireAdmin>
            <UserManagement />
          </ProtectedRoute>
        }
      />

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <AppRouter />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
