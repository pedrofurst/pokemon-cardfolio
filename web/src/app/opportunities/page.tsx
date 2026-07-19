"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { OpportunitiesResponse, Signal } from "@/lib/types";
import { money, pct } from "@/lib/format";
import { ConnectionError, EmptyState, PageHead } from "@/components/ui";

function SignalGroup({
  title,
  hint,
  tone,
  signals,
}: {
  title: string;
  hint: string;
  tone: "gain" | "gold" | "brand";
  signals: Signal[];
}) {
  const toneClass =
    tone === "gain" ? "pill--up" : tone === "gold" ? "pill--gold" : "pill--brand";
  return (
    <section className="section">
      <div className="section__head">
        <span className="section__title">{title}</span>
        <span className="section__count">{signals.length}</span>
      </div>
      {signals.length === 0 ? (
        <div className="panel panel--pad" style={{ color: "var(--muted)", fontSize: 14 }}>
          {hint}
        </div>
      ) : (
        <div className="panel">
          {signals.map((signal, index) => (
            <Link
              href={`/card/${signal.card_id}`}
              className="signal"
              key={`${signal.card_id}-${index}`}
            >
              <div className="signal__main">
                <div className="signal__name">{signal.card_name}</div>
                <div className="signal__detail">{signal.detail}</div>
              </div>
              {signal.change_pct !== null && (
                <span className={`pill ${toneClass}`}>{pct(signal.change_pct)}</span>
              )}
              <div className="signal__prices">
                <div className="p-now">{money(signal.current_price)}</div>
                <div className="p-ref">ref {money(signal.reference_price)}</div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}

export default function OpportunitiesPage() {
  const [data, setData] = useState<OpportunitiesResponse | null>(null);
  const [loadError, setLoadError] = useState(false);

  const load = useCallback(async () => {
    try {
      setData(await api.listOpportunities());
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

  const total = data
    ? data.movers.length + data.deals.length + data.target_hits.length
    : 0;

  return (
    <div className="container">
      <PageHead
        eyebrow="Signals"
        title="Opportunities"
        subtitle="Computed from your stored price history — refresh prices on the collection to keep it current."
      />

      {loadError && !data ? (
        <ConnectionError onRetry={load} />
      ) : data && total === 0 ? (
        <EmptyState
          title="No signals yet"
          action={
            <Link href="/" className="btn btn--primary">
              Refresh prices
            </Link>
          }
        >
          Signals appear once there&apos;s price history: movers need two refreshes, deals need a listing
          below market, and target hits need a watchlist target.
        </EmptyState>
      ) : (
        data && (
          <>
            <SignalGroup
              title="Movers"
              tone="gain"
              hint="No cards have moved past the threshold since the last refresh."
              signals={data.movers}
            />
            <SignalGroup
              title="Deals"
              tone="brand"
              hint="No listings are sitting notably below market right now."
              signals={data.deals}
            />
            <SignalGroup
              title="Target hits"
              tone="gold"
              hint="No watchlist cards have reached their target price."
              signals={data.target_hits}
            />
          </>
        )
      )}
    </div>
  );
}
