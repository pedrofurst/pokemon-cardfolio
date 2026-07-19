"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Booster, StoreResponse } from "@/lib/types";
import { useMoney } from "@/components/Currency";
import { ConnectionError, EmptyState, PageHead } from "@/components/ui";
import { Reveal } from "@/components/Reveal";
import { SkeletonCardGrid } from "@/components/Skeleton";

function OddsRow({
  estHitPct,
  oneIn,
}: {
  estHitPct: number | null;
  oneIn: number | null;
}) {
  if (estHitPct === null) {
    return <div className="odds-row odds-row--unknown">Not enough price data for an estimate.</div>;
  }
  return (
    <div className="odds-row">
      <span>
        ≈ {estHitPct}% chance the rare slot is a card worth ≥$15
      </span>
      {oneIn !== null && <span className="odds-row__sep">· ≈ 1 in {oneIn} packs</span>}
    </div>
  );
}

function BoosterPanel({ booster, index }: { booster: Booster; index: number }) {
  const { fmt } = useMoney();

  return (
    <Reveal index={index}>
      <div className="panel panel--pad booster">
        <div className="booster__head">
          {booster.logo_url && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={booster.logo_url} alt={booster.set_name} height={40} className="booster__logo" />
          )}
          <div className="booster__title">
            <span className="booster__name">{booster.set_name}</span>
            <span className="booster__date">{booster.release_date}</span>
          </div>
        </div>

        <OddsRow estHitPct={booster.est_hit_pct} oneIn={booster.one_in} />

        {booster.chase_cards.length > 0 && (
          <div className="chase-row">
            {booster.chase_cards.map((card) => (
              <a
                key={card.id}
                href={card.buy_url}
                target="_blank"
                rel="noopener noreferrer"
                className="chase-card"
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={card.image_url} alt={card.name} className="chase-card__image" />
                <span className="chase-card__name">{card.name}</span>
                <span className="chase-card__price">{fmt(card.price)}</span>
              </a>
            ))}
          </div>
        )}

        <div className="row wrap booster__actions">
          <a
            href={booster.booster_links.tcgplayer}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn--primary"
          >
            TCGplayer
          </a>
          <a
            href={booster.booster_links.ebay}
            target="_blank"
            rel="noopener noreferrer"
            className="btn"
          >
            eBay
          </a>
        </div>
      </div>
    </Reveal>
  );
}

export default function StorePage() {
  const [data, setData] = useState<StoreResponse | null>(null);
  const [loadError, setLoadError] = useState(false);

  const load = useCallback(async () => {
    try {
      const result = await api.getStore();
      setData(result);
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

  const loading = data === null && !loadError;
  const boosters = data?.boosters ?? [];

  return (
    <div className="container">
      <PageHead
        eyebrow="Buy"
        title="Store"
        subtitle="Boosters worth a look — chase cards, estimated odds, and where to buy."
      />

      <div className="panel panel--pad disclaimer">
        Odds are rough estimates, not official pull rates. Prices via pokemontcg.io. Not
        affiliated with any store. Not financial advice.
      </div>

      {loading ? (
        <SkeletonCardGrid count={4} />
      ) : loadError && !data ? (
        <ConnectionError onRetry={load} />
      ) : boosters.length === 0 ? (
        <EmptyState title="No boosters to show">
          Check back later — we couldn&apos;t find any sets with enough price data right now.
        </EmptyState>
      ) : (
        <div className="booster-list">
          {boosters.map((booster, index) => (
            <BoosterPanel key={booster.set_id} booster={booster} index={index} />
          ))}
        </div>
      )}
    </div>
  );
}
