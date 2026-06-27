export default function Toggle({ checked, disabled = false, label, onChange }) {
  return (
    <button
      type="button"
      className={`admin-toggle ${checked ? 'on' : 'off'}`}
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange?.(!checked)}
    >
      <span className="admin-toggle-knob" />
    </button>
  );
}
