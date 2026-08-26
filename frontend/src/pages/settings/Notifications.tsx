import { useState } from 'react';

function Toggle({ label, description, defaultOn = false }: { label: string; description?: string; defaultOn?: boolean }) {
  const [on, setOn] = useState(defaultOn);
  return (
    <div className="flex items-center justify-between gap-4 py-3.5 border-b border-[rgba(125,211,252,0.06)] last:border-0">
      <div>
        <p className="text-sm text-[#e0e8f0] font-medium">{label}</p>
        {description && <p className="text-xs text-[#a0b4c4] mt-0.5">{description}</p>}
      </div>
      <button
        onClick={() => setOn(!on)}
        className={`relative w-11 h-6 rounded-full transition-all flex-shrink-0 ${on ? 'bg-[#7dd3fc]' : 'bg-[rgba(125,211,252,0.15)]'}`}
        style={{ border: on ? 'none' : '1px solid rgba(125,211,252,0.2)' }}
      >
        <span
          className={`absolute top-0.5 w-5 h-5 rounded-full transition-all ${on ? 'left-[22px] bg-[#001f2e]' : 'left-0.5 bg-[#a0b4c4]'}`}
        />
      </button>
    </div>
  );
}

export function Notifications() {
  return (
    <div className="space-y-8">
      <div className="pb-4 border-b border-[rgba(125,211,252,0.08)]">
        <h2 className="text-2xl font-bold text-[#e0e8f0]">Notifications</h2>
        <p className="text-[#a0b4c4] mt-1 text-sm">Choose how and when you receive alerts.</p>
      </div>

      <div className="glass-panel rounded-xl p-6">
        <h3 className="text-base font-semibold text-[#e0e8f0] mb-4">Email Notifications</h3>
        <Toggle label="Recovery Alerts" description="Get notified when a transaction is recovered." defaultOn={true} />
        <Toggle label="Failure Alerts" description="Get notified on unrecoverable failures." defaultOn={true} />
        <Toggle label="Weekly Digest" description="Summary of weekly recovery performance." defaultOn={false} />
        <Toggle label="System Updates" description="Platform updates and maintenance notices." defaultOn={true} />
      </div>

      <div className="glass-panel rounded-xl p-6">
        <h3 className="text-base font-semibold text-[#e0e8f0] mb-4">In-App Notifications</h3>
        <Toggle label="Real-time Alerts" description="Show live pop-up alerts in the dashboard." defaultOn={true} />
        <Toggle label="Audit Log Events" description="Notify when new audit events are logged." defaultOn={false} />
        <Toggle label="API Key Activity" description="Alert on unusual API key usage patterns." defaultOn={true} />
      </div>

      <div className="flex justify-end">
        <button className="px-6 py-2.5 rounded-lg font-medium text-sm text-[#001f2e] transition-all hover:opacity-90 active:scale-95"
          style={{ background: '#7dd3fc', boxShadow: '0 0 20px rgba(125,211,252,0.25)' }}>
          Save Preferences
        </button>
      </div>
    </div>
  );
}
