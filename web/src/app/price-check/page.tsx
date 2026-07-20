"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { CardResult, PriceCheckResult } from "@/lib/types";
import { money, pct } from "@/lib/format";
import { EmptyState, PageHead } from "@/components/ui";
import { SkeletonCardGrid } from "@/components/Skeleton";

type Tone = "gain" | "gold" | "loss" | "brand";

interface VerdictMeta {
  label: string;
  cls: string;
  tone: Tone;
}

const VERDICT_META: Record<string, VerdictMeta> = {
  great_deal: { label: "Great deal", cls: "reco--grade", tone: "gain" },
  fair: { label: "Fair price", cls: "reco--fair", tone: "brand" },
  slightly_low: { label: "A little under", cls: "reco--insufficient", tone: "gold" },
  slightly_high: { label: "A little over", cls: "reco--insufficient", tone: "gold" },
  overpriced: { label: "Overpriced", cls: "reco--dont", tone: "loss" },
};

function verdictMeta(verdict: string): VerdictMeta {
  return VERDICT_META[verdict] ?? { label: verdict, cls: "reco--insufficient", tone: "gold" };
}

interface GaugeDomain {
  min: number;
  max: number;
}

function computeGaugeDomain(result: PriceCheckResult): GaugeDomain {
  const lowFloor = result.low ?? result.market * 0.6;
  const min = Math.min(lowFloor, result.offer, result.market) * 0.95;
  const max = Math.max(result.market * 1.4, result.offer) * 1.02;
  return { min, max };
}

function positionPct(value: number, domain: GaugeDomain): number {
  if (domain.max <= domain.min) {
    return 50;
  }
  const raw = ((value - domain.min) / (domain.max - domain.min)) * 100;
  return Math.min(100, Math.max(0, raw));
}

function deltaColor(deltaPct: number): string {
  if (deltaPct > 0) {
    return "var(--loss)";
  }
  if (deltaPct < 0) {
    return "var(--gain)";
  }
  return "var(--ink)";
}

function PriceGauge({ result }: { result: PriceCheckResult }) {
  const domain = computeGaugeDomain(result);
  const marketPosition = positionPct(result.market, domain);
  const offerPosition = positionPct(result.offer, domain);
  const tone = verdictMeta(result.verdict).tone;
  // Deterministic initial render (server and client agree): start at the market
  // position, then move to the offer after mount. Reduced-motion is handled in
  // CSS (the marker transition is disabled), so we never read matchMedia here.
  const [markerPosition, setMarkerPosition] = useState(marketPosition);

  useEffect(() => {
    const frame = requestAnimationFrame(() => setMarkerPosition(offerPosition));
    return () => cancelAnimationFrame(frame);
  }, [offerPosition]);

  return (
    <div className="gauge">
      <div className="gauge__track">
        <span className="gauge__tick" style={{ left: `${marketPosition}%` }}>
          <span>Market · {money(result.market)}</span>
          <span className="gauge__tick-line" />
        </span>
        <span
          className={`gauge__marker gauge__marker--${tone}`}
          style={{ left: `${markerPosition}%` }}
        >
          <span className="gauge__marker-dot" />
          <span className="gauge__marker-label">Your offer · {money(result.offer)}</span>
        </span>
      </div>
    </div>
  );
}

