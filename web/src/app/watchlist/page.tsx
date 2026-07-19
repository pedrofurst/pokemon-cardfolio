"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { WatchEntry } from "@/lib/types";

export default function WatchlistPage() {
  const [entries, setEntries] = useState<WatchEntry[]>([]);

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

  return (
    <main style={{ padding: 24 }}>
      <h1>Watchlist</h1>
      <p>
        <Link href="/">Back to collection</Link> · <Link href="/search">Search &amp; add</Link>
      </p>
      {entries.length === 0 && <p>Nothing watched yet — search for a card and hit Watch.</p>}
      <ul>
        {entries.map((entry) => (
          <li key={entry.item.id}>
            {entry.card?.image_url && (
              <img src={entry.card.image_url} alt={entry.card?.name ?? ""} width={60} />
            )}
            {" "}
            <Link href={`/card/${entry.item.card_id}`}>
              {entry.card?.name ?? entry.item.card_id}
            </Link>
            {entry.card?.set_name ? ` — ${entry.card.set_name}` : ""}
            {entry.item.target_price !== null && (
              <> — target ${entry.item.target_price.toFixed(2)}</>
            )}
            <button onClick={() => remove(entry.item.id)} style={{ marginLeft: 12 }}>
              Remove
            </button>
          </li>
        ))}
      </ul>
    </main>
  );
}
