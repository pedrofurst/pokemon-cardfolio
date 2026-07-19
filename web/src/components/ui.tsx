import type { ReactNode } from "react";
import { direction, pct, signedMoney } from "@/lib/format";

export function PageHead({
  eyebrow,
  title,
  subtitle,
  actions,
}: {
  eyebrow: string;
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="page-head">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1 className="title">{title}</h1>
        {subtitle && <p className="subtitle">{subtitle}</p>}
      </div>
      {actions && <div className="row wrap">{actions}</div>}
    </div>
  );
}

const arrowUp = (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 19V5M6 11l6-6 6 6" />
  </svg>
);
const arrowDown = (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 5v14M6 13l6 6 6-6" />
  </svg>
);

export function PnLPill({
  value,
  showPct,
  onSlab,
}: {
  value: number | null;
  showPct?: number | null;
  onSlab?: boolean;
}) {
  const dir = direction(value);
  const cls = dir === "up" ? "pill--up" : dir === "down" ? "pill--down" : "pill--flat";
  return (
    <span className={`pill ${cls}${onSlab ? " pill--on-slab" : ""}`}>
      {dir === "up" ? arrowUp : dir === "down" ? arrowDown : null}
      {signedMoney(value)}
      {showPct !== undefined && showPct !== null ? ` · ${pct(showPct)}` : ""}
    </span>
  );
}

export function EmptyState({
  title,
  children,
  action,
}: {
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="empty empty--panel">
      <svg
        className="empty__glyph"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <rect x="4" y="3" width="16" height="18" rx="2" />
        <path d="M8 8h8M8 12h8M8 16h5" />
      </svg>
      <div className="empty__title">{title}</div>
      {children && <p style={{ margin: 0, maxWidth: "40ch" }}>{children}</p>}
      {action && <div style={{ marginTop: 6 }}>{action}</div>}
    </div>
  );
}