export default function PriceCheckPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<CardResult[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [selected, setSelected] = useState<CardResult | null>(null);
  const [offerPrice, setOfferPrice] = useState("");
  const [checking, setChecking] = useState(false);
  const [checkError, setCheckError] = useState<string | null>(null);
  const [result, setResult] = useState<PriceCheckResult | null>(null);

  async function runSearch() {
    if (!query.trim()) return;
    setSearching(true);
    try {
      setResults(await api.searchCards(query));
    } catch {
      setResults([]);
    } finally {
      setSearching(false);
    }
  }

  function selectCard(card: CardResult) {
    setSelected(card);
    setResult(null);
    setCheckError(null);
    setOfferPrice("");
  }

  function changeCard() {
    setSelected(null);
    setResult(null);
    setCheckError(null);
  }

  async function runCheck() {
    if (!selected) return;
    const offer = Number(offerPrice);
    if (offerPrice.trim() === "" || Number.isNaN(offer) || offer < 0) {
      setCheckError("Enter a valid asking price of 0 or more.");
      return;
    }
    setCheckError(null);
    setChecking(true);
    try {
      setResult(await api.checkPrice({ card_id: selected.id, offer_price: offer }));
    } catch {
      setCheckError("Couldn't check this price. Check the backend is running and try again.");
      setResult(null);
    } finally {
      setChecking(false);
    }
  }

  const meta = result ? verdictMeta(result.verdict) : null;

  return (
    <div className="container">
      <PageHead
        eyebrow="Buy-time check"
        title="Am I overpaying?"
        subtitle="Search a card, enter the asking price, and see how it stacks up against the market."
      />

      {!selected && (
        <>
          <form
            className="searchbar"
            onSubmit={(e) => {
              e.preventDefault();
              runSearch();
            }}
          >
            <input
              className="input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Charizard, Umbreon, Pikachu…"
              autoFocus
            />
            <button className="btn btn--primary" type="submit" disabled={searching}>
              {searching ? "Searching…" : "Search"}
            </button>
          </form>

          {searching && <SkeletonCardGrid count={4} />}

          {!searching && results === null && (
            <EmptyState title="Start with a name">
              Type a card name and hit Search, then pick the card you were offered.
            </EmptyState>
          )}

          {!searching && results !== null && results.length === 0 && (
            <EmptyState title="No matches">
              Nothing came back for “{query}”. Try a different spelling or a shorter term.
            </EmptyState>
          )}

          {!searching && results !== null && results.length > 0 && (
            <div className="card-grid">
              {results.map((card) => (
                <div className="tile" key={card.id}>
                  <div className="tile__art">
                    {card.image_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={card.image_url} alt={card.name} />
                    ) : (
                      <span className="tile__art--empty">No image</span>
                    )}
                  </div>
                  <div className="tile__body">
                    <div>
                      <div className="tile__name">{card.name}</div>
                      <div className="tile__set">
                        {card.set_name || "—"} · #{card.number || "—"}
                      </div>
                    </div>
                    <div className="tile__foot">
                      <div className="tile__price">
                        <span className="now">
                          {card.market_price === null ? "Unpriced" : money(card.market_price)}
                        </span>
                        <span className="cost">market</span>
                      </div>
                    </div>
                  </div>
                  <div className="tile__actions">
                    <button
                      className="btn btn--primary btn--sm"
                      onClick={() => selectCard(card)}
                    >
                      Select
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {selected && (
        <div className="grid-2">
          <div className="panel panel--pad stack">
            <div className="row" style={{ justifyContent: "space-between" }}>
              <div className="row">
                {selected.image_url && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img className="modal__thumb" src={selected.image_url} alt={selected.name} />
                )}
                <div>
                  <div className="tile__name">{selected.name}</div>
                  <div className="tile__set">{selected.set_name || "—"}</div>
                </div>
              </div>
              <button className="btn btn--sm" onClick={changeCard}>
                Change card
              </button>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                runCheck();
              }}
            >
              <label className="field">
                <span className="label">What are you being asked to pay? (USD)</span>
                <input
                  className="input num"
                  inputMode="decimal"
                  value={offerPrice}
                  onChange={(e) => setOfferPrice(e.target.value)}
                  placeholder="0.00"
                  autoFocus
                />
                <span className="hint">We&apos;ll compare this against the live market price.</span>
              </label>
              {checkError && <p className="alert" style={{ marginTop: 12 }}>{checkError}</p>}
              <button
                className="btn btn--primary"
                type="submit"
                style={{ marginTop: 14, width: "100%", justifyContent: "center" }}
                disabled={checking}
              >
                {checking ? "Checking…" : "Check price"}
              </button>
            </form>
          </div>

          <div className="panel panel--pad">
            {!result || !meta ? (
              <EmptyState title="Your verdict shows here">
                Enter an asking price and hit Check price to see if it&apos;s a deal.
              </EmptyState>
            ) : (
              <div className="stack">
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <span className={`reco ${meta.cls}`}>
                    <span className="reco__dot" />
                    {meta.label}
                  </span>
                  <span className="badge" style={{ color: deltaColor(result.delta_pct) }}>
                    Δ {pct(result.delta_pct)}
                  </span>
                </div>
                <p style={{ margin: 0, color: "var(--muted)" }}>{result.detail}</p>

                <PriceGauge result={result} />

                <div className="ledger">
                  <div className="ledger__row">
                    <span className="ledger__k">Your offer</span>
                    <span className="ledger__v">{money(result.offer)}</span>
                  </div>
                  <div className="ledger__row">
                    <span className="ledger__k">Market</span>
                    <span className="ledger__v">{money(result.market)}</span>
                  </div>
                  <div className="ledger__row">
                    <span className="ledger__k">Low</span>
                    <span className="ledger__v">{money(result.low)}</span>
                  </div>
                  <div className="ledger__row">
                    <span className="ledger__k">Direct low</span>
                    <span className="ledger__v">{money(result.direct_low)}</span>
                  </div>
                  <div className="ledger__row is-total">
                    <span className="ledger__k" style={{ color: "var(--ink)", fontWeight: 600 }}>
                      Δ vs. market
                    </span>
                    <span
                      className="ledger__v"
                      style={{ color: deltaColor(result.delta_pct) }}
                    >
                      {pct(result.delta_pct)}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
