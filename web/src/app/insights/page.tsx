"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { InsightsResponse } from "@/lib/types";
import { useMoney } from "@/components/Currency";
import { ConnectionError, EmptyState, PageHead } from "@/components/ui";
import { Reveal } from "@/components/Reveal";

function SetRow({
  setId,
  setName,
  owned,
  total,
  pct,
}: {
  setId: string;
  setName: string;
  owned: number;
  total: number | null;
  pct: number | null;
}) {
  return (
    <div className="progress-row" key={setId}>
      <div className="progress-row__head">
        <span className="progress-row__name">{setName}</span>
        <span className="progress-row__count">{total !== null ? `${owned}/${total}` : owned}</span>
      </div>
      <div className="progress" role="progressbar" aria-valuenow={pct ?? undefined} aria-valuemin={0} aria-valuemax={100}>
        <div className="progress__fill" style={{ width: `${pct !== null ? Math.min(pct, 100) : 0}%` }} />
      </div>
    </div>
  );
}

function BarRow({
  label,
  value,
  pct,
  fmt,
}: {
  label: string;
  value: number;
  pct: number;
  fmt: (value: number) => string;
}) {
  return (
    <div className="bar-row">
      <div className="bar-row__head">
        <span className="bar-row__label">{label}</span>
        <span className="bar-row__value">
          {fmt(value)} <span className="bar-row__pct">· {pct.toFixed(1)}%</span>
        </span>
      </div>
      <div className="progress progress--sm">
        <div className="progress__fill" style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
    </div>
  );
}

export default function InsightsPage() {
  const { fmt } = useMoney();
  const [data, setData] = useState<InsightsResponse | null>(null);
  const [loadError, setLoadError] = useState(false);

  const load = useCallback(async () => {
    try {
      setData(await api.getInsights());
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

  const sets = data?.sets ?? [];
  const allocation = data?.allocation ?? null;
  const hasAllocation = !!allocation && allocation.total_value > 0;

  return (
    <div className="container">
      <PageHead
        eyebrow="Analysis"
        title="Insights"
        subtitle="Set completion and where your collection's value actually sits."
      />

      {loadError && !data ? (
        <ConnectionError onRetry={load} />
      ) : (
        data && (
          <>
            <section className="section">
              <div className="section__head">
                <span className="section__title">Set completion</span>
                {sets.length > 0 && <span className="section__count">{sets.length}</span>}
              </div>
              {sets.length === 0 ? (
                <EmptyState title="No sets tracked yet">
                  Add cards to your collection — once a card&apos;s set is known, its completion
                  progress will show up here.
                </EmptyState>
              ) : (
                <Reveal index={0}>
                  <div className="panel panel--pad progress-list">
                    {sets.map((set) => (
                      <SetRow
                        key={set.set_id}
                        setId={set.set_id}
                        setName={set.set_name}
                        owned={set.owned}
                        total={set.total}
                        pct={set.pct}
                      />
                    ))}
                  </div>
                </Reveal>
              )}
            </section>

            <section className="section">
              <div className="section__head">
                <span className="section__title">Where your money is</span>
              </div>
              {!hasAllocation ? (
                <EmptyState title="No value to allocate yet">
                  Once your cards have priced holdings, this breaks the total value down by set
                  and rarity.
                </EmptyState>
              ) : (
                allocation && (
                  <div className="insight-grid insight-grid--wide">
                    <Reveal index={1}>
                      <div className="panel panel--pad">
                        <div className="insight-card__label">By set</div>
                        <div className="bar-list">
                          {allocation.by_set.map((slice) => (
                            <BarRow
                              key={slice.name}
                              label={slice.name}
                              value={slice.value}
                              pct={slice.pct}
                              fmt={fmt}
                            />
                          ))}
                        </div>
                      </div>
                    </Reveal>

                    <Reveal index={2}>
                      <div className="panel panel--pad">
                        <div className="insight-card__label">By rarity</div>
                        <div className="bar-list">
                          {allocation.by_rarity.map((slice) => (
                            <BarRow
                              key={slice.rarity}
                              label={slice.rarity}
                              value={slice.value}
                              pct={slice.pct}
                              fmt={fmt}
                            />
                          ))}
                        </div>
                      </div>
                    </Reveal>

                    <Reveal index={3}>
                      <div className="panel panel--pad">
                        <div className="insight-card__label">Top cards</div>
                        <div className="top-cards">
                          {allocation.top_cards.map((card) => (
                            <Link
                              href={`/card/${card.card_id}`}
                              className="top-cards__row"
                              key={card.card_id}
                            >
                              <span className="top-cards__name">{card.name}</span>
                              <span className="top-cards__value">{fmt(card.value)}</span>
                            </Link>
                          ))}
                        </div>
                      </div>
                    </Reveal>
                  </div>
                )
              )}
            </section>
          </>
        )
      )}
    </div>
  );
}
