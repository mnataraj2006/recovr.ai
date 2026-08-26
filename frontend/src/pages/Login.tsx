import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';

export const Login: React.FC = () => {
  const { login } = useAuth();
  const [email, setEmail] = useState<string>('admin@recovr.ai');
  const [password, setPassword] = useState<string>('Admin@123456');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    const success = await login(email, password);
    setSubmitting(false);
    if (!success) {
      setError('Invalid email or password credentials.');
    }
  };

  return (
    <div className="min-h-screen bg-[#00141e] text-[#e0e8f0] flex items-center justify-center p-4">
      {/* Background glow elements */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-[rgba(125,211,252,0.06)] rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md glass-panel p-8 rounded-2xl border border-[rgba(125,211,252,0.15)] shadow-2xl relative z-10 animate-fade-in">
        {/* Logo & Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-[rgba(125,211,252,0.1)] border border-[rgba(125,211,252,0.2)] text-[#7dd3fc] mb-4">
            <span className="material-symbols-outlined" style={{ fontSize: 32 }}>shield_lock</span>
          </div>
          <h1 className="text-2xl font-bold text-[#e0e8f0] tracking-tight">Recovr.ai</h1>
          <p className="text-sm text-[#a0b4c4] mt-1">Autonomous Payment Recovery Platform</p>
        </div>

        {error && (
          <div className="mb-6 p-3.5 rounded-xl bg-[rgba(255,107,107,0.12)] border border-[rgba(255,107,107,0.25)] text-[#ff6b6b] text-xs font-medium flex items-center gap-2">
            <span className="material-symbols-outlined" style={{ fontSize: 18 }}>error</span>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-xs font-semibold text-[#a0b4c4] uppercase tracking-wider mb-2">Email Address</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-4 py-3 rounded-xl bg-[rgba(0,31,46,0.6)] border border-[rgba(125,211,252,0.15)] text-[#e0e8f0] placeholder-[#a0b4c4]/50 focus:outline-none focus:border-[#7dd3fc] transition-all text-sm"
              placeholder="admin@recovr.ai"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#a0b4c4] uppercase tracking-wider mb-2">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-4 py-3 rounded-xl bg-[rgba(0,31,46,0.6)] border border-[rgba(125,211,252,0.15)] text-[#e0e8f0] placeholder-[#a0b4c4]/50 focus:outline-none focus:border-[#7dd3fc] transition-all text-sm"
              placeholder="••••••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full py-3.5 rounded-xl font-semibold text-sm text-[#001f2e] transition active:scale-95 disabled:opacity-50 shadow-lg mt-2 flex items-center justify-center gap-2"
            style={{
              background: 'linear-gradient(135deg, #7dd3fc 0%, #38bdf8 100%)',
              boxShadow: '0 0 20px rgba(125,211,252,0.2)',
            }}
          >
            {submitting ? (
              <>
                <span className="material-symbols-outlined animate-spin" style={{ fontSize: 18 }}>progress_activity</span>
                Authenticating...
              </>
            ) : (
              <>
                Sign In
                <span className="material-symbols-outlined" style={{ fontSize: 18 }}>arrow_forward</span>
              </>
            )}
          </button>
        </form>

        <div className="mt-8 pt-6 border-t border-[rgba(125,211,252,0.08)] text-center text-xs text-[#a0b4c4]">
          <p>Protected by Stateless JWT & RBAC Engine</p>
          <div className="mt-2 text-[11px] text-[#7dd3fc]/70">Default Admin: admin@recovr.ai / Admin@123456</div>
        </div>
      </div>
    </div>
  );
};
