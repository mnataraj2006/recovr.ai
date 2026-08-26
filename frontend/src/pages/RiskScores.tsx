export function RiskScores() {
  return (
    <div className="p-6 lg:p-8 animate-fade-in max-w-4xl mx-auto">
      <div className="pb-6 border-b border-[rgba(125,211,252,0.08)] mb-8">
        <h1 className="text-2xl lg:text-3xl font-bold text-[#e0e8f0] tracking-tight">Risk Scores</h1>
        <p className="text-[#a0b4c4] mt-1 text-sm">AI-powered risk scoring for all transactions and counterparties.</p>
      </div>
      <div className="glass-panel-elevated rounded-2xl p-12 flex flex-col items-center justify-center text-center gap-4" style={{ minHeight: 320 }}>
        <span className="material-symbols-outlined text-[#a0b4c4]" style={{ fontSize: 48 }}>security</span>
        <h2 className="text-xl font-semibold text-[#e0e8f0]">Risk Intelligence Coming Soon</h2>
        <p className="text-[#a0b4c4] text-sm max-w-md">
          Our ML-powered risk scoring engine is being trained on your transaction data. Check back after more simulation runs.
        </p>
        <button className="mt-2 px-5 py-2.5 rounded-lg text-sm font-medium text-[#001f2e] transition-all hover:opacity-90"
          style={{ background: '#7dd3fc' }}>
          View Analytics Instead
        </button>
      </div>
    </div>
  );
}
