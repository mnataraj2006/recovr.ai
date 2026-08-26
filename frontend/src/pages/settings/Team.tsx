import { useState, useEffect } from 'react';
import { authFetch } from '../../services/api';

interface Member {
  id: string;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
  created_at?: string;
}

const ROLE_COLORS: Record<string, string> = {
  ADMIN: 'text-[#7dd3fc] bg-[rgba(125,211,252,0.1)] border-[rgba(125,211,252,0.2)]',
  OPERATOR: 'text-[#c8a0f0] bg-[rgba(200,160,240,0.1)] border-[rgba(200,160,240,0.2)]',
  VIEWER: 'text-[#a0b4c4] bg-[rgba(160,180,196,0.08)] border-[rgba(160,180,196,0.15)]',
};

export function Team() {
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [forbidden, setForbidden] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Invite Form State
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('OPERATOR');
  const [creating, setCreating] = useState(false);
  const [tempPasswordNotice, setTempPasswordNotice] = useState<{ email: string; tempPw: string } | null>(null);

  // Delete Modal State
  const [deleteTarget, setDeleteTarget] = useState<Member | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    fetchTeam();
  }, []);

  async function fetchTeam() {
    try {
      setLoading(true);
      setForbidden(false);
      const res = await authFetch('/api/v1/users');
      if (res.status === 403) {
        setForbidden(true);
        return;
      }
      if (res.ok) {
        const data = await res.json();
        setMembers(data);
      } else {
        setMessage({ type: 'error', text: 'Failed to fetch team members.' });
      }
    } catch {
      setMessage({ type: 'error', text: 'Network error fetching team members.' });
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateUser(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim() || !name.trim()) return;

    setCreating(true);
    setMessage(null);
    setTempPasswordNotice(null);

    try {
      const res = await authFetch('/api/v1/users', {
        method: 'POST',
        body: JSON.stringify({ email: email.trim(), name: name.trim(), role })
      });

      if (res.ok) {
        const data = await res.json();
        setMembers([data.user, ...members]);
        setTempPasswordNotice({ email: data.user.email, tempPw: data.temporary_password });
        setEmail('');
        setName('');
        setRole('OPERATOR');
        setMessage({ type: 'success', text: `User ${data.user.email} created successfully.` });
      } else {
        const err = await res.json();
        setMessage({ type: 'error', text: err.detail || 'Failed to create user.' });
      }
    } catch {
      setMessage({ type: 'error', text: 'Network error creating user.' });
    } finally {
      setCreating(false);
    }
  }

  async function handleRoleChange(user: Member, newRole: string) {
    try {
      const res = await authFetch(`/api/v1/users/${user.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ role: newRole })
      });
      if (res.ok) {
        const updated = await res.json();
        setMembers(members.map((m) => (m.id === user.id ? updated : m)));
        setMessage({ type: 'success', text: `Updated ${user.email} role to ${newRole}.` });
      } else {
        const err = await res.json();
        setMessage({ type: 'error', text: err.detail || 'Failed to update role.' });
      }
    } catch {
      setMessage({ type: 'error', text: 'Network error updating user role.' });
    }
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      const res = await authFetch(`/api/v1/users/${deleteTarget.id}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        setMembers(members.filter((m) => m.id !== deleteTarget.id));
        setMessage({ type: 'success', text: `User ${deleteTarget.email} removed.` });
      } else {
        const err = await res.json();
        setMessage({ type: 'error', text: err.detail || 'Failed to delete user.' });
      }
    } catch {
      setMessage({ type: 'error', text: 'Network error deleting user.' });
    } finally {
      setDeleting(false);
      setDeleteTarget(null);
    }
  }

  if (forbidden) {
    return (
      <div className="space-y-8">
        <div className="pb-4 border-b border-[rgba(125,211,252,0.08)]">
          <h2 className="text-2xl font-bold text-[#e0e8f0]">Team Management</h2>
        </div>
        <div className="glass-panel rounded-xl p-8 text-center space-y-3">
          <span className="material-symbols-outlined text-amber-400" style={{ fontSize: 40 }}>
            lock
          </span>
          <h3 className="text-lg font-semibold text-[#e0e8f0]">Access Restricted</h3>
          <p className="text-sm text-[#a0b4c4] max-w-md mx-auto">
            You require the <span className="text-[#7dd3fc] font-semibold">ADMIN</span> role to manage team members and permissions.
          </p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="p-8 text-center text-[#a0b4c4] text-sm animate-pulse">
        Loading team members...
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="pb-4 border-b border-[rgba(125,211,252,0.08)]">
        <h2 className="text-2xl font-bold text-[#e0e8f0]">Team</h2>
        <p className="text-[#a0b4c4] mt-1 text-sm">Manage team members and their access levels.</p>
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

      {tempPasswordNotice && (
        <div className="glass-panel rounded-xl p-4 border border-[#7dd3fc]/40 bg-[#7dd3fc]/10 text-sm space-y-1">
          <p className="font-semibold text-[#7dd3fc]">User Account Created Successfully</p>
          <p className="text-xs text-[#e0e8f0]">
            User Email: <span className="font-mono">{tempPasswordNotice.email}</span>
          </p>
          <p className="text-xs text-[#e0e8f0]">
            Temporary Password: <span className="font-mono bg-[#001f2e] px-2 py-0.5 rounded text-[#7dd3fc]">{tempPasswordNotice.tempPw}</span>
          </p>
        </div>
      )}

      {/* Invite/Create User Form */}
      <form onSubmit={handleCreateUser} className="glass-panel rounded-xl p-5 space-y-4">
        <h3 className="text-base font-semibold text-[#e0e8f0]">Add Team Member</h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Full Name (e.g. Alex Smith)"
            className="rounded-lg px-4 py-2.5 text-sm text-[#e0e8f0] placeholder:text-[#a0b4c4]/60 outline-none border border-[rgba(125,211,252,0.12)] focus:border-[rgba(125,211,252,0.4)] transition-all"
            style={{ background: 'rgba(10,14,26,0.6)' }}
          />
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="colleague@company.com"
            className="rounded-lg px-4 py-2.5 text-sm text-[#e0e8f0] placeholder:text-[#a0b4c4]/60 outline-none border border-[rgba(125,211,252,0.12)] focus:border-[rgba(125,211,252,0.4)] transition-all"
            style={{ background: 'rgba(10,14,26,0.6)' }}
          />
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="appearance-none rounded-lg px-4 py-2.5 text-sm text-[#e0e8f0] outline-none border border-[rgba(125,211,252,0.12)] focus:border-[rgba(125,211,252,0.4)] transition-all"
            style={{ background: 'rgba(10,14,26,0.6)' }}
          >
            <option value="ADMIN">ADMIN</option>
            <option value="OPERATOR">OPERATOR</option>
            <option value="VIEWER">VIEWER</option>
          </select>
        </div>
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={creating}
            className="px-5 py-2.5 rounded-lg font-medium text-sm text-[#001f2e] transition-all hover:opacity-90 active:scale-95 disabled:opacity-50"
            style={{ background: '#7dd3fc' }}
          >
            {creating ? 'Creating User...' : 'Add User'}
          </button>
        </div>
      </form>

      {/* Members List */}
      <div className="glass-panel rounded-xl overflow-hidden">
        <div className="px-5 py-3.5 border-b border-[rgba(125,211,252,0.08)]">
          <h3 className="text-sm font-semibold text-[#e0e8f0]">Members ({members.length})</h3>
        </div>
        <div className="divide-y divide-[rgba(125,211,252,0.06)]">
          {members.map((m) => (
            <div key={m.id} className="flex items-center justify-between px-5 py-3.5 hover:bg-[rgba(125,211,252,0.03)] transition-colors">
              <div className="flex items-center gap-3">
                <div
                  className="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold text-[#001f2e] flex-shrink-0"
                  style={{ background: '#7dd3fc' }}
                >
                  {m.name ? m.name.slice(0, 2).toUpperCase() : m.email.slice(0, 2).toUpperCase()}
                </div>
                <div>
                  <p className="text-sm text-[#e0e8f0] font-medium">{m.name || 'User'}</p>
                  <p className="text-xs text-[#a0b4c4]">{m.email}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <select
                  value={m.role}
                  onChange={(e) => handleRoleChange(m, e.target.value)}
                  className={`text-xs font-semibold px-2.5 py-1 rounded-full border outline-none cursor-pointer ${
                    ROLE_COLORS[m.role] ?? ROLE_COLORS['VIEWER']
                  }`}
                  style={{ background: 'rgba(10,14,26,0.8)' }}
                >
                  <option value="ADMIN" className="bg-[#0a0e1a] text-[#e0e8f0]">ADMIN</option>
                  <option value="OPERATOR" className="bg-[#0a0e1a] text-[#e0e8f0]">OPERATOR</option>
                  <option value="VIEWER" className="bg-[#0a0e1a] text-[#e0e8f0]">VIEWER</option>
                </select>
                <button
                  type="button"
                  onClick={() => setDeleteTarget(m)}
                  className="text-[#a0b4c4] hover:text-[#ff6b6b] transition-colors p-1"
                >
                  <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
                    person_remove
                  </span>
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {deleteTarget && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-panel p-6 rounded-2xl max-w-sm w-full space-y-4 border border-rose-500/30">
            <h3 className="text-lg font-bold text-[#e0e8f0]">Remove Team Member</h3>
            <p className="text-sm text-[#a0b4c4]">
              Are you sure you want to remove <span className="text-[#e0e8f0] font-semibold">{deleteTarget.email}</span> from the system?
            </p>
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setDeleteTarget(null)}
                className="px-4 py-2 text-xs font-medium text-[#a0b4c4] hover:text-[#e0e8f0]"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={deleting}
                onClick={confirmDelete}
                className="px-4 py-2 text-xs font-medium text-white bg-rose-500 hover:bg-rose-600 rounded-lg transition-colors"
              >
                {deleting ? 'Removing...' : 'Confirm Remove'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
