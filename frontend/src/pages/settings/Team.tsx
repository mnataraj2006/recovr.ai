import { useState } from 'react';

const INITIAL_MEMBERS: Array<{ id: string; name: string; email: string; role: string; avatar: string }> = [];

const ROLE_COLORS: Record<string, string> = {
  Admin:  'text-[#7dd3fc] bg-[rgba(125,211,252,0.1)] border-[rgba(125,211,252,0.2)]',
  Member: 'text-[#c8a0f0] bg-[rgba(200,160,240,0.1)] border-[rgba(200,160,240,0.2)]',
  Viewer: 'text-[#a0b4c4] bg-[rgba(160,180,196,0.08)] border-[rgba(160,180,196,0.15)]',
};

export function Team() {
  const [members, setMembers] = useState(INITIAL_MEMBERS);
  const [inviteEmail, setInviteEmail] = useState('');

  function removeMember(id: string) {
    setMembers((m) => m.filter((x) => x.id !== id));
  }

  function invite() {
    if (!inviteEmail.trim()) return;
    const initials = inviteEmail.split('@')[0].slice(0, 2).toUpperCase();
    setMembers((m) => [
      ...m,
      { id: String(Date.now()), name: inviteEmail, email: inviteEmail, role: 'Viewer', avatar: initials },
    ]);
    setInviteEmail('');
  }

  return (
    <div className="space-y-8">
      <div className="pb-4 border-b border-[rgba(125,211,252,0.08)]">
        <h2 className="text-2xl font-bold text-[#e0e8f0]">Team</h2>
        <p className="text-[#a0b4c4] mt-1 text-sm">Manage team members and their access levels.</p>
      </div>

      {/* Invite */}
      <div className="glass-panel rounded-xl p-5">
        <h3 className="text-base font-semibold text-[#e0e8f0] mb-4">Invite Member</h3>
        <div className="flex gap-3">
          <input
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            placeholder="colleague@company.com"
            className="flex-1 rounded-lg px-4 py-2.5 text-sm text-[#e0e8f0] placeholder:text-[#a0b4c4]/60 outline-none border border-[rgba(125,211,252,0.12)] focus:border-[rgba(125,211,252,0.4)] transition-all"
            style={{ background: 'rgba(10,14,26,0.6)' }}
            onKeyDown={(e) => e.key === 'Enter' && invite()}
          />
          <button onClick={invite} className="px-5 py-2.5 rounded-lg font-medium text-sm text-[#001f2e] transition-all hover:opacity-90 active:scale-95"
            style={{ background: '#7dd3fc' }}>
            Send Invite
          </button>
        </div>
      </div>

      {/* Members List */}
      <div className="glass-panel rounded-xl overflow-hidden">
        <div className="px-5 py-3.5 border-b border-[rgba(125,211,252,0.08)]">
          <h3 className="text-sm font-semibold text-[#e0e8f0]">Members ({members.length})</h3>
        </div>
        <div className="divide-y divide-[rgba(125,211,252,0.06)]">
          {members.map((m) => (
            <div key={m.id} className="flex items-center justify-between px-5 py-3.5 hover:bg-[rgba(125,211,252,0.03)] transition-colors">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold text-[#001f2e] flex-shrink-0"
                  style={{ background: '#7dd3fc' }}>
                  {m.avatar}
                </div>
                <div>
                  <p className="text-sm text-[#e0e8f0] font-medium">{m.name}</p>
                  <p className="text-xs text-[#a0b4c4]">{m.email}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className={`text-[10px] font-semibold px-2.5 py-1 rounded-full border ${ROLE_COLORS[m.role] ?? ROLE_COLORS['Viewer']}`}>
                  {m.role}
                </span>
                {m.role !== 'Admin' && (
                  <button onClick={() => removeMember(m.id)} className="text-[#a0b4c4] hover:text-[#ff6b6b] transition-colors p-1">
                    <span className="material-symbols-outlined" style={{ fontSize: 18 }}>person_remove</span>
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
