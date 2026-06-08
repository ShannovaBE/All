// components/QualityCard.tsx
"use client";

import { useMemo, useState } from "react";
import "@/styles/Marketplace.css";

export type HeadlineQuality = {
  key: string;
  label: string;
  score: number;
};

export type AdvancedCheck = {
  name: string;
  status: "PASS" | "WARN" | "FAIL" | "SKIP" | "NA";
  interpretation?: string;
};

export type QualitySummary = {
  overallScore: number;
  headline: HeadlineQuality[];
  advanced?: AdvancedCheck[];
};

export default function QualityCard({ quality }: { quality: QualitySummary }) {
  const safeOverall = Math.max(0, Math.min(100, quality.overallScore));
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"ALL" | "PASS" | "WARN" | "FAIL">(
    "ALL"
  );
  const [showAll, setShowAll] = useState(false);

  const filteredAdvanced = useMemo(() => {
    const advancedList = quality.advanced ?? [];
    const term = search.trim().toLowerCase();
    return advancedList.filter((item) => {
      const matchesSearch =
        term.length === 0 || item.name.toLowerCase().includes(term);
      const matchesStatus =
        statusFilter === "ALL" || item.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [quality.advanced, search, statusFilter]);

  const visibleAdvanced = showAll ? filteredAdvanced : filteredAdvanced.slice(0, 25);
  const hasMore = filteredAdvanced.length > 25;

  return (
    <section className="quality-card">
      <div className="quality-card__header">
        <div className="quality-card__score">
          <span className="quality-card__score-value">{safeOverall}</span>
          <span className="quality-card__score-label">Overall Score</span>
        </div>
        <div className="quality-card__meta">
          <h3>Quality Summary</h3>
          <p>Snapshot across core dataset dimensions.</p>
        </div>
      </div>

      <div className="quality-card__grid">
        {quality.headline.map((item) => {
          const value = Math.max(0, Math.min(100, item.score));
          return (
            <div className="quality-card__item" key={item.key}>
              <div className="quality-card__item-row">
                <span className="quality-card__item-label">{item.label}</span>
                <span className="quality-card__item-score">{value}</span>
              </div>
              <div className="quality-card__bar">
                <div
                  className="quality-card__bar-fill"
                  style={{ width: `${value}%` }}
                  aria-hidden="true"
                />
              </div>
            </div>
          );
        })}
      </div>

      <div className="quality-card__advanced">
        <button
          type="button"
          className="quality-card__advanced-toggle"
          onClick={() => setAdvancedOpen((v) => !v)}
          aria-expanded={advancedOpen}
        >
          <span>Advanced checks</span>
          <span className="quality-card__chevron">
            {advancedOpen ? "▾" : "▸"}
          </span>
        </button>

        {advancedOpen && (
          <div className="quality-card__advanced-panel">
            <div className="quality-card__filters">
              <input
                className="quality-card__search"
                type="text"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setShowAll(false);
                }}
                placeholder="Search checks"
                aria-label="Search advanced checks"
              />

              <div className="quality-card__status-filters">
                {(["ALL", "PASS", "WARN", "FAIL"] as const).map((status) => (
                  <button
                    key={status}
                    type="button"
                    className={
                      "quality-card__status-button" +
                      (statusFilter === status ? " is-active" : "")
                    }
                    onClick={() => {
                      setStatusFilter(status);
                      setShowAll(false);
                    }}
                  >
                    {status}
                  </button>
                ))}
              </div>
            </div>

            {filteredAdvanced.length === 0 ? (
              <p className="quality-card__advanced-placeholder">
                No advanced checks available.
              </p>
            ) : (
              <div className="quality-card__advanced-list">
                {visibleAdvanced.map((item) => (
                  <div className="quality-card__advanced-row" key={item.name}>
                    <div className="quality-card__advanced-main">
                      <span className="quality-card__advanced-name">
                        {item.name}
                      </span>
                      <span
                        className={
                          "quality-card__badge quality-card__badge--" +
                          item.status.toLowerCase()
                        }
                      >
                        {item.status}
                      </span>
                    </div>
                    {item.interpretation && (
                      <div className="quality-card__advanced-note">
                        {item.interpretation}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {hasMore && !showAll && (
              <button
                type="button"
                className="quality-card__show-more"
                onClick={() => setShowAll(true)}
              >
                Show more
              </button>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
