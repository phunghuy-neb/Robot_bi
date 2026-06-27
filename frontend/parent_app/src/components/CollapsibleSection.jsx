import { useId, useState } from 'react';

export default function CollapsibleSection({
  title,
  actions = null,
  children,
  defaultExpanded = true,
  className = '',
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const contentId = useId();

  return (
    <section className={`card collapsible-section ${expanded ? '' : 'collapsed'} ${className}`.trim()}>
      <div className="card-header collapsible-section-header">
        <button
          type="button"
          className="collapsible-section-toggle"
          aria-expanded={expanded}
          aria-controls={contentId}
          onClick={() => setExpanded(value => !value)}
        >
          <span className="collapsible-section-caret" aria-hidden="true">▾</span>
          <span className="card-title">{title}</span>
        </button>
        {actions && <div className="collapsible-section-actions">{actions}</div>}
      </div>
      {expanded && (
        <div id={contentId} className="collapsible-section-body">
          {children}
        </div>
      )}
    </section>
  );
}
