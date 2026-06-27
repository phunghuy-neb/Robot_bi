export default function ModeCard({ icon, label, sub, color, comingSoon, onClick }) {
  return (
    <button
      type="button"
      className={`mode-card${comingSoon ? ' coming-soon' : ''}`}
      onClick={onClick}
      aria-disabled={comingSoon || undefined}
      style={color && !comingSoon ? { borderColor: color } : undefined}
    >
      {comingSoon && <span className="mode-card-badge">Sắp có</span>}
      <span className="mode-card-icon">{icon}</span>
      <span className="mode-card-label">{label}</span>
      {sub && <span className="mode-card-sub">{sub}</span>}
    </button>
  );
}
