import { useState, useEffect } from 'react';
import { authFetch } from '../../services/api';

interface UserAccountInfo {
  email: string;
  role: string;
}

export function Security() {
  const [currentPw, setCurrentPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [updating, setUpdating] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  
  const [accountInfo, setAccountInfo] = useState<UserAccountInfo | null>(null);

  useEffect(() => {
    fetchAccountInfo();
  }, []);

  async function fetchAccountInfo() {
    try {
      const res = await authFetch('/api/v1/users/me');
      if (res.ok) {
        const data = await res.json();
        setAccountInfo({ email: data.email, role: data.role });
      }
    } catch {
      // Non-critical background fetch failure
    }
  }

  async function handlePasswordChange(e: React.FormEvent) {
    e.preventDefault();
    setMessage(null);

    if (!currentPw) {
      setMessage({ type: 'error', text: 'Current password is required.' });
      return;
    }
    if (newPw.length < 8) {
      setMessage({ type: 'error', text: 'New password must be at least 8 characters long.' });
      return;
    }
    if (newPw !== confirmPw) {
      setMessage({ type: 'error', text: 'New password and confirm password do not match.' });
      return;
    }

    setUpdating(true);
    try {
      const res = await authFetch('/api/v1/auth/change-password', {
        method: 'POST',
        body: JSON.stringify({
          current_password: currentPw,
          new_password: newPw
        })
      });

      if (res.ok) {
        setMessage({ type: 'success', text: 'Password updated successfully.' });
        setCurrentPw('');
        setNewPw('');
        setConfirmPw('');
      } else {
        const err = await res.json();
        setMessage({ type: 'error', text: err.detail || 'Failed to update password.' });
      }
    } catch {
      setMessage({ type: 'error', text: 'Network error updating password.' });
    } finally {
      setUpdating(false);
    }
  }

  return (
    <div className="space-y-8">
      <div className="pb-4 border-b border-[rgba(125,211,252,0.08)]">
        <h2 className="text-2xl font-bold text-[#e0e8f0]">Security</h2>
        <p className="text-[#a0b4c4] mt-1 text-sm">Manage your password, 2FA, and active session details.</p>
      </div>

      {message && (
        <div
          className={`p-4 rounded-xl text-sm font-medium border ${
            message.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
              : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
          }`}
        >
          {message.text}
        </div>
      )}

      {/* Change Password */}
      <form onSubmit={handlePasswordChange} className="glass-panel rounded-xl p-6 space-y-4">
        <h3 className="text-base font-semibold text-[#e0e8f0]">Change Password</h3>
        <div>
          <label className="block text-xs font-semibold text-[#a0b4c4] uppercase tracking-wider mb-1.5">
            Current Password
          </label>
          <input
            type="password"
            value={currentPw}
            onChange={(e) => setCurrentPw(e.target.value)}
            className="w-full rounded-lg px-4 py-2.5 text-sm text-[#e0e8f0] outline-none border border-[rgba(125,211,252,0.12)] focus:border-[rgba(125,211,252,0.4)] transition-all"
            style={{ background: 'rgba(10,14,26,0.6)' }}
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-[#a0b4c4] uppercase tracking-wider mb-1.5">
            New Password
          </label>
          <input
            type="password"
            value={newPw}
            onChange={(e) => setNewPw(e.target.value)}
            className="w-full rounded-lg px-4 py-2.5 text-sm text-[#e0e8f0] outline-none border border-[rgba(125,211,252,0.12)] focus:border-[rgba(125,211,252,0.4)] transition-all"
            style={{ background: 'rgba(10,14,26,0.6)' }}
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-[#a0b4c4] uppercase tracking-wider mb-1.5">
            Confirm New Password
          </label>
          <input
            type="password"
            value={confirmPw}
            onChange={(e) => setConfirmPw(e.target.value)}
            className="w-full rounded-lg px-4 py-2.5 text-sm text-[#e0e8f0] outline-none border border-[rgba(125,211,252,0.12)] focus:border-[rgba(125,211,252,0.4)] transition-all"
            style={{ background: 'rgba(10,14,26,0.6)' }}
          />
        </div>
        <button
          type="submit"
          disabled={updating}
          className="px-5 py-2.5 rounded-lg text-sm font-medium text-[#001f2e] transition-all hover:opacity-90 active:scale-95 disabled:opacity-50"
          style={{ background: '#7dd3fc' }}
        >
          {updating ? 'Updating Password...' : 'Update Password'}
        </button>
      </form>

      {/* 2FA (Honest UI) */}
      <div className="glass-panel rounded-xl p-6 flex items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-semibold text-[#e0e8f0]">Two-Factor Authentication (2FA)</h3>
          <p className="text-xs text-[#a0b4c4] mt-1">TOTP 2FA infrastructure is currently not configured in this environment.</p>
        </div>
        <span className="text-xs text-[#a0b4c4] bg-[rgba(125,211,252,0.08)] border border-[rgba(125,211,252,0.15)] px-3 py-1.5 rounded-lg font-medium">
          Not Configured
        </span>
      </div>

      {/* Sessions */}
      <div className="glass-panel rounded-xl p-6">
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-base font-semibold text-[#e0e8f0]">Current Session Details</h3>
        </div>
        <div className="space-y-3">
          <div className="flex items-center justify-between p-3.5 rounded-lg border border-[rgba(125,211,252,0.08)]"
            style={{ background: 'rgba(10,14,26,0.4)' }}>
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-[#7dd3fc]" style={{ fontSize: 20 }}>security</span>
              <div>
                <p className="text-sm text-[#e0e8f0] font-medium">{accountInfo?.email || 'Authenticated User'}</p>
                <p className="text-xs text-[#a0b4c4]">Role: {accountInfo?.role || 'User'} · Active JWT Token Session</p>
              </div>
            </div>
            <span className="text-xs text-emerald-400 bg-emerald-400/10 px-2.5 py-1 rounded border border-emerald-400/20 font-medium">
              Active Session
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
