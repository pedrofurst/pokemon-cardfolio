"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { WatchEntry } from "@/lib/types";
import { money } from "@/lib/format";
import { EmptyState, PageHead } from "@/components/ui";

export default function WatchlistPage() {
  const [entries, setEntries] = useState<WatchEntry[] | null>(null);

  useEffect(() => {
    async function load() {
      setEntries(await api.listWatchlist());
    }
    load();
  }, []);

  async function remove(id: string) {
    await api.removeWatch(id);
    setEntries(await api.listWatchlist());
  }

  const list = entries ?? [];

  return (
    <div className="container">
      <PageHead
        eyebrow="Tracking"
        title="Watchlist"
        subtitle="Cards you don't own yet. Set a target price and they'll surface in Opportunities when they hit it."
        actions={
          <Link href="/search" className="btn">
            Add from search
          </Link>
        }
      />

      {entries !== null && list.length === 0 ? (
        <EmptyState
          title="Nothing watched yet"
          action={
            <Link href="/search" className="btn btn--primary">
              Search for a card
            </Link>
          }
        >
          Find a card and hit Watch to track its price without owning it.
        </EmptyState>
      ) : (
        <div className="card-grid">
          {list.map((entry) => (
            <div className="tile tile--hoverable" key={entry.item.id}>
              <Link href={`/card/${entry.item.card_id}`} className="tile__art">
                {entry.card?.image_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={entry.card.image_url} alt={entry.card?.name ?? "Card"} />
                ) : (
                  <span className="tile__art--empty">No image</span>
                )}
              </Link>
              <div className="tile__body">
                <div>
                  <div className="tile__name">{entry.card?.name ?? entry.item.card_id}</div>
                  <div className="tile__set">{entry.card?.set_name || "—"}</div>
                </div>
                <div className="tile__foot">
                  {entry.item.target_price !== null ? (
                    <span className="badge badge--gold">target {money(entry.item.target_price)}</span>
                  ) : (
                    <span className="badge">no target</span>
                  )}
                </div>
              </div>
              <div className="tile__actions">
                <button className="btn btn--sm btn--danger" onClick={() => remove(entry.item.id)}>
                  Remove
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
