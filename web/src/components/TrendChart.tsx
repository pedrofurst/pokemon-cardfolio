"use client";

import { useEffect, useId, useRef, useState } from "react";

interface TrendChartPoint {
  t: string;
  v: number;
}

interface TrendChartProps {
  points: TrendChartPoint[];
  height?: number;
  accent?: string;
  ariaLabel?: string;
}

const VIEWBOX_WIDTH = 300;
const VERTICAL_PADDING_RATIO = 0.14;
const FALLBACK_PATH_LENGTH = 1000;

function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

function buildLinePath(coordinates: Array<[number, number]>): string {
  return coordinates
    .map(([x, y], index) => `${index === 0 ? "M" : "L"}${x},${y}`)
    .join(" ");
}

export function TrendChart({ points, height = 96, accent, ariaLabel }: TrendChartProps) {
  const gradientId = `trend-gradient-${useId()}`;
  const lineRef = useRef<SVGPathElement | null>(null);
  const [pathLength, setPathLength] = useState(FALLBACK_PATH_LENGTH);
  const [isDrawn, setIsDrawn] = useState(false);

  const strokeColor = accent ?? "var(--brand)";
  const hasEnoughHistory = points.length >= 2;

  const values = points.map((point) => point.v);
  const minValue = hasEnoughHistory ? Math.min(...values) : 0;
  const maxValue = hasEnoughHistory ? Math.max(...values) : 0;
  const valueRange = maxValue - minValue;
  const verticalPadding = height * VERTICAL_PADDING_RATIO;
  const usableHeight = height - verticalPadding * 2;

  const coordinates: Array<[number, number]> = hasEnoughHistory
    ? points.map((point, index) => {
        const x = (index / (points.length - 1)) * VIEWBOX_WIDTH;
        const normalized = valueRange === 0 ? 0.5 : (point.v - minValue) / valueRange;
        const y = verticalPadding + (1 - normalized) * usableHeight;
        return [x, y];
      })
    : [];

  const linePath = buildLinePath(coordinates);
  const lastCoordinate = coordinates[coordinates.length - 1];
  const firstCoordinate = coordinates[0];
  const areaPath =
    linePath && lastCoordinate && firstCoordinate
      ? `${linePath} L${lastCoordinate[0]},${height} L${firstCoordinate[0]},${height} Z`
      : "";

  useEffect(() => {
    if (!hasEnoughHistory || !lineRef.current) {
      return;
    }

    const measuredLength = lineRef.current.getTotalLength();
    setPathLength(measuredLength);

    if (prefersReducedMotion()) {
      setIsDrawn(true);
      return;
    }

    setIsDrawn(false);
    const frame = requestAnimationFrame(() => {
      setIsDrawn(true);
    });

    return () => cancelAnimationFrame(frame);
  }, [hasEnoughHistory, linePath]);

  if (!hasEnoughHistory) {
    return (
      <div className="trend-chart trend-chart--empty" style={{ height }}>
        <svg
          viewBox={`0 0 ${VIEWBOX_WIDTH} ${height}`}
          width="100%"
          height={height}
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <line
            x1={0}
            y1={height / 2}
            x2={VIEWBOX_WIDTH}
            y2={height / 2}
            stroke="var(--line)"
            strokeWidth={1.5}
            strokeDasharray="4 4"
          />
        </svg>
        <p className="trend-chart__caption">Not enough history yet — refresh a few times.</p>
      </div>
    );
  }

  return (
    <div className="trend-chart" style={{ height }}>
      <svg
        viewBox={`0 0 ${VIEWBOX_WIDTH} ${height}`}
        width="100%"
        height={height}
        preserveAspectRatio="none"
        role="img"
        aria-label={ariaLabel ?? "Trend chart"}
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={strokeColor} stopOpacity={0.18} />
            <stop offset="100%" stopColor={strokeColor} stopOpacity={0} />
          </linearGradient>
        </defs>
        <path
          d={areaPath}
          fill={`url(#${gradientId})`}
          stroke="none"
          className="trend-area"
          style={{ opacity: isDrawn ? 1 : 0 }}
        />
        <path
          ref={lineRef}
          d={linePath}
          fill="none"
          stroke={strokeColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          className="trend-line"
          style={{
            strokeDasharray: pathLength,
            strokeDashoffset: isDrawn ? 0 : pathLength,
          }}
        />
        {lastCoordinate && (
          <circle cx={lastCoordinate[0]} cy={lastCoordinate[1]} r={3.5} fill={strokeColor} />
        )}
      </svg>
    </div>
  );
}
