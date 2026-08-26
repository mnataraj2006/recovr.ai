import { NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

const topNavLinks = [
  { label: 'Dashboard',  to: '/' },
  { label: 'Analytics',  to: '/analytics' },
  { label: 'Audit Logs', to: '/audit-logs' },
  { label: 'Settings',   to: '/settings/api-keys' },
];

export function TopNav() {
  const location = useLocation();
  const { user, logout } = useAuth();

  const isSettings = location.pathname.startsWith('/settings');

  return (
    <header
      className="fixed top-0 left-[134px] md:left-[170px] lg:left-[200px] right-0 z-50 flex items-center justify-between px-4 lg:px-6 py-3 border-b border-[rgba(125,211,252,0.10)]"
      style={{
        background: 'rgba(15,21,36,0.75)',
        backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)',
        boxShadow: '0 0 30px rgba(125,211,252,0.04)',
      }}
    >
      {/* Left: Brand + Nav */}
      <div className="flex items-center gap-4 lg:gap-8">
        <div className="flex items-center gap-2 text-lg font-bold text-[#7dd3fc] font-headline">
          <div className="w-5 h-5 rounded bg-[rgba(125,211,252,0.15)] border border-[rgba(125,211,252,0.4)] flex items-center justify-center">
            <span className="w-1.5 h-1.5 rounded-full bg-[#7dd3fc] animate-pulse block"></span>
          </div>
          Recovr.ai
        </div>
        <nav className="hidden md:flex items-center gap-1 text-sm">
          {topNavLinks.map((link) => {
            const isActive =
              link.to === '/'
                ? location.pathname === '/' || location.pathname === '/dashboard'
                : link.to === '/settings/api-keys'
                ? isSettings
                : location.pathname.startsWith(link.to);
            return (
              <NavLink
                key={link.to}
                to={link.to}
                className={`px-3 py-1.5 rounded-md transition-all duration-200 active:scale-95 ${
                  isActive
                    ? 'text-[#7dd3fc] border-b-2 border-[#7dd3fc] rounded-b-none pb-[4px]'
                    : 'text-[#a0b4c4] hover:text-[#e0e8f0] hover:bg-[rgba(125,211,252,0.08)]'
                }`}
              >
                {link.label}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Right: User Profile & Actions */}
      <div className="flex items-center gap-3">
        {user && (
          <div className="flex items-center gap-3 bg-[rgba(26,36,56,0.6)] px-3 py-1.5 rounded-full border border-[rgba(125,211,252,0.12)]">
            <div className="text-right hidden sm:block">
              <div className="text-xs font-semibold text-[#e0e8f0]">{user.name}</div>
              <div className="text-[10px] text-[#7dd3fc] font-mono">{user.role}</div>
            </div>
            <div className="w-7 h-7 rounded-full border border-[rgba(125,211,252,0.3)] flex items-center justify-center bg-[rgba(125,211,252,0.15)] text-[#7dd3fc] font-bold text-xs">
              {user.name.charAt(0).toUpperCase()}
            </div>
          </div>
        )}

        <button
          onClick={logout}
          className="p-2 text-[#a0b4c4] hover:text-[#ff6b6b] hover:bg-[rgba(255,107,107,0.1)] rounded-full transition-all flex items-center gap-1 text-xs"
          title="Sign Out"
        >
          <span className="material-symbols-outlined" style={{ fontSize: 20 }}>logout</span>
        </button>
      </div>
    </header>
  );
}
