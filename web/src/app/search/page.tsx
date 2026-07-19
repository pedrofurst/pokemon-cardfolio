"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { CardResult } from "@/lib/types";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<CardResult[]>([]);
  const [selected, setSelected] = useState<CardResult | null>(null);
  const [cost, setCost] = useState("");

  async function runSearch() {
    setResults(await api.searchCards(query));
  }

  async function add() {
    if (!selected) return;
    await api.addHolding({
      card: selected,
      acquisition_cost: Number(cost) || 0,
      quantity: 1,
      condition: "raw",
    });
    setSelected(null);
    setCost("");
  }

  return (
    <main style={{ padding: 24 }}>
      <h1>Search &amp; add</h1>
      <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Charizard" />
      <button onClick={runSearch}>Search</button>
      <ul>
        {results.map((card) => (
          <li key={card.id}>
            <img src={card.image_url} alt={card.name} width={80} />
            {card.name} — {card.set_name} — ${card.market_price ?? "?"}
            <button onClick={() => setSelected(card)}>Add</button>
          </li>
        ))}
      </ul>
      {selected && (
        <div>
          <h2>Add {selected.name}</h2>
          <input value={cost} onChange={(e) => setCost(e.target.value)} placeholder="Acquisition cost (USD)" />
          <button onClick={add}>Save</button>
        </div>
      )}
    </main>
  );
}
