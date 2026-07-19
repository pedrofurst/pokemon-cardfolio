"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

type NavItem = { href: string; label: string; icon: ReactNode; match: (p: string) => boolean };

const icons = {
  today: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="4.5" />
      <path d="M12 2.5v2.5M12 19v2.5M4.2 4.2l1.8 1.8M18 18l1.8 1.8M2.5 12H5M19 12h2.5M4.2 19.8 6 18M18 6l1.8-1.8" />
    </svg>
  ),
  collection: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  ),
  search: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.2-3.2" />
    </svg>
  ),
  watchlist: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  ),
  opportunities: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 17l6-6 4 4 7-7" />
      <path d="M14 7h6v6" />
    </svg>
  ),
  grading: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3l7 3v5c0 4.4-3 8-7 10-4-2-7-5.6-7-10V6l7-3Z" />
      <path d="m9 11 2 2 4-4" />
    </svg>
  ),
  priceCheck: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20.5 12.4 12.9 20a2 2 0 0 1-2.8 0l-6.1-6.1a2 2 0 0 1 0-2.8l7.6-7.6a2 2 0 0 1 1.4-.6H19a1.5 1.5 0 0 1 1.5 1.5v6.1a2 2 0 0 1-.6 1.4Z" />
      <circle cx="14.5" cy="8.5" r="1.5" />
    </svg>
  ),
  sales: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 3h14v17l-3.5-2-3.5 2-3.5-2L5 20V3Z" />
      <path d="M8.5 9h7M8.5 13h4.5" />
    </svg>
  ),
};

const NAV: NavItem[] = [
  { href: "/today", label: "Today", icon: icons.today, match: (p) => p.startsWith("/today") },
  { href: "/", label: "Collection", icon: icons.collection, match: (p) => p === "/" || p.startsWith("/card") },
  { href: "/search", label: "Search & add", icon: icons.search, match: (p) => p.startsWith("/search") },
  { href: "/price-check", label: "Price check", icon: icons.priceCheck, match: (p) => p.startsWith("/price-check") },
  { href: "/watchlist", label: "Watchlist", icon: icons.watchlist, match: (p) => p.startsWith("/watchlist") },
  { href: "/opportunities", label: "Opportunities", icon: icons.opportunities, match: (p) => p.startsWith("/opportunities") },
  { href: "/grading", label: "Grading", icon: icons.grading, match: (p) => p.startsWith("/grading") },
  { href: "/sales", label: "Sales", icon: icons.sales, match: (p) => p.startsWith("/sales") },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname() ?? "/";

  return (
    <div className="app">
      <aside className="sidebar">
        <Link href="/" className="brand" aria-label="Cardfolio home">
          <span className="brand__mark" aria-hidden />
          <span className="brand__name">
            Cardfolio
            <small>collection ledger</small>
          </span>
        </Link>
        <nav className="nav" aria-label="Primary">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`nav-link${item.match(pathname) ? " active" : ""}`}
              aria-current={item.match(pathname) ? "page" : undefined}
            >
              {item.icon}
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>
        <p className="sidebar__foot">
          Prices via pokemontcg.io · USD.
          <br />
          For tracking, not advice.
        </p>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}
