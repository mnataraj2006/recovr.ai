import { NavLink, useLocation } from 'react-router-dom';
import { useState } from 'react';

const topNavLinks = [
  { label: 'Dashboard',  to: '/' },
  { label: 'Analytics',  to: '/analytics' },
  { label: 'Audit Logs', to: '/audit-logs' },
  { label: 'Settings',   to: '/settings/api-keys' },
];

export function TopNav() {
  const [searchVal, setSearchVal] = useState('');
  const location = useLocation();

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

      {/* Right: Search + Icons + Avatar */}
      <div className="flex items-center gap-2 lg:gap-3">
        <div className="relative hidden lg:block">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-[#a0b4c4]" style={{ fontSize: 18 }}>search</span>
          <input
            value={searchVal}
            onChange={(e) => setSearchVal(e.target.value)}
            placeholder="Search metrics..."
            className="w-52 rounded-full py-1.5 pl-9 pr-4 text-sm text-[#e0e8f0] placeholder:text-[#a0b4c4]/60 outline-none transition-all focus:w-64 border border-[rgba(125,211,252,0.15)]"
            style={{ background: 'rgba(32,44,66,0.6)', backdropFilter: 'blur(8px)' }}
          />
        </div>
        <button className="relative p-2 text-[#a0b4c4] hover:text-[#7dd3fc] hover:bg-[rgba(125,211,252,0.08)] rounded-full transition-all">
          <span className="material-symbols-outlined" style={{ fontSize: 22 }}>notifications</span>
          <span className="absolute top-2 right-2 w-1.5 h-1.5 bg-[#ff6b6b] rounded-full shadow-[0_0_5px_rgba(255,107,107,0.8)]"></span>
        </button>
        <button className="p-2 text-[#a0b4c4] hover:text-[#7dd3fc] hover:bg-[rgba(125,211,252,0.08)] rounded-full transition-all">
          <span className="material-symbols-outlined" style={{ fontSize: 22 }}>settings</span>
        </button>
        <div className="w-8 h-8 rounded-full border border-[rgba(125,211,252,0.3)] overflow-hidden cursor-pointer hover:border-[#7dd3fc] transition-colors flex items-center justify-center bg-[rgba(125,211,252,0.15)]">
          <span className="material-symbols-outlined text-[#7dd3fc]" style={{ fontSize: 20 }}>person</span>
        </div>
      </div>
    </header>
  );
}
