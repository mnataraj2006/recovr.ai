import { useState, useEffect, useCallback } from 'react';
import { authFetch, API_BASE } from '../../services/api';

interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  masked_key: string;
  created_at: string;
  last_used_at?: string;
  status: string;
}

export function ApiKeys() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [createdSecret, setCreatedSecret] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const webhookUrl = `${API_BASE || window.location.origin}/api/v1/webhooks/payment`;

  const loadKeys = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await authFetch('/api/v1/api-keys');
      if (res.ok) {
        const data = await res.json();
        setKeys(data);
      } else {
        setError('Failed to load API keys from server.');
      }
    } catch (err) {
      console.error('Error fetching API keys:', err);
      setError('Network error while connecting to server.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadKeys();
  }, [loadKeys]);

  async function createKey() {
    if (!newKeyName.trim()) return;
    setError(null);
    try {
      const res = await authFetch('/api/v1/api-keys', {
        method: 'POST',
        body: JSON.stringify({ name: newKeyName.trim() }),
      });
      if (res.ok) {
        const newKey = await res.json();
        setCreatedSecret(newKey.secret);
        setNewKeyName('');
        setShowCreate(false);
        loadKeys();
      } else {
        const errData = await res.json();
        setError(errData.detail || 'Failed to create API Key.');
      }
    } catch (err) {
      setError('Network error creating API Key.');
    }
  }

  async function revokeKey(id: string) {
    try {
      const res = await authFetch(`/api/v1/api-keys/${id}/revoke`, { method: 'POST' });
      if (res.ok) {
        loadKeys();
      }
    } catch (err) {
      console.error('Failed to revoke API key:', err);
    }
  }

  async function deleteKey(id: string) {
    try {
      const res = await authFetch(`/api/v1/api-keys/${id}`, { method: 'DELETE' });
      if (res.ok) {
        loadKeys();
      }
    } catch (err) {
      console.error('Failed to delete API key:', err);
    }
  }

  function copyToClipboard(text: string, id: string) {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  }

  return (
    <div className="space-y-8">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-[rgba(125,211,252,0.08)]">
        <div>
          <h2 className="text-2xl font-bold text-[#e0e8f0] tracking-tight">API Keys</h2>
          <p className="text-[#a0b4c4] mt-1 text-sm">Manage programmatically authenticated secret keys for Recovr.ai services.</p>
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

      {error && (
        <div className="p-4 rounded-xl bg-[rgba(255,107,107,0.12)] border border-[rgba(255,107,107,0.25)] text-[#ff6b6b] text-xs font-medium flex items-center gap-2">
          <span className="material-symbols-outlined" style={{ fontSize: 18 }}>error</span>
          {error}
        </div>
      )}

      {/* Secret One-Time Reveal Modal */}
      {createdSecret && (
        <div className="glass-panel-elevated rounded-xl p-6 border border-[#7dd3fc]/50 bg-[rgba(125,211,252,0.08)] space-y-4 animate-slide-in">
          <div className="flex items-center gap-2 text-[#7dd3fc]">
            <span className="material-symbols-outlined" style={{ fontSize: 22 }}>key</span>
            <h3 className="text-base font-bold">API Key Generated Successfully</h3>
          </div>
          <p className="text-xs text-[#a0b4c4]">
            Copy this secret now. <span className="text-[#ff6b6b] font-semibold">It will never be shown again!</span>
          </p>
          <div className="flex items-center gap-2">
            <input
              readOnly
              value={createdSecret}
              className="flex-1 rounded-lg px-4 py-2.5 font-mono text-xs text-[#7dd3fc] border border-[rgba(125,211,252,0.3)] outline-none bg-[rgba(10,14,26,0.9)]"
            />
            <button
              onClick={() => copyToClipboard(createdSecret, 'secret')}
              className="px-4 py-2.5 rounded-lg text-xs font-semibold text-[#001f2e] transition-all hover:opacity-90 flex items-center gap-1.5"
              style={{ background: '#7dd3fc' }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
                {copiedId === 'secret' ? 'check' : 'content_copy'}
              </span>
              {copiedId === 'secret' ? 'Copied!' : 'Copy Secret'}
            </button>
            <button
              onClick={() => setCreatedSecret(null)}
              className="px-4 py-2.5 rounded-lg text-xs text-[#a0b4c4] hover:text-[#e0e8f0]"
              style={{ background: 'rgba(15,21,36,0.8)', border: '1px solid rgba(125,211,252,0.2)' }}
            >
              Done
            </button>
          </div>
        </div>
      )}

      {/* Create Key Modal */}
      {showCreate && !createdSecret && (
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
              Generate
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
          Active API Keys
        </h3>
        {loading ? (
          <div className="glass-panel rounded-xl p-8 text-center text-[#a0b4c4] animate-pulse">
            Loading API keys...
          </div>
        ) : (
          <div className="space-y-3">
            {keys.map((key) => (
              <div
                key={key.id}
                className="glass-panel rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 glow-hover transition-all duration-300 animate-slide-in"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-1.5">
                    <h4 className="font-medium text-[#e0e8f0]">{key.name}</h4>
                    <span className={`text-[11px] px-2.5 py-0.5 rounded-full font-semibold border ${
                      key.status === 'ACTIVE'
                        ? 'text-[#7dd3fc] bg-[rgba(125,211,252,0.1)] border-[rgba(125,211,252,0.2)]'
                        : 'text-[#ff6b6b] bg-[rgba(255,107,107,0.1)] border-[rgba(255,107,107,0.2)]'
                    }`}>
                      {key.status}
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-4 text-xs text-[#a0b4c4]">
                    <span className="font-mono text-[#7dd3fc]/80">{key.masked_key}</span>
                    <span className="flex items-center gap-1">
                      <span className="material-symbols-outlined" style={{ fontSize: 13 }}>calendar_today</span>
                      Created: {new Date(key.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {key.status === 'ACTIVE' && (
                    <button
                      onClick={() => revokeKey(key.id)}
                      className="px-3 py-1.5 rounded-lg text-[#ff6b6b]/80 hover:text-[#ff6b6b] hover:bg-[rgba(255,107,107,0.1)] border border-transparent hover:border-[rgba(255,107,107,0.2)] transition-all text-sm font-medium"
                    >
                      Revoke
                    </button>
                  )}
                  <button
                    onClick={() => deleteKey(key.id)}
                    className="p-2 rounded-lg text-[#a0b4c4] hover:text-[#ff6b6b] transition-colors"
                    title="Delete Key Record"
                  >
                    <span className="material-symbols-outlined" style={{ fontSize: 18 }}>delete</span>
                  </button>
                </div>
              </div>
            ))}
            {keys.length === 0 && (
              <div className="glass-panel rounded-xl p-8 text-center text-[#a0b4c4]">
                No API keys found. Click "Create New Key" above to generate your first secret API key.
              </div>
            )}
          </div>
        )}
      </section>

      {/* Production Webhook Endpoints */}
      <section>
        <h3 className="text-base font-semibold text-[#e0e8f0] mb-4 flex items-center gap-2">
          <span className="material-symbols-outlined text-[#7dd3fc]" style={{ fontSize: 18 }}>webhook</span>
          Webhook Endpoint
        </h3>
        <div className="glass-panel rounded-xl p-6 space-y-4">
          <p className="text-sm text-[#a0b4c4]">
            Paste this environment-aware Webhook Endpoint into your payment gateway dashboard (Stripe, Razorpay, PayPal) to automatically trigger recovery workflows on payment failures.
          </p>

          <div className="space-y-3">
            <div>
              <label className="block text-[10px] font-semibold text-[#a0b4c4] uppercase tracking-wider mb-1.5">Gateway Payment Failed Webhook URL</label>
              <div className="flex items-center gap-2">
                <input
                  readOnly
                  value={webhookUrl}
                  className="flex-1 rounded-lg px-4 py-2.5 font-mono text-xs text-[#7dd3fc] border border-[rgba(125,211,252,0.2)] outline-none"
                  style={{ background: 'rgba(10,14,26,0.8)' }}
                />
                <button
                  onClick={() => copyToClipboard(webhookUrl, 'webhook')}
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
          </div>
        </div>
      </section>
    </div>
  );
}
