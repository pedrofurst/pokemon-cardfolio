"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { CollectionResponse, PortfolioPoint, PriceStatus } from "@/lib/types";
import { pct, timeAgo } from "@/lib/format";
import { useMoney } from "@/components/Currency";
import { useToast } from "@/components/Toast";
import { ConnectionError, EmptyState, PageHead, PnLPill } from "@/components/ui";
import { CountUp } from "@/components/CountUp";
import { TrendChart } from "@/components/TrendChart";
import { Reveal } from "@/components/Reveal";
import { TiltCard } from "@/components/TiltCard";
import { SkeletonCardGrid, SkeletonSlab } from "@/components/Skeleton";

type FlashDirection = "up" | "down";

const FLASH_DURATION_MS = 900;

export default function Home() {
  const { fmt } = useMoney();
  const { toast } = useToast();
  const [data, setData] = useState<CollectionResponse | null>(null);
  const [archivedData, setArchivedData] = useState<CollectionResponse | null>(null);
  const [showingArchived, setShowingArchived] = useState(false);
  const [portfolioHistory, setPortfolioHistory] = useState<PortfolioPoint[]>([]);
  const [priceStatus, setPriceStatus] = useState<PriceStatus | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefreshFailed, setLastRefreshFailed] = useState(0);
  const [loadError, setLoadError] = useState(false);
  const [flashed, setFlashed] = useState<Record<string, FlashDirection>>({});
  const flashTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async () => {
    try {
      const [holdings, archived, history, status] = await Promise.all([
        api.listHoldings(),
        api.listHoldings(true),
        api.getPortfolioHistory(),
        api.getPriceStatus(),
      ]);
      setData(holdings);
      setArchivedData(archived);
      setPortfolioHistory(history);
      setPriceStatus(status);
      setLoadError(false);
      return archived;
    } catch {
      setLoadError(true);
      return null;
    }
  }, []);

  useEffect(() => {
    async function run() {
      await load();
    }
    run();
  }, [load]);

  useEffect(() => {
    return () => {
      if (flashTimeoutRef.current) {
        clearTimeout(flashTimeoutRef.current);
      }
    };
  }, []);

  async function restore(holdingId: string) {
    try {
      await api.restoreHolding(holdingId);
      const archived = await load();
      if (archived !== null && archived.items.length === 0) {
        setShowingArchived(false);
      }
    } catch {
      toast("Couldn't restore that card.", "error");
    }
  }

  async function refresh() {
    setRefreshing(true);
    const previousPricesByCardId = new Map(
      (data?.items ?? []).map((item) => [item.holding.card_id, item.current_price])
    );
    try {
      const result = await api.refreshPrices();
      setLastRefreshFailed(result.failed);
      const holdings = await api.listHoldings();
      const nextFlashed: Record<string, FlashDirection> = {};
      for (const item of holdings.items) {
        const previousPrice = previousPricesByCardId.get(item.holding.card_id);
        if (previousPrice === undefined) {
          continue;
        }
        if (item.current_price !== null && previousPrice !== null && item.current_price !== previousPrice) {
          nextFlashed[item.holding.card_id] = item.current_price > previousPrice ? "up" : "down";
        }
      }
      setData(holdings);
      const [history, status] = await Promise.all([api.getPortfolioHistory(), api.getPriceStatus()]);
      setPortfolioHistory(history);
      setPriceStatus(status);
      setLoadError(false);
      if (Object.keys(nextFlashed).length > 0) {
        setFlashed(nextFlashed);
        if (flashTimeoutRef.current) {
          clearTimeout(flashTimeoutRef.current);
        }
        flashTimeoutRef.current = setTimeout(() => {
          setFlashed({});
        }, FLASH_DURATION_MS);
      }
    } catch {
      setLoadError(true);
    } finally {
      setRefreshing(false);
    }
  }

  const summary = data?.summary;
  const items = data?.items ?? [];
  const visibleItems = showingArchived ? archivedData?.items ?? [] : items;

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
            <div style={{ position: "relative" }}>
              <button className="btn btn--primary" onClick={refresh} disabled={refreshing}>
                <svg
                  className={refreshing ? "spin" : undefined}
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M21 12a9 9 0 1 1-2.6-6.4M21 4v5h-5" />
                </svg>
                {refreshing ? "Refreshing…" : "Refresh prices"}
              </button>
              {priceStatus?.last_refresh && (
                <span
                  style={{
                    position: "absolute",
                    top: "calc(100% + 5px)",
                    right: 0,
                    whiteSpace: "nowrap",
                    color: "var(--muted)",
                    fontSize: 12,
                  }}
                >
                  Updated {timeAgo(priceStatus.last_refresh)}
                  {lastRefreshFailed > 0 ? ` · ${lastRefreshFailed} couldn't be priced` : ""}
                </span>
              )}
            </div>
          </>
        }
      />

      {data === null && !loadError ? (
        <>
          <SkeletonSlab />
          <section className="section">
            <div className="section__head">
              <span className="section__title">Holdings</span>
            </div>
            <SkeletonCardGrid />
          </section>
        </>
      ) : loadError && !data ? (
        <ConnectionError onRetry={load} />
      ) : (
        <>
      {summary && (
        <section className="slab" aria-label="Portfolio value">
          <div className="slab__top">
            <span className="slab__label">Total value</span>
            <PnLPill value={summary.pnl} showPct={summary.pnl_pct} onSlab />
          </div>
          <div className="slab__value">
            <CountUp value={summary.total_value} format={fmt} />
          </div>
          <div className="slab__stats">
            <div className="slab__stat">
              <span className="k">Cost basis</span>
              <span className="v">{fmt(summary.total_cost)}</span>
            </div>
            <div className="slab__stat">
              <span className="k">Unrealized P&amp;L</span>
              <span className="v">
                <CountUp value={summary.pnl} format={fmt} />
              </span>
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
          <div style={{ marginTop: 16 }}>
            <TrendChart
              points={portfolioHistory.map((point) => ({ t: point.fetched_at, v: point.total_value }))}
              accent="var(--brand)"
              height={72}
              ariaLabel="Portfolio value over time"
            />
          </div>
        </section>
      )}

      <section className="section">
        <div className="section__head">
          <span className="section__title">Holdings</span>
          {visibleItems.length > 0 && <span className="section__count">{visibleItems.length}</span>}
          {(archivedData?.items.length ?? 0) > 0 && (
            <button
              className={`btn btn--sm${showingArchived ? " btn--primary" : ""}`}
              onClick={() => setShowingArchived((previous) => !previous)}
            >
              Archived ({archivedData?.items.length ?? 0})
            </button>
          )}
        </div>

        {data && visibleItems.length === 0 ? (
          showingArchived ? (
            <EmptyState title="No archived cards">
              Restoring a card brings it back to your active collection.
            </EmptyState>
          ) : (
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
          )
        ) : (
          <div className="card-grid">
            {visibleItems.map((item, index) => {
              const gain = item.pnl > 0;
              const flashDirection = flashed[item.holding.card_id];
              const flashClassName = flashDirection ? ` flash-${flashDirection}` : "";
              const archivedClassName = showingArchived ? " tile--archived" : "";
              return (
                <Reveal key={item.holding.id} index={index}>
                  <TiltCard>
                    <Link
                      href={`/card/${item.holding.card_id}`}
                      className={`tile${gain ? " tile--gain" : ""}${flashClassName}${archivedClassName}`}
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
                          {item.holding.variant !== "normal" && (
                            <span className="badge badge--brand">{item.holding.variant}</span>
                          )}
                        </div>
                        <div className="tile__foot">
                          <div className="tile__price">
                            <span className="now">
                              {item.current_price === null ? "Unpriced" : fmt(item.current_price)}
                            </span>
                            <span className="cost">cost {fmt(item.holding.acquisition_cost)}</span>
                          </div>
                          <PnLPill value={item.pnl} />
                        </div>
                      </div>
                      {showingArchived && (
                        <div className="tile__actions">
                          <button
                            className="btn btn--sm"
                            onClick={(event) => {
                              event.preventDefault();
                              restore(item.holding.id);
                            }}
                          >
                            Restore
                          </button>
                        </div>
                      )}
                    </Link>
                  </TiltCard>
                </Reveal>
              );
            })}
          </div>
        )}
      </section>
        </>
      )}
    </div>
  );
}
