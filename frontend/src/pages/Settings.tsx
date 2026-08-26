import { NavLink, Outlet, useLocation } from 'react-router-dom';

const settingsTabs = [
  { icon: 'person',               label: 'General',       to: '/settings/general' },
  { icon: 'lock',                 label: 'Security',      to: '/settings/security' },
  { icon: 'notifications_active', label: 'Notifications', to: '/settings/notifications' },
  { icon: 'key',                  label: 'API Keys',      to: '/settings/api-keys' },
  { icon: 'group',                label: 'Team',          to: '/settings/team' },
];

export function Settings() {
  const location = useLocation();

  return (
    <div className="p-6 lg:p-8 animate-fade-in max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-8 pb-6 border-b border-[rgba(125,211,252,0.08)] flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-[#e0e8f0] tracking-tight">Settings</h1>
          <p className="text-[#a0b4c4] mt-1 text-sm">Manage your account, security and integrations.</p>
        </div>
      </div>

      <div className="flex gap-6">
        {/* Left Settings Sub-Nav (desktop only — sidebar handles mobile) */}
        <nav className="hidden lg:flex flex-col gap-1 w-48 flex-shrink-0">
          <p className="text-[10px] font-semibold text-[#a0b4c4] uppercase tracking-wider px-3 mb-2">Settings</p>
          {settingsTabs.map((tab) => {
            const isActive = location.pathname === tab.to;
            return (
              <NavLink
                key={tab.to}
                to={tab.to}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150 ${
                  isActive
                    ? 'bg-[rgba(125,211,252,0.15)] text-[#7dd3fc] border-r-2 border-[#7dd3fc] rounded-r-none'
                    : 'text-[#a0b4c4] hover:bg-[rgba(125,211,252,0.05)] hover:text-[#e0e8f0]'
                }`}
              >
                <span className="material-symbols-outlined" style={{ fontSize: 18, fontVariationSettings: isActive ? "'FILL' 1" : "'FILL' 0" }}>{tab.icon}</span>
                {tab.label}
              </NavLink>
            );
          })}
        </nav>

        {/* Settings Content */}
        <div className="flex-1 min-w-0">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
