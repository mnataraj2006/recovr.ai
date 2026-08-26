import { useState, useEffect } from 'react';
import { authFetch } from '../../services/api';

export function General() {
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [organization, setOrganization] = useState('');
  const [timezone, setTimezone] = useState('UTC (Coordinated Universal Time)');
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    fetchProfile();
  }, []);

  async function fetchProfile() {
    try {
      setLoading(true);
      const res = await authFetch('/api/v1/users/me');
      if (res.ok) {
        const data = await res.json();
        setFirstName(data.first_name || '');
        setLastName(data.last_name || '');
        setEmail(data.email || '');
        setOrganization(data.organization || '');
        setTimezone(data.timezone || 'UTC (Coordinated Universal Time)');
      } else {
        setMessage({ type: 'error', text: 'Failed to load profile data.' });
      }
    } catch {
      setMessage({ type: 'error', text: 'Network error loading profile.' });
    } finally {
      setLoading(false);
    }
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMessage(null);

    try {
      const res = await authFetch('/api/v1/users/me', {
        method: 'PATCH',
        body: JSON.stringify({
          first_name: firstName,
          last_name: lastName,
          email: email,
          organization: organization,
          timezone: timezone
        })
      });

      if (res.ok) {
        const updated = await res.json();
        setFirstName(updated.first_name || '');
        setLastName(updated.last_name || '');
        setEmail(updated.email || '');
        setOrganization(updated.organization || '');
        setTimezone(updated.timezone || 'UTC (Coordinated Universal Time)');
        setMessage({ type: 'success', text: 'Profile changes saved successfully.' });
      } else {
        const err = await res.json();
        setMessage({ type: 'error', text: err.detail || 'Failed to update profile.' });
      }
    } catch {
      setMessage({ type: 'error', text: 'Network error saving profile changes.' });
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="p-8 text-center text-[#a0b4c4] text-sm animate-pulse">
        Loading general profile settings...
      </div>
    );
  }

  return (
    <form onSubmit={handleSave} className="space-y-8">
      <div className="pb-4 border-b border-[rgba(125,211,252,0.08)]">
        <h2 className="text-2xl font-bold text-[#e0e8f0]">General</h2>
        <p className="text-[#a0b4c4] mt-1 text-sm">Update your profile and account preferences.</p>
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

      {/* Avatar (Honest UI) */}
      <div className="glass-panel rounded-xl p-5 flex items-center justify-between gap-5">
        <div className="flex items-center gap-5">
          <div
            className="w-16 h-16 rounded-full flex items-center justify-center border-2 border-[rgba(125,211,252,0.3)]"
            style={{ background: 'rgba(125,211,252,0.15)' }}
          >
            <span className="material-symbols-outlined text-[#7dd3fc]" style={{ fontSize: 32 }}>
              person
            </span>
          </div>
          <div>
            <p className="text-[#e0e8f0] font-medium">Profile Photo</p>
            <p className="text-xs text-[#a0b4c4] mt-0.5">Cloud object storage is not configured in this environment.</p>
          </div>
        </div>
        <button
          type="button"
          disabled
          className="text-xs text-[#a0b4c4] border border-[rgba(125,211,252,0.15)] px-3 py-1.5 rounded-lg opacity-60 cursor-not-allowed"
        >
          Upload Photo (Not Configured)
        </button>
      </div>

      {/* Form */}
      <div className="glass-panel rounded-xl p-6 space-y-5">
        <h3 className="text-base font-semibold text-[#e0e8f0] mb-2">Account Information</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div>
            <label className="block text-xs font-semibold text-[#a0b4c4] uppercase tracking-wider mb-1.5">
              First Name
            </label>
            <input
              type="text"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              className="w-full rounded-lg px-4 py-2.5 text-sm text-[#e0e8f0] outline-none border border-[rgba(125,211,252,0.12)] focus:border-[rgba(125,211,252,0.4)] transition-all"
              style={{ background: 'rgba(10,14,26,0.6)' }}
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-[#a0b4c4] uppercase tracking-wider mb-1.5">
              Last Name
            </label>
            <input
              type="text"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              className="w-full rounded-lg px-4 py-2.5 text-sm text-[#e0e8f0] outline-none border border-[rgba(125,211,252,0.12)] focus:border-[rgba(125,211,252,0.4)] transition-all"
              style={{ background: 'rgba(10,14,26,0.6)' }}
            />
          </div>
        </div>
        <div>
          <label className="block text-xs font-semibold text-[#a0b4c4] uppercase tracking-wider mb-1.5">
            Email Address
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg px-4 py-2.5 text-sm text-[#e0e8f0] outline-none border border-[rgba(125,211,252,0.12)] focus:border-[rgba(125,211,252,0.4)] transition-all"
            style={{ background: 'rgba(10,14,26,0.6)' }}
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-[#a0b4c4] uppercase tracking-wider mb-1.5">
            Organization
          </label>
          <input
            type="text"
            value={organization}
            onChange={(e) => setOrganization(e.target.value)}
            className="w-full rounded-lg px-4 py-2.5 text-sm text-[#e0e8f0] outline-none border border-[rgba(125,211,252,0.12)] focus:border-[rgba(125,211,252,0.4)] transition-all"
            style={{ background: 'rgba(10,14,26,0.6)' }}
          />
        </div>
      </div>

      {/* Timezone */}
      <div className="glass-panel rounded-xl p-6 space-y-3">
        <h3 className="text-base font-semibold text-[#e0e8f0] mb-2">Preferences</h3>
        <div>
          <label className="block text-xs font-semibold text-[#a0b4c4] uppercase tracking-wider mb-1.5">
            Timezone
          </label>
          <select
            value={timezone}
            onChange={(e) => setTimezone(e.target.value)}
            className="w-full appearance-none rounded-lg px-4 py-2.5 text-sm text-[#e0e8f0] outline-none border border-[rgba(125,211,252,0.12)] focus:border-[rgba(125,211,252,0.4)] transition-all"
            style={{ background: 'rgba(10,14,26,0.6)' }}
          >
            <option value="UTC (Coordinated Universal Time)">UTC (Coordinated Universal Time)</option>
            <option value="UTC+5:30 (India Standard Time)">UTC+5:30 (India Standard Time)</option>
            <option value="UTC-8 (Pacific Standard Time)">UTC-8 (Pacific Standard Time)</option>
          </select>
        </div>
      </div>

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={saving}
          className="px-6 py-2.5 rounded-lg font-medium text-sm text-[#001f2e] transition-all hover:opacity-90 active:scale-95 disabled:opacity-50"
          style={{ background: '#7dd3fc', boxShadow: '0 0 20px rgba(125,211,252,0.25)' }}
        >
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>
    </form>
  );
}
