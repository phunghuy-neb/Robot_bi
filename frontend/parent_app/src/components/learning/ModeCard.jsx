export default function ModeCard({ icon, label, sub, color, onClick }) {
  return (
    <button
      type="button"
      className="mode-card"
      onClick={onClick}
      style={color ? { borderColor: color } : undefined}
    >
      <span className="mode-card-icon">{icon}</span>
      <span className="mode-card-label">{label}</span>
      {sub && <span className="mode-card-sub">{sub}</span>}
    </button>
  );
}
