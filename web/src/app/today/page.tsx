"use client";

import { useCallback, useEffect, useState } from "react";
import type { ReactNode } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Digest } from "@/lib/types";
import { direction, money, pct, timeAgo } from "@/lib/format";
import { ConnectionError, EmptyState, PageHead, PnLPill } from "@/components/ui";
import { CountUp } from "@/components/CountUp";
import { Reveal } from "@/components/Reveal";

function InsightCard({
  label,
  index,
  children,
}: {
  label: string;
  index: number;
  children: ReactNode;
}) {
  return (
    <Reveal index={index}>
      <div className="panel panel--pad">
        <div className="insight-card__label">{label}</div>
        {children}
      </div>
    </Reveal>
  );
}

export default function TodayPage() {
  const [data, setData] = useState<Digest | null>(null);
  const [loadError, setLoadError] = useState(false);

  const load = useCallback(async () => {
    try {
      setData(await api.getDigest());
      setLoadError(false);
    } catch {
      setLoadError(true);
    }
  }, []);

  useEffect(() => {
    async function run() {
      await load();
    }
    run();
  }, [load]);

  const subtitle = data?.last_refresh
    ? `What's changed since your last refresh, ${timeAgo(data.last_refresh)}.`
    : "What's changed since your last refresh.";

  const topMover = data?.movers[0] ?? null;
  const topDeal = data?.deals[0] ?? null;
  const targetHits = data?.target_hits ?? [];
  const moverDirection = topMover ? direction(topMover.change_pct) : "flat";
  const moverPillClass =
    moverDirection === "up" ? "pill--up" : moverDirection === "down" ? "pill--down" : "pill--flat";

  const isEmpty =
    !!data &&
    data.summary.total_value === 0 &&
    data.movers.length === 0 &&
    data.deals.length === 0 &&
    data.target_hits.length === 0;

  return (
    <div className="container">
      <PageHead eyebrow="Daily" title="Today" subtitle={subtitle} />

      {loadError && !data ? (
        <ConnectionError onRetry={load} />
      ) : data && isEmpty ? (
        <EmptyState
          title="Nothing to show yet"
          action={
            <Link href="/search" className="btn btn--primary">
              Find your first card
            </Link>
          }
        >
          Add cards to your collection and refresh prices — your daily digest will fill in from
          there.
        </EmptyState>
      ) : (
        data && (
          <>
            <section className="slab" aria-label="Today's summary">
              <div className="slab__top">
                <span className="slab__label">Total value</span>
                <PnLPill value={data.summary.pnl} showPct={data.summary.pnl_pct} onSlab />
              </div>
              <div className="slab__value">
                <CountUp value={data.summary.total_value} format={money} />
              </div>
              <div className="slab__stats">
                <div className="slab__stat">
                  <span className="k">Unrealized P&amp;L</span>
                  <span className="v">
                    <PnLPill value={data.summary.pnl} onSlab />
                  </span>
                </div>
                <div className="slab__stat">
                  <span className="k">Realized P&amp;L</span>
                  <span className="v">
                    <PnLPill value={data.realized.realized_pnl} onSlab />
                  </span>
                </div>
                <div className="slab__stat">
                  <span className="k">Sales logged</span>
                  <span className="v">{data.realized.sales_count}</span>
                </div>
              </div>
            </section>

            <section className="section">
              <div className="section__head">
                <span className="section__title">Highlights</span>
              </div>
              <div className="insight-grid">
                <InsightCard label="Top gainer" index={0}>
                  {data.top_gainer ? (
                    <Link
                      href={`/card/${data.top_gainer.card_id}`}
                      className="insight-card__link"
                    >
                      <div className="insight-card__name">{data.top_gainer.card_name}</div>
                      <PnLPill value={data.top_gainer.pnl} />
                    </Link>
                  ) : (
                    <span className="insight-card__empty">—</span>
                  )}
                </InsightCard>

                <InsightCard label="Top loser" index={1}>
                  {data.top_loser ? (
                    <Link
                      href={`/card/${data.top_loser.card_id}`}
                      className="insight-card__link"
                    >
                      <div className="insight-card__name">{data.top_loser.card_name}</div>
                      <PnLPill value={data.top_loser.pnl} />
                    </Link>
                  ) : (
                    <span className="insight-card__empty">—</span>
                  )}
                </InsightCard>

                <InsightCard label="Biggest mover" index={2}>
                  {topMover ? (
                    <Link href={`/card/${topMover.card_id}`} className="insight-card__link">
                      <div className="insight-card__name">{topMover.card_name}</div>
                      <div className="insight-card__detail">{topMover.detail}</div>
                      {topMover.change_pct !== null && (
                        <span className={`pill ${moverPillClass}`}>{pct(topMover.change_pct)}</span>
                      )}
                    </Link>
                  ) : (
                    <span className="insight-card__empty">
                      No movers since your last refresh.
                    </span>
                  )}
                </InsightCard>

                <InsightCard label="Best deal" index={3}>
                  {topDeal ? (
                    <Link href={`/card/${topDeal.card_id}`} className="insight-card__link">
                      <div className="insight-card__name">{topDeal.card_name}</div>
                      <div className="insight-card__detail">{topDeal.detail}</div>
                    </Link>
                  ) : (
                    <span className="insight-card__empty">
                      No listings below market right now.
                    </span>
                  )}
                </InsightCard>

                <InsightCard label="Targets hit" index={4}>
                  {targetHits.length > 0 ? (
                    <Link href="/opportunities" className="insight-card__link">
                      <div className="insight-card__name">{targetHits.length}</div>
                      <div className="insight-card__detail">
                        {targetHits
                          .slice(0, 2)
                          .map((hit) => hit.card_name)
                          .join(", ")}
                        {targetHits.length > 2 ? "…" : ""}
                      </div>
                    </Link>
                  ) : (
                    <span className="insight-card__empty">No watchlist targets hit yet.</span>
                  )}
                </InsightCard>
              </div>
            </section>
          </>
        )
      )}
    </div>
  );
}
