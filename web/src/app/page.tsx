"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { CollectionResponse } from "@/lib/types";
import { money, pct } from "@/lib/format";
import { EmptyState, PageHead, PnLPill } from "@/components/ui";

export default function Home() {
  const [data, setData] = useState<CollectionResponse | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    async function load() {
      setData(await api.listHoldings());
    }
    load();
  }, []);

  async function refresh() {
    setRefreshing(true);
    try {
      await api.refreshPrices();
      setData(await api.listHoldings());
    } finally {
      setRefreshing(false);
    }
  }

  const summary = data?.summary;
  const items = data?.items ?? [];

  return (
    <div className="container">
      <PageHead
        eyebrow="Portfolio"
        title="My collection"
        actions={
          <>
            <Link href="/search" className="btn">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M12 5v14M5 12h14" />
              </svg>
              Add cards
            </Link>
            <button className="btn btn--primary" onClick={refresh} disabled={refreshing}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 12a9 9 0 1 1-2.6-6.4M21 4v5h-5" />
              </svg>
              {refreshing ? "Refreshing…" : "Refresh prices"}
            </button>
          </>
        }
      />

      {summary && (
        <section className="slab" aria-label="Portfolio value">
          <div className="slab__top">
            <span className="slab__label">Total value</span>
            <PnLPill value={summary.pnl} showPct={summary.pnl_pct} onSlab />
          </div>
          <div className="slab__value">{money(summary.total_value)}</div>
          <div className="slab__stats">
            <div className="slab__stat">
              <span className="k">Cost basis</span>
              <span className="v">{money(summary.total_cost)}</span>
            </div>
            <div className="slab__stat">
              <span className="k">Unrealized P&amp;L</span>
              <span className="v">{money(summary.pnl)}</span>
            </div>
            <div className="slab__stat">
              <span className="k">Return</span>
              <span className="v">{pct(summary.pnl_pct)}</span>
            </div>
            <div className="slab__stat">
              <span className="k">Cards</span>
              <span className="v">{items.length}</span>
            </div>
          </div>
        </section>
      )}

      <section className="section">
        <div className="section__head">
          <span className="section__title">Holdings</span>
          {items.length > 0 && <span className="section__count">{items.length}</span>}
        </div>

        {data && items.length === 0 ? (
          <EmptyState
            title="No cards yet"
            action={
              <Link href="/search" className="btn btn--primary">
                Find your first card
              </Link>
            }
          >
            Search a card by name, add what you own with its cost, then refresh prices to see your P&amp;L.
          </EmptyState>
        ) : (
          <div className="card-grid">
            {items.map((item) => {
              const gain = item.pnl > 0;
              return (
                <Link
                  key={item.holding.id}
                  href={`/card/${item.holding.card_id}`}
                  className={`tile${gain ? " tile--gain" : ""}`}
                >
                  <div className="tile__art">
                    {item.card?.image_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={item.card.image_url} alt={item.card?.name ?? "Card"} />
                    ) : (
                      <span className="tile__art--empty">No image</span>
                    )}
                    <span className="tile__sheen" aria-hidden />
                  </div>
                  <div className="tile__body">
                    <div>
                      <div className="tile__name">{item.card?.name ?? item.holding.card_id}</div>
                      <div className="tile__set">
                        {item.card?.set_name || "—"} · {item.holding.condition}
                        {item.holding.quantity > 1 ? ` · ×${item.holding.quantity}` : ""}
                      </div>
                    </div>
                    <div className="tile__foot">
                      <div className="tile__price">
                        <span className="now">
                          {item.current_price === null ? "Unpriced" : money(item.current_price)}
                        </span>
                        <span className="cost">cost {money(item.holding.acquisition_cost)}</span>
                      </div>
                      <PnLPill value={item.pnl} />
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
