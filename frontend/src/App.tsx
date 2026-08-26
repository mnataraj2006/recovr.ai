import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Login } from './pages/Login';
import { AppShell } from './components/layout/AppShell';
import { Dashboard } from './pages/Dashboard';
import { Analytics } from './pages/Analytics';
import { AuditLogs } from './pages/AuditLogs';
import { TransactionDrillDown } from './pages/TransactionDrillDown';
import { RiskScores } from './pages/RiskScores';
import { Settings } from './pages/Settings';
import { ApiKeys } from './pages/settings/ApiKeys';
import { General } from './pages/settings/General';
import { Security } from './pages/settings/Security';
import { Notifications } from './pages/settings/Notifications';
import { Team } from './pages/settings/Team';

function AppRoutes() {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-[#00141e] flex items-center justify-center text-[#7dd3fc]">
        <div className="flex flex-col items-center gap-3">
          <span className="material-symbols-outlined animate-spin text-3xl">progress_activity</span>
          <span className="text-sm font-medium">Authenticating Recovr.ai Session...</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Login />;
  }

  return (
    <Routes>
      <Route element={<AppShell />}>
        {/* Dashboard */}
        <Route index element={<Dashboard />} />
        <Route path="dashboard" element={<Dashboard />} />

        {/* Analytics */}
        <Route path="analytics" element={<Analytics />} />

        {/* Risk Scores */}
        <Route path="risk-scores" element={<RiskScores />} />

        {/* Audit Logs */}
        <Route path="audit-logs" element={<AuditLogs />} />
        <Route path="audit-logs/:txnId" element={<TransactionDrillDown />} />

        {/* Settings — nested */}
        <Route path="settings" element={<Settings />}>
          <Route index element={<Navigate to="/settings/api-keys" replace />} />
          <Route path="general"       element={<General />} />
          <Route path="security"      element={<Security />} />
          <Route path="notifications" element={<Notifications />} />
          <Route path="api-keys"      element={<ApiKeys />} />
          <Route path="team"          element={<Team />} />
        </Route>

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}

export default App;
