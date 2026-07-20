"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { CardResult } from "@/lib/types";
import { useMoney } from "@/components/Currency";
import { EmptyState, PageHead } from "@/components/ui";
import { TiltCard } from "@/components/TiltCard";
import { SkeletonCardGrid } from "@/components/Skeleton";
import { PackReveal } from "@/components/PackReveal";
import { useToast } from "@/components/Toast";

const CONDITION_OPTIONS: { value: string; label: string }[] = [
  { value: "raw", label: "Raw" },
  { value: "NM", label: "Near Mint (NM)" },
  { value: "LP", label: "Lightly Played (LP)" },
  { value: "MP", label: "Moderately Played (MP)" },
  { value: "HP", label: "Heavily Played (HP)" },
  { value: "DMG", label: "Damaged (DMG)" },
];

const VARIANT_OPTIONS: { value: string; label: string }[] = [
  { value: "normal", label: "Normal" },
  { value: "holofoil", label: "Holofoil" },
  { value: "reverse", label: "Reverse Holo" },
  { value: "1st_edition", label: "1st Edition" },
];

function SearchPageFallback() {
  return (
    <div className="container">
      <PageHead
        eyebrow="Add cards"
        title="Search & add"
        subtitle="Find a card by name, then add a copy you own or put it on your watchlist."
      />
      <SkeletonCardGrid />
    </div>
  );
}

function SearchPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryParam = searchParams.get("q") ?? "";
  const { toast } = useToast();
  const { fmt } = useMoney();
  const [query, setQuery] = useState(queryParam);
  const [results, setResults] = useState<CardResult[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [selected, setSelected] = useState<CardResult | null>(null);
  const [cost, setCost] = useState("");
  const [condition, setCondition] = useState("raw");
  const [variant, setVariant] = useState("normal");
  const [saving, setSaving] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);
  const [watchError, setWatchError] = useState<string | null>(null);
  const [watched, setWatched] = useState<Set<string>>(new Set());
  const [revealed, setRevealed] = useState<CardResult | null>(null);

  // The URL is the single source of truth for what's being searched: submitting
  // pushes ?q=, and this effect reacts to it. That keeps a reload, a shared
  // link, and back/forward all landing on the same results, and avoids the
  // double fetch you'd get from searching on submit *and* on param change.
  const runSearch = useCallback(async (term: string) => {
    if (!term.trim()) return;
    setSearching(true);
    setWatchError(null);
    try {
      setResults(await api.searchCards(term));
    } catch {
      setResults([]);
    } finally {
      setSearching(false);
    }
  }, []);

  useEffect(() => {
    async function run() {
      await runSearch(queryParam);
    }
    run();
  }, [queryParam, runSearch]);

  function submitSearch() {
    const term = query.trim();
    if (!term) return;
    router.push(`/search?q=${encodeURIComponent(term)}`);
  }

  async function add() {
    if (!selected) return;
    setAddError(null);
    setSaving(true);
    try {
      await api.addHolding({
        card: selected,
        acquisition_cost: Number(cost) || 0,
        quantity: 1,
        condition,
        variant,
      });
      toast("Added to your collection");
      if (selected.image_url) {
        setRevealed(selected);
      } else {
        router.push("/");
      }
      setSelected(null);
    } catch {
      setAddError("Couldn't add this card. Check the backend is running and try again.");
      toast("Couldn't add this card", "error");
    } finally {
      setSaving(false);
    }
  }

  async function watch(card: CardResult) {
    setWatchError(null);
    try {
      await api.addWatch({ card, target_price: null });
      setWatched((prev) => new Set(prev).add(card.id));
      toast("Added to watchlist");
    } catch {
      setWatchError("Couldn't add this card to your watchlist. Try again.");
      toast("Couldn't add to watchlist", "error");
    }
  }

  return (
    <div className="container">
      <PageHead
        eyebrow="Add cards"
        title="Search & add"
        subtitle="Find a card by name, then add a copy you own or put it on your watchlist."
      />

      <form
        className="searchbar"
        onSubmit={(e) => {
          e.preventDefault();
          submitSearch();
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

      {watchError && <p className="alert" style={{ marginBottom: 16 }}>{watchError}</p>}

      {searching && <SkeletonCardGrid />}

      {!searching && results === null && (
        <EmptyState title="Start with a name">
          Type a Pokémon or card name and hit Search. Results show the market price where TCGplayer
          has one.
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
            <TiltCard key={card.id}>
              <div className="tile">
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
                        {card.market_price === null ? "Unpriced" : fmt(card.market_price)}
                      </span>
                      <span className="cost">market</span>
                    </div>
                  </div>
                </div>
                <div className="tile__actions">
                  <button className="btn btn--primary btn--sm" onClick={() => setSelected(card)}>
                    Add
                  </button>
                  <button
                    className="btn btn--sm"
                    onClick={() => watch(card)}
                    disabled={watched.has(card.id)}
                  >
                    {watched.has(card.id) ? "Watching" : "Watch"}
                  </button>
                </div>
              </div>
            </TiltCard>
          ))}
        </div>
      )}

      {selected && (
        <div className="modal-scrim" onClick={() => setSelected(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal__head">
              <div>
                <div className="eyebrow">Add to collection</div>
                <div className="modal__title">{selected.name}</div>
                <div className="tile__set">{selected.set_name}</div>
              </div>
              {selected.image_url && (
                // eslint-disable-next-line @next/next/no-img-element
                <img className="modal__thumb" src={selected.image_url} alt={selected.name} />
              )}
            </div>
            <label className="field">
              <span className="label">What did you pay? (USD)</span>
              <input
                className="input num"
                inputMode="decimal"
                value={cost}
                onChange={(e) => setCost(e.target.value)}
                placeholder="0.00"
                autoFocus
              />
            </label>
            <label className="field">
              <span className="label">Condition</span>
              <select
                className="input"
                value={condition}
                onChange={(e) => setCondition(e.target.value)}
              >
                {CONDITION_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span className="label">Variant</span>
              <select
                className="input"
                value={variant}
                onChange={(e) => setVariant(e.target.value)}
              >
                {VARIANT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            {addError && <p className="alert">{addError}</p>}
            <div className="row" style={{ justifyContent: "flex-end", marginTop: 4 }}>
              <button className="btn btn--ghost" onClick={() => setSelected(null)}>
                Cancel
              </button>
              <button className="btn btn--primary" onClick={add} disabled={saving}>
                {saving ? "Adding…" : "Add to collection"}
              </button>
            </div>
          </div>
        </div>
      )}

      {revealed && (
        <PackReveal
          imageUrl={revealed.image_url}
          name={revealed.name}
          onDone={() => {
            setRevealed(null);
            router.push("/");
          }}
        />
      )}
    </div>
  );
}

// useSearchParams needs a Suspense boundary or the production build fails with
// "Missing Suspense boundary with useSearchParams" — dev renders on demand and
// hides this, so it only shows up in `next build`.
export default function SearchPage() {
  return (
    <Suspense fallback={<SearchPageFallback />}>
      <SearchPageInner />
    </Suspense>
  );
}
