import { useState } from 'react';

export function Security() {
  const [currentPw, setCurrentPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [twoFa, setTwoFa] = useState(false);

  const sessions = [
    { id: '1', device: 'Current Browser Session', location: 'Local Session', active: true, lastSeen: 'Now' },
  ];

  return (
    <div className="space-y-8">
      <div className="pb-4 border-b border-[rgba(125,211,252,0.08)]">
        <h2 className="text-2xl font-bold text-[#e0e8f0]">Security</h2>
        <p className="text-[#a0b4c4] mt-1 text-sm">Manage your password, 2FA, and active sessions.</p>
      </div>

      {/* Change Password */}
      <div className="glass-panel rounded-xl p-6 space-y-4">
        <h3 className="text-base font-semibold text-[#e0e8f0]">Change Password</h3>
        {[
          { label: 'Current Password', val: currentPw, set: setCurrentPw },
          { label: 'New Password',     val: newPw,     set: setNewPw },
          { label: 'Confirm Password', val: confirmPw, set: setConfirmPw },
        ].map(({ label, val, set }) => (
          <div key={label}>
            <label className="block text-xs font-semibold text-[#a0b4c4] uppercase tracking-wider mb-1.5">{label}</label>
            <input
              type="password"
              value={val}
              onChange={(e) => set(e.target.value)}
              className="w-full rounded-lg px-4 py-2.5 text-sm text-[#e0e8f0] outline-none border border-[rgba(125,211,252,0.12)] focus:border-[rgba(125,211,252,0.4)] transition-all"
              style={{ background: 'rgba(10,14,26,0.6)' }}
            />
          </div>
        ))}
        <button className="px-5 py-2 rounded-lg text-sm font-medium text-[#001f2e]"
          style={{ background: '#7dd3fc' }}>
          Update Password
        </button>
      </div>

      {/* 2FA */}
      <div className="glass-panel rounded-xl p-6 flex items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-semibold text-[#e0e8f0]">Two-Factor Authentication</h3>
          <p className="text-xs text-[#a0b4c4] mt-1">Add an extra layer of security with an authenticator app.</p>
        </div>
        <button
          onClick={() => setTwoFa(!twoFa)}
          className={`relative w-11 h-6 rounded-full transition-all flex-shrink-0 ${twoFa ? 'bg-[#7dd3fc]' : 'bg-[rgba(125,211,252,0.15)]'}`}
          style={{ border: twoFa ? 'none' : '1px solid rgba(125,211,252,0.2)' }}
        >
          <span className={`absolute top-0.5 w-5 h-5 rounded-full transition-all ${twoFa ? 'left-[22px] bg-[#001f2e]' : 'left-0.5 bg-[#a0b4c4]'}`} />
        </button>
      </div>

      {/* Sessions */}
      <div className="glass-panel rounded-xl p-6">
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-base font-semibold text-[#e0e8f0]">Active Sessions</h3>
          <button className="text-xs text-[#ff6b6b] hover:text-[#ff6b6b]/80 transition-colors">Revoke All Others</button>
        </div>
        <div className="space-y-3">
          {sessions.map((s) => (
            <div key={s.id} className="flex items-center justify-between p-3.5 rounded-lg border border-[rgba(125,211,252,0.08)]"
              style={{ background: 'rgba(10,14,26,0.4)' }}>
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined text-[#a0b4c4]" style={{ fontSize: 20 }}>devices</span>
                <div>
                  <p className="text-sm text-[#e0e8f0] font-medium">{s.device}</p>
                  <p className="text-xs text-[#a0b4c4]">{s.location} · {s.lastSeen}</p>
                </div>
              </div>
              {s.active ? (
                <span className="text-xs text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded border border-emerald-400/20">Current</span>
              ) : (
                <button className="text-xs text-[#ff6b6b]/80 hover:text-[#ff6b6b] transition-colors">Revoke</button>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
