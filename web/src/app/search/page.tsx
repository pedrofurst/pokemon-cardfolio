"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { CardResult } from "@/lib/types";
import { money } from "@/lib/format";
import { EmptyState, PageHead } from "@/components/ui";

export default function SearchPage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<CardResult[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [selected, setSelected] = useState<CardResult | null>(null);
  const [cost, setCost] = useState("");
  const [saving, setSaving] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);
  const [watchError, setWatchError] = useState<string | null>(null);
  const [watched, setWatched] = useState<Set<string>>(new Set());

  async function runSearch() {
    if (!query.trim()) return;
    setSearching(true);
    setWatchError(null);
    try {
      setResults(await api.searchCards(query));
    } catch {
      setResults([]);
    } finally {
      setSearching(false);
    }
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
        condition: "raw",
      });
      router.push("/");
    } catch {
      setAddError("Couldn't add this card. Check the backend is running and try again.");
    } finally {
      setSaving(false);
    }
  }

  async function watch(card: CardResult) {
    setWatchError(null);
    try {
      await api.addWatch({ card, target_price: null });
      setWatched((prev) => new Set(prev).add(card.id));
    } catch {
      setWatchError("Couldn't add this card to your watchlist. Try again.");
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

      {watchError && <p className="alert" style={{ marginBottom: 16 }}>{watchError}</p>}

      {results === null && (
        <EmptyState title="Start with a name">
          Type a Pokémon or card name and hit Search. Results show the market price where TCGplayer
          has one.
        </EmptyState>
      )}

      {results !== null && results.length === 0 && (
        <EmptyState title="No matches">
          Nothing came back for “{query}”. Try a different spelling or a shorter term.
        </EmptyState>
      )}

      {results !== null && results.length > 0 && (
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
              <span className="hint">Condition defaults to raw. You can refine later.</span>
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
    </div>
  );
}
