"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { HoldingView } from "@/lib/types";
import { money } from "@/lib/format";
import { PnLPill } from "@/components/ui";

export default function CardDetail() {
  const params = useParams<{ id: string }>();
  const [view, setView] = useState<HoldingView | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    api.listHoldings().then((data) => {
      setView(data.items.find((i) => i.holding.card_id === params.id) ?? null);
      setLoaded(true);
    });
  }, [params.id]);

  const backLink = (
    <Link href="/" className="back-link">
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M15 18l-6-6 6-6" />
      </svg>
      Back to collection
    </Link>
  );

  if (!loaded) {
    return <div className="container">{backLink}<p style={{ color: "var(--muted)" }}>Loading…</p></div>;
  }

  if (!view) {
    return (
      <div className="container">
        {backLink}
        <div className="empty empty--panel">
          <div className="empty__title">Not in your collection</div>
          <p style={{ margin: 0 }}>
            This card ({params.id}) isn&apos;t among your holdings. You can still run a grading
            estimate for it.
          </p>
          <Link href={`/grading?card_id=${params.id}`} className="btn btn--primary" style={{ marginTop: 6 }}>
            Estimate grading
          </Link>
        </div>
      </div>
    );
  }

  const gain = view.pnl > 0;

  return (
    <div className="container">
      {backLink}
      <div className="grid-2">
        <div className={`tile${gain ? " tile--gain" : ""}`} style={{ maxWidth: 340 }}>
          <div className="tile__art">
            {view.card?.image_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={view.card.image_url} alt={view.card?.name ?? "Card"} />
            ) : (
              <span className="tile__art--empty">No image</span>
            )}
            <span className="tile__sheen" aria-hidden />
          </div>
        </div>

        <div className="stack">
          <div>
            <div className="eyebrow">{view.card?.set_name || "Card"}</div>
            <h1 className="title">{view.card?.name ?? params.id}</h1>
            <div className="row wrap" style={{ marginTop: 10 }}>
              <span className="badge">{view.holding.condition}</span>
              {view.holding.is_graded && <span className="badge badge--gold">graded</span>}
              {view.holding.quantity > 1 && <span className="badge">×{view.holding.quantity}</span>}
            </div>
          </div>

          <div className="panel panel--pad">
            <div className="ledger">
              <div className="ledger__row">
                <span className="ledger__k">Current price</span>
                <span className="ledger__v">
                  {view.current_price === null ? "Unpriced" : money(view.current_price)}
                </span>
              </div>
              <div className="ledger__row">
                <span className="ledger__k">Cost basis</span>
                <span className="ledger__v">{money(view.holding.acquisition_cost)}</span>
              </div>
              <div className="ledger__row is-total">
                <span className="ledger__k" style={{ color: "var(--ink)", fontWeight: 600 }}>
                  Unrealized P&amp;L
                </span>
                <PnLPill value={view.pnl} />
              </div>
            </div>
          </div>

          <div className="row wrap">
            <Link href={`/grading?card_id=${view.holding.card_id}`} className="btn btn--primary">
              Should I grade it?
            </Link>
            <Link href="/search" className="btn">
              Add another
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
