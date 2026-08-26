import { useState } from 'react';

interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  createdAt: string;
  lastUsed: string;
  highlight?: boolean;
}

const INITIAL_KEYS: ApiKey[] = [];

export function ApiKeys() {
  const [keys, setKeys] = useState<ApiKey[]>(INITIAL_KEYS);
  const [showCreate, setShowCreate] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  function createKey() {
    if (!newKeyName.trim()) return;
    const id = String(Date.now());
    setKeys((prev) => [
      ...prev,
      {
        id,
        name: newKeyName.trim(),
        prefix: 'sk_new_...',
        createdAt: new Date().toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' }),
        lastUsed: 'Never',
      },
    ]);
    setNewKeyName('');
    setShowCreate(false);
  }

  function revokeKey(id: string) {
    setKeys((prev) => prev.filter((k) => k.id !== id));
  }

  function copyKey(id: string) {
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  }

  return (
    <div className="space-y-8">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-[rgba(125,211,252,0.08)]">
        <div>
          <h2 className="text-2xl font-bold text-[#e0e8f0] tracking-tight">API Keys</h2>
          <p className="text-[#a0b4c4] mt-1 text-sm">Manage your API keys for programmatic access to Recovr.ai services.</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-5 py-2.5 rounded-lg font-medium text-sm text-[#7dd3fc] border border-[rgba(125,211,252,0.3)] transition-all hover:bg-[rgba(125,211,252,0.2)] active:scale-95 glow-hover"
          style={{ background: 'rgba(125,211,252,0.1)' }}
        >
          <span className="material-symbols-outlined" style={{ fontSize: 18 }}>add</span>
          Create New Key
        </button>
      </div>

      {/* Create Key Modal */}
      {showCreate && (
        <div className="glass-panel-elevated rounded-xl p-5 border border-[rgba(125,211,252,0.2)] animate-slide-in">
          <h3 className="text-base font-semibold text-[#e0e8f0] mb-4">Create New API Key</h3>
          <div className="flex gap-3">
            <input
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              placeholder="Key name (e.g. Production Service)"
              className="flex-1 rounded-lg px-4 py-2.5 text-sm text-[#e0e8f0] placeholder:text-[#a0b4c4]/60 outline-none border border-[rgba(125,211,252,0.2)] focus:border-[rgba(125,211,252,0.5)] transition-all"
              style={{ background: 'rgba(10,14,26,0.7)' }}
              onKeyDown={(e) => e.key === 'Enter' && createKey()}
              autoFocus
            />
            <button onClick={createKey} className="px-4 py-2.5 rounded-lg font-medium text-sm text-[#001f2e] transition-all hover:opacity-90 active:scale-95"
              style={{ background: '#7dd3fc' }}>
              Create
            </button>
            <button onClick={() => setShowCreate(false)} className="px-4 py-2.5 rounded-lg text-sm text-[#a0b4c4] hover:text-[#e0e8f0] transition-colors"
              style={{ background: 'rgba(15,21,36,0.6)', border: '1px solid rgba(125,211,252,0.1)' }}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Active Keys */}
      <section>
        <h3 className="text-base font-semibold text-[#e0e8f0] mb-4 flex items-center gap-2">
          <span className="material-symbols-outlined text-[#7dd3fc]" style={{ fontSize: 18 }}>vpn_key</span>
          Active Keys
        </h3>
        <div className="space-y-3">
          {keys.map((key) => (
            <div
              key={key.id}
              className="glass-panel rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 glow-hover transition-all duration-300 animate-slide-in"
            >
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-1.5">
                  <h4 className="font-medium text-[#e0e8f0]">{key.name}</h4>
                  <span className="text-[11px] px-2 py-0.5 rounded-full text-[#a0b4c4] border border-[rgba(125,211,252,0.15)]"
                    style={{ background: 'rgba(26,36,56,0.8)' }}>
                    {key.prefix}
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-4 text-xs text-[#a0b4c4]">
                  <span className="flex items-center gap-1">
                    <span className="material-symbols-outlined" style={{ fontSize: 13 }}>calendar_today</span>
                    Created: {key.createdAt}
                  </span>
                  <span className={`flex items-center gap-1 ${key.highlight ? 'text-[#7dd3fc]' : ''}`}>
                    <span className="material-symbols-outlined" style={{ fontSize: 13 }}>update</span>
                    Last Used: {key.lastUsed}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => copyKey(key.id)}
                  className="p-2 rounded-lg text-[#a0b4c4] hover:text-[#e0e8f0] transition-colors hover:bg-[rgba(125,211,252,0.08)]"
                  title="Copy Key"
                >
                  <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
                    {copiedId === key.id ? 'check' : 'content_copy'}
                  </span>
                </button>
                <button
                  onClick={() => revokeKey(key.id)}
                  className="px-3 py-1.5 rounded-lg text-[#ff6b6b]/80 hover:text-[#ff6b6b] hover:bg-[rgba(255,107,107,0.1)] border border-transparent hover:border-[rgba(255,107,107,0.2)] transition-all text-sm font-medium"
                >
                  Revoke
                </button>
              </div>
            </div>
          ))}
          {keys.length === 0 && (
            <div className="glass-panel rounded-xl p-8 text-center text-[#a0b4c4]">
              No active API keys. Create one to get started.
            </div>
          )}
        </div>
      </section>

      {/* Production Webhook Endpoints */}
      <section>
        <h3 className="text-base font-semibold text-[#e0e8f0] mb-4 flex items-center gap-2">
          <span className="material-symbols-outlined text-[#7dd3fc]" style={{ fontSize: 18 }}>webhook</span>
          Production Webhook Endpoints
        </h3>
        <div className="glass-panel rounded-xl p-6 space-y-4">
          <p className="text-sm text-[#a0b4c4]">
            Paste this Webhook Endpoint into your payment gateway dashboard (Stripe, Razorpay, PayPal) to automatically trigger recovery workflows on payment failures.
          </p>

          <div className="space-y-3">
            <div>
              <label className="block text-[10px] font-semibold text-[#a0b4c4] uppercase tracking-wider mb-1.5">Gateway Payment Failed Webhook URL</label>
              <div className="flex items-center gap-2">
                <input
                  readOnly
                  value="http://localhost:8000/api/v1/webhooks/payment"
                  className="flex-1 rounded-lg px-4 py-2.5 font-mono text-xs text-[#7dd3fc] border border-[rgba(125,211,252,0.2)] outline-none"
                  style={{ background: 'rgba(10,14,26,0.8)' }}
                />
                <button
                  onClick={() => {
                    navigator.clipboard.writeText('http://localhost:8000/api/v1/webhooks/payment');
                    setCopiedId('webhook');
                    setTimeout(() => setCopiedId(null), 2000);
                  }}
                  className="px-4 py-2.5 rounded-lg text-xs font-semibold text-[#001f2e] transition-all hover:opacity-90 active:scale-95 flex items-center gap-1.5"
                  style={{ background: '#7dd3fc' }}
                >
                  <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
                    {copiedId === 'webhook' ? 'check' : 'content_copy'}
                  </span>
                  {copiedId === 'webhook' ? 'Copied!' : 'Copy URL'}
                </button>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2 text-xs text-[#a0b4c4] pt-2">
              <span className="font-semibold text-[#e0e8f0]">Supported Events:</span>
              <span className="px-2 py-0.5 rounded bg-[rgba(125,211,252,0.1)] border border-[rgba(125,211,252,0.2)] text-[#7dd3fc]">payment.failed</span>
              <span className="px-2 py-0.5 rounded bg-[rgba(125,211,252,0.1)] border border-[rgba(125,211,252,0.2)] text-[#7dd3fc]">charge.failed</span>
              <span className="px-2 py-0.5 rounded bg-[rgba(125,211,252,0.1)] border border-[rgba(125,211,252,0.2)] text-[#7dd3fc]">checkout.session.expired</span>
            </div>
          </div>
        </div>
      </section>

      {/* Security Notice */}
      <div className="glass-panel-elevated rounded-xl p-6 relative overflow-hidden">
        <div className="absolute -right-8 -top-8 w-32 h-32 rounded-full pointer-events-none"
          style={{ background: 'rgba(125,211,252,0.06)', filter: 'blur(24px)' }} />
        <div className="flex items-start gap-4 relative z-10">
          <span className="material-symbols-outlined text-[#c8a0f0]" style={{ fontSize: 26 }}>shield</span>
          <div>
            <h4 className="text-[#e0e8f0] font-medium mb-1">Security Best Practices</h4>
            <p className="text-sm text-[#a0b4c4] mb-3 max-w-2xl leading-relaxed">
              Never share your secret keys or commit them to version control. If you suspect a key has been compromised, revoke it immediately and generate a new one.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
