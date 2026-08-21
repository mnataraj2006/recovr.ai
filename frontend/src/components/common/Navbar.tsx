import { RefreshCw, Play, Cpu } from 'lucide-react';

interface NavbarProps {
  loading: boolean;
  simulating: boolean;
  onRefresh: () => void;
  onSimulate: () => void;
}

/**
 * Top navigation bar with branding, refresh button, and simulation trigger.
 * Extracted from App.tsx lines 199–240.
 */
export function Navbar({ loading, simulating, onRefresh, onSimulate }: NavbarProps) {
  return (
    <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8 pb-6 border-b border-white/5 animate-slide-in">
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-extrabold bg-gradient-to-r from-blue-400 via-indigo-200 to-emerald-400 bg-clip-text text-transparent hover-shine cursor-pointer">
            Recovr.ai
          </h1>
          <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-xs px-2.5 py-1 rounded-full font-bold flex items-center gap-1.5 uppercase tracking-wider">
            <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
            Agent Active
          </span>
        </div>
        <p className="text-zinc-400 text-sm mt-1">Autonomous Payment Degradation &amp; Checkout Recovery System</p>
      </div>

      <div className="flex gap-3">
        <button
          onClick={onRefresh}
          className="glass-panel p-2.5 hover:bg-white/5 transition border border-white/10 text-zinc-300 rounded-xl"
          title="Refresh Dashboard Data"
        >
          <RefreshCw size={20} className={loading ? 'animate-spin' : ''} />
        </button>

        <button
          onClick={onSimulate}
          disabled={simulating}
          className="flex items-center gap-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold py-2.5 px-5 rounded-xl transition shadow-lg shadow-indigo-600/20 disabled:opacity-50"
        >
          {simulating ? (
            <>
              <Cpu size={18} className="animate-spin" />
              <span>Simulating Cohort...</span>
            </>
          ) : (
            <>
              <Play size={18} fill="white" />
              <span>Trigger Simulation Cohort</span>
            </>
          )}
        </button>
      </div>
    </header>
  );
}
