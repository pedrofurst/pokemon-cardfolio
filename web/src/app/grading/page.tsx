"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { GradingResult } from "@/lib/types";

function formatNumber(value: number | null): string {
  return value === null ? "—" : value.toFixed(2);
}

function formatRoiPct(value: number | null): string {
  return value == null ? "—" : `${value.toFixed(1)}%`;
}

function recommendationLabel(recommendation: string): string {
  if (recommendation === "GRADE") return "GRADE";
  if (recommendation === "DONT_GRADE") return "DON'T GRADE";
  return "INSUFFICIENT DATA";
}

function recommendationColor(recommendation: string): string {
  if (recommendation === "GRADE") return "#166534";
  if (recommendation === "DONT_GRADE") return "#b91c1c";
  return "#92400e";
}

function GradingForm() {
  const searchParams = useSearchParams();
  const [cardId, setCardId] = useState(searchParams.get("card_id") ?? "");
  const [rawPrice, setRawPrice] = useState("");
  const [psa10Price, setPsa10Price] = useState("");
  const [psa9Price, setPsa9Price] = useState("");
  const [gradingCost, setGradingCost] = useState("25");
  const [sellingFeesPct, setSellingFeesPct] = useState("13");
  const [probPsa10, setProbPsa10] = useState("0.5");
  const [result, setResult] = useState<GradingResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  function parseOptionalNumber(value: string): number | null {
    const trimmed = value.trim();
    return trimmed === "" ? null : Number(trimmed);
  }

  async function evaluate() {
    setError(null);
    setResult(null);
    try {
      const payload = {
        card_id: cardId.trim() === "" ? null : cardId.trim(),
        raw_price: parseOptionalNumber(rawPrice),
        psa10_price: parseOptionalNumber(psa10Price),
        psa9_price: parseOptionalNumber(psa9Price),
        grading_cost: Number(gradingCost) || 0,
        selling_fees_pct: Number(sellingFeesPct) || 0,
        prob_psa10: Number(probPsa10) || 0,
      };
      setResult(await api.evaluateGrading(payload));
    } catch {
      setError("Couldn't evaluate grading. Try again.");
    }
  }

  return (
    <main style={{ padding: 24 }}>
      <h1>Should I grade it?</h1>
      <div style={{ display: "flex", flexDirection: "column", gap: 8, maxWidth: 320 }}>
        <label>
          Card ID (optional)
          <input value={cardId} onChange={(e) => setCardId(e.target.value)} style={{ display: "block", width: "100%" }} />
        </label>
        <label>
          Raw price (optional — auto-fills from card ID if blank)
          <input value={rawPrice} onChange={(e) => setRawPrice(e.target.value)} style={{ display: "block", width: "100%" }} />
        </label>
        <label>
          PSA 10 price
          <input value={psa10Price} onChange={(e) => setPsa10Price(e.target.value)} style={{ display: "block", width: "100%" }} />
        </label>
        <label>
          PSA 9 price
          <input value={psa9Price} onChange={(e) => setPsa9Price(e.target.value)} style={{ display: "block", width: "100%" }} />
        </label>
        <label>
          Grading cost
          <input value={gradingCost} onChange={(e) => setGradingCost(e.target.value)} style={{ display: "block", width: "100%" }} />
        </label>
        <label>
          Selling fees (%)
          <input value={sellingFeesPct} onChange={(e) => setSellingFeesPct(e.target.value)} style={{ display: "block", width: "100%" }} />
        </label>
        <label>
          Probability of PSA 10
          <input value={probPsa10} onChange={(e) => setProbPsa10(e.target.value)} style={{ display: "block", width: "100%" }} />
        </label>
        <p style={{ fontSize: 12, color: "#6b7280", margin: 0 }}>
          Only applied when both PSA 10 and PSA 9 prices are entered.
        </p>
        <button onClick={evaluate}>Evaluate</button>
      </div>
      {error && <p style={{ color: "#b91c1c" }}>{error}</p>}
      {result && (
        <div style={{ marginTop: 24 }}>
          <span
            style={{
              display: "inline-block",
              padding: "4px 12px",
              borderRadius: 4,
              color: "#fff",
              backgroundColor: recommendationColor(result.recommendation),
              fontWeight: "bold",
            }}
          >
            {recommendationLabel(result.recommendation)}
          </span>
          <p>{result.rationale}</p>
          <ul>
            <li>Raw net: ${formatNumber(result.raw_net)}</li>
            <li>PSA 10 net: ${formatNumber(result.psa10_net)}</li>
            <li>PSA 9 net: ${formatNumber(result.psa9_net)}</li>
            <li>Expected graded net: ${formatNumber(result.expected_graded_net)}</li>
            <li>Uplift: ${formatNumber(result.uplift)}</li>
            <li>ROI: {formatRoiPct(result.roi_pct)}</li>
          </ul>
        </div>
      )}
    </main>
  );
}

export default function GradingPage() {
  return (
    <Suspense fallback={<main style={{ padding: 24 }}>Loading…</main>}>
      <GradingForm />
    </Suspense>
  );
}
