import { Outlet } from 'react-router-dom';
import { TopNav } from './TopNav';
import { SideNav } from './SideNav';

export function AppShell() {
  return (
    <div className="min-h-screen flex" style={{ background: '#0a0e1a' }}>
      <SideNav />
      <div className="flex-1 flex flex-col min-h-screen ml-[134px] md:ml-[170px] lg:ml-[200px]">
        <TopNav />
        <main className="flex-1 overflow-y-auto pt-[53px]">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
