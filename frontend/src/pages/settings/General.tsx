import { useState } from 'react';

function Field({ label, defaultValue, type = 'text' }: { label: string; defaultValue: string; type?: string }) {
  const [val, setVal] = useState(defaultValue);
  return (
    <div>
      <label className="block text-xs font-semibold text-[#a0b4c4] uppercase tracking-wider mb-1.5">{label}</label>
      <input
        type={type}
        value={val}
        onChange={(e) => setVal(e.target.value)}
        className="w-full rounded-lg px-4 py-2.5 text-sm text-[#e0e8f0] outline-none border border-[rgba(125,211,252,0.12)] focus:border-[rgba(125,211,252,0.4)] transition-all"
        style={{ background: 'rgba(10,14,26,0.6)' }}
      />
    </div>
  );
}

export function General() {
  return (
    <div className="space-y-8">
      <div className="pb-4 border-b border-[rgba(125,211,252,0.08)]">
        <h2 className="text-2xl font-bold text-[#e0e8f0]">General</h2>
        <p className="text-[#a0b4c4] mt-1 text-sm">Update your profile and account preferences.</p>
      </div>

      {/* Avatar */}
      <div className="glass-panel rounded-xl p-5 flex items-center gap-5">
        <div className="w-16 h-16 rounded-full flex items-center justify-center border-2 border-[rgba(125,211,252,0.3)]"
          style={{ background: 'rgba(125,211,252,0.15)' }}>
          <span className="material-symbols-outlined text-[#7dd3fc]" style={{ fontSize: 32 }}>person</span>
        </div>
        <div>
          <p className="text-[#e0e8f0] font-medium">Profile Photo</p>
          <p className="text-xs text-[#a0b4c4] mt-0.5">JPG, PNG or GIF. Max 2MB.</p>
          <button className="mt-2 text-xs text-[#7dd3fc] border border-[rgba(125,211,252,0.3)] px-3 py-1.5 rounded-lg hover:bg-[rgba(125,211,252,0.1)] transition-all">
            Upload Photo
          </button>
        </div>
      </div>

      {/* Form */}
      <div className="glass-panel rounded-xl p-6 space-y-5">
        <h3 className="text-base font-semibold text-[#e0e8f0] mb-2">Account Information</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <Field label="First Name" defaultValue="" />
          <Field label="Last Name" defaultValue="" />
        </div>
        <Field label="Email Address" defaultValue="" type="email" />
        <Field label="Organization" defaultValue="" />
      </div>

      {/* Timezone */}
      <div className="glass-panel rounded-xl p-6 space-y-3">
        <h3 className="text-base font-semibold text-[#e0e8f0] mb-2">Preferences</h3>
        <div>
          <label className="block text-xs font-semibold text-[#a0b4c4] uppercase tracking-wider mb-1.5">Timezone</label>
          <select className="w-full appearance-none rounded-lg px-4 py-2.5 text-sm text-[#e0e8f0] outline-none border border-[rgba(125,211,252,0.12)] focus:border-[rgba(125,211,252,0.4)] transition-all"
            style={{ background: 'rgba(10,14,26,0.6)' }}>
            <option>UTC (Coordinated Universal Time)</option>
            <option>UTC+5:30 (India Standard Time)</option>
            <option>UTC-8 (Pacific Standard Time)</option>
          </select>
        </div>
      </div>

      <div className="flex justify-end">
        <button className="px-6 py-2.5 rounded-lg font-medium text-sm text-[#001f2e] transition-all hover:opacity-90 active:scale-95"
          style={{ background: '#7dd3fc', boxShadow: '0 0 20px rgba(125,211,252,0.25)' }}>
          Save Changes
        </button>
      </div>
    </div>
  );
}
