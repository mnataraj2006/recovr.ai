import { Routes, Route, Navigate } from 'react-router-dom';
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

function App() {
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

export default App;
