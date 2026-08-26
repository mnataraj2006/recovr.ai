import { useState, useEffect } from 'react';
import { authFetch } from '../../services/api';

interface Prefs {
  recovery_alerts: boolean;
  payment_failures: boolean;
  weekly_digest: boolean;
  system_updates: boolean;
  realtime_alerts: boolean;
  audit_log_events: boolean;
  api_key_activity: boolean;
}

const DEFAULT_PREFS: Prefs = {
  recovery_alerts: true,
  payment_failures: true,
  weekly_digest: false,
  system_updates: true,
  realtime_alerts: true,
  audit_log_events: false,
  api_key_activity: true,
};

function ToggleItem({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (val: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-4 py-3.5 border-b border-[rgba(125,211,252,0.06)] last:border-0">
      <div>
        <p className="text-sm text-[#e0e8f0] font-medium">{label}</p>
        {description && <p className="text-xs text-[#a0b4c4] mt-0.5">{description}</p>}
      </div>
      <button
        type="button"
        onClick={() => onChange(!checked)}
        className={`relative w-11 h-6 rounded-full transition-all flex-shrink-0 ${
          checked ? 'bg-[#7dd3fc]' : 'bg-[rgba(125,211,252,0.15)]'
        }`}
        style={{ border: checked ? 'none' : '1px solid rgba(125,211,252,0.2)' }}
      >
        <span
          className={`absolute top-0.5 w-5 h-5 rounded-full transition-all ${
            checked ? 'left-[22px] bg-[#001f2e]' : 'left-0.5 bg-[#a0b4c4]'
          }`}
        />
      </button>
    </div>
  );
}

export function Notifications() {
  const [prefs, setPrefs] = useState<Prefs>(DEFAULT_PREFS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    fetchPrefs();
  }, []);

  async function fetchPrefs() {
    try {
      setLoading(true);
      const res = await authFetch('/api/v1/users/me/notifications');
      if (res.ok) {
        const data = await res.json();
        setPrefs(data);
      }
    } catch {
      setMessage({ type: 'error', text: 'Failed to load notification preferences.' });
    } finally {
      setLoading(false);
    }
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMessage(null);

    try {
      const res = await authFetch('/api/v1/users/me/notifications', {
        method: 'PATCH',
        body: JSON.stringify(prefs),
      });

      if (res.ok) {
        const updated = await res.json();
        setPrefs(updated);
        setMessage({ type: 'success', text: 'Notification preferences saved successfully.' });
      } else {
        setMessage({ type: 'error', text: 'Failed to save notification preferences.' });
      }
    } catch {
      setMessage({ type: 'error', text: 'Network error saving notification preferences.' });
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="p-8 text-center text-[#a0b4c4] text-sm animate-pulse">
        Loading notification preferences...
      </div>
    );
  }

  return (
    <form onSubmit={handleSave} className="space-y-8">
      <div className="pb-4 border-b border-[rgba(125,211,252,0.08)]">
        <h2 className="text-2xl font-bold text-[#e0e8f0]">Notifications</h2>
        <p className="text-[#a0b4c4] mt-1 text-sm">Choose how and when you receive alerts.</p>
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

      <div className="glass-panel rounded-xl p-6">
        <h3 className="text-base font-semibold text-[#e0e8f0] mb-4">Email Notifications</h3>
        <ToggleItem
          label="Recovery Alerts"
          description="Get notified when a transaction is recovered."
          checked={prefs.recovery_alerts}
          onChange={(val) => setPrefs({ ...prefs, recovery_alerts: val })}
        />
        <ToggleItem
          label="Failure Alerts"
          description="Get notified on unrecoverable failures."
          checked={prefs.payment_failures}
          onChange={(val) => setPrefs({ ...prefs, payment_failures: val })}
        />
        <ToggleItem
          label="Weekly Digest"
          description="Summary of weekly recovery performance."
          checked={prefs.weekly_digest}
          onChange={(val) => setPrefs({ ...prefs, weekly_digest: val })}
        />
        <ToggleItem
          label="System Updates"
          description="Platform updates and maintenance notices."
          checked={prefs.system_updates}
          onChange={(val) => setPrefs({ ...prefs, system_updates: val })}
        />
      </div>

      <div className="glass-panel rounded-xl p-6">
        <h3 className="text-base font-semibold text-[#e0e8f0] mb-4">In-App Notifications</h3>
        <ToggleItem
          label="Real-time Alerts"
          description="Show live pop-up alerts in the dashboard."
          checked={prefs.realtime_alerts}
          onChange={(val) => setPrefs({ ...prefs, realtime_alerts: val })}
        />
        <ToggleItem
          label="Audit Log Events"
          description="Notify when new audit events are logged."
          checked={prefs.audit_log_events}
          onChange={(val) => setPrefs({ ...prefs, audit_log_events: val })}
        />
        <ToggleItem
          label="API Key Activity"
          description="Alert on unusual API key usage patterns."
          checked={prefs.api_key_activity}
          onChange={(val) => setPrefs({ ...prefs, api_key_activity: val })}
        />
      </div>

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={saving}
          className="px-6 py-2.5 rounded-lg font-medium text-sm text-[#001f2e] transition-all hover:opacity-90 active:scale-95 disabled:opacity-50"
          style={{ background: '#7dd3fc', boxShadow: '0 0 20px rgba(125,211,252,0.25)' }}
        >
          {saving ? 'Saving...' : 'Save Preferences'}
        </button>
      </div>
    </form>
  );
}
