"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { CardResult } from "@/lib/types";

export default function SearchPage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<CardResult[]>([]);
  const [selected, setSelected] = useState<CardResult | null>(null);
  const [cost, setCost] = useState("");
  const [addError, setAddError] = useState<string | null>(null);

  async function runSearch() {
    setResults(await api.searchCards(query));
  }

  async function add() {
    if (!selected) return;
    setAddError(null);
    try {
      await api.addHolding({
        card: selected,
        acquisition_cost: Number(cost) || 0,
        quantity: 1,
        condition: "raw",
      });
      setSelected(null);
      setCost("");
      router.push("/");
    } catch {
      setAddError("Couldn't add this card to your collection. Try again.");
    }
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
          {addError && <p style={{ color: "#b91c1c" }}>{addError}</p>}
        </div>
      )}
    </main>
  );
}
