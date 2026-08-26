import { NavLink, useLocation } from 'react-router-dom';

const mainNavItems = [
  { icon: 'insights',  label: 'Recovery Intelligence', to: '/' },
  { icon: 'security',  label: 'Risk Scores',           to: '/risk-scores' },
  { icon: 'terminal',  label: 'API Management',        to: '/settings/api-keys' },
];

const settingsNavItems = [
  { icon: 'person',               label: 'General',       to: '/settings/general' },
  { icon: 'lock',                 label: 'Security',      to: '/settings/security' },
  { icon: 'notifications_active', label: 'Notifications', to: '/settings/notifications' },
  { icon: 'key',                  label: 'API Keys',      to: '/settings/api-keys' },
  { icon: 'group',                label: 'Team',          to: '/settings/team' },
];

export function SideNav() {
  const location = useLocation();
  const isSettings = location.pathname.startsWith('/settings');
  const navItems = isSettings ? settingsNavItems : mainNavItems;

  return (
    <aside
      className="fixed top-0 left-0 h-screen w-[134px] md:w-[170px] lg:w-[200px] flex flex-col z-40 border-r border-[rgba(125,211,252,0.10)]"
      style={{ background: 'rgba(20,28,46,0.60)', backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)' }}
    >
      {/* Header */}
      <div className="p-4 lg:p-6 border-b border-[rgba(125,211,252,0.10)]">
        <div className="flex items-center gap-2 lg:gap-3">
          <div className="w-7 h-7 lg:w-8 lg:h-8 rounded flex items-center justify-center border border-[rgba(125,211,252,0.3)] bg-[rgba(125,211,252,0.1)] flex-shrink-0">
            <span className="material-symbols-outlined text-[#7dd3fc]" style={{ fontSize: 16, fontVariationSettings: "'FILL' 1" }}>terminal</span>
          </div>
          <div className="min-w-0">
            <p className="text-[#e0e8f0] font-bold text-sm leading-tight">Terminal</p>
            <p className="text-[#a0b4c4] text-[10px] font-mono">v2.4.0-stable</p>
          </div>
        </div>
      </div>

      {/* Nav Items */}
      <nav className="flex-1 py-3 overflow-y-auto flex flex-col gap-0.5 px-2">
        {isSettings && (
          <p className="text-[10px] font-semibold text-[#a0b4c4] uppercase tracking-wider px-2 mb-2 mt-1">Settings</p>
        )}
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-2 lg:gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150 active:translate-x-0.5 ${
                isActive
                  ? 'bg-[rgba(125,211,252,0.15)] text-[#7dd3fc] border-r-2 border-[#7dd3fc] rounded-r-none'
                  : 'text-[#a0b4c4] hover:bg-[rgba(125,211,252,0.05)] hover:text-[#e0e8f0]'
              }`
            }
          >
            <span className="material-symbols-outlined flex-shrink-0" style={{ fontSize: 18 }}>{item.icon}</span>
            <span className="truncate text-xs lg:text-sm">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Sidebar Footer Links */}
      <div className="p-3 lg:p-4 border-t border-[rgba(125,211,252,0.10)]">
        <div className="flex flex-col gap-0.5">
          <a href="#" className="flex items-center gap-2 px-2 py-1.5 rounded text-[#a0b4c4] hover:text-[#e0e8f0] hover:bg-[rgba(125,211,252,0.05)] text-xs transition-all">
            <span className="material-symbols-outlined flex-shrink-0" style={{ fontSize: 16 }}>help</span>
            <span className="truncate">Help Center</span>
          </a>
          <a href="#" className="flex items-center gap-2 px-2 py-1.5 rounded text-[#a0b4c4] hover:text-[#e0e8f0] hover:bg-[rgba(125,211,252,0.05)] text-xs transition-all">
            <span className="material-symbols-outlined flex-shrink-0" style={{ fontSize: 16 }}>description</span>
            <span className="truncate">Documentation</span>
          </a>
        </div>
      </div>
    </aside>
  );
}
