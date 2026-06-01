// app/selling/page.tsx
"use client";

import { useEffect, useState, Suspense } from "react";
import "@/styles/MainPage.css";
import "@/styles/Metadata.css";
import "@/styles/Marketplace.css";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

interface CategoryVerification {
  user_selected?: string;
  auto_detected?: string;
  confidence?: number;
  match?: boolean;
}

interface ExtraMeta {
  prediction_confidence?: number;
  ask_price_usd?: number;
}

interface MetadataRecord {
  filename: string;
  hash: string;
  quality_score?: number;
  quality_scores?: { overall?: number };
  status: string;
  timestamp: string;
  category?: string;
  file_type?: string;
  ask_price_usd?: number;
  category_verification?: CategoryVerification;
  extra?: ExtraMeta;
}

const CATEGORIES = [
  "medical",
  "finance",
  "retail",
  "text",
  "images",
  "geospatial",
  "general",
];

const FILE_TYPES = ["all", "csv", "json", "txt", "png", "jpg", "other"];

// confidence levels (for category detection / verification)
const CONFIDENCE_MIN = 0;
const CONFIDENCE_MAX = 1;
const QUALITY_MIN = 0;
const QUALITY_MAX = 100;

export default function SellingPage() {
  return (
    <Suspense fallback={<p>Loading marketplace...</p>}>
      <InternalSellingPage />
    </Suspense>
  );
}

function InternalSellingPage() {
  const searchParams = useSearchParams();
  const [data, setData] = useState<MetadataRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [downloadingHash, setDownloadingHash] = useState<string | null>(null);

  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [selectedFileType, setSelectedFileType] = useState<string>("all");
  const [confidenceMin, setConfidenceMin] = useState<string>("");
  const [confidenceMax, setConfidenceMax] = useState<string>("");
  const [qualityMin, setQualityMin] = useState<string>("");
  const [qualityMax, setQualityMax] = useState<string>("");

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  function getAskPrice(rec: MetadataRecord): number | null {
    const value = rec.ask_price_usd ?? rec.extra?.ask_price_usd ?? null;
    return typeof value === "number" ? value : null;
  }

  function formatAskPrice(price: number | null): string {
    if (price == null) return "—";
    return `$${price.toFixed(2)}`;
  }

  async function handleDownload(fileHash: string) {
    setDownloadError(null);
    setDownloadingHash(fileHash);
    try {
      const res = await fetch(`${apiUrl}/datasets/${fileHash}/download`);
      const data = (await res.json().catch(() => ({}))) as {
        url?: string;
        expires_in?: number;
        detail?: string;
      };
      if (!res.ok) {
        throw new Error(data.detail || "Failed to generate download link");
      }
      if (!data.url) {
        throw new Error("Download link missing");
      }
      window.location.href = data.url;
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to download dataset";
      setDownloadError(message);
    } finally {
      setDownloadingHash(null);
    }
  }

  useEffect(() => {
    async function fetchMetadata() {
      try {
        const res = await fetch(`${apiUrl}/metadata`);
        if (!res.ok) throw new Error("Failed to fetch metadata");
        const json = await res.json();
        setData(json.items || []);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Failed to fetch metadata";
        setError(message);
      } finally {
        setLoading(false);
      }
    }
    fetchMetadata();
  }, [apiUrl]);

  if (loading) return <p className="status-text loading">Loading datasets...</p>;
  if (error) return <p className="status-text error">{error}</p>;

  // helper: get a usable confidence value from record
  function getConfidence(rec: MetadataRecord): number | null {
    // prefer category_verification.confidence
    if (rec.category_verification?.confidence != null) {
      return rec.category_verification.confidence;
    }
    // fallback: extra.prediction_confidence if present
    if (rec.extra?.prediction_confidence != null) {
      return rec.extra.prediction_confidence;
    }
    return null;
  }

  const filtered = data.filter((rec) => {
    // category filter
    if (selectedCategory !== "all") {
      if ((rec.category || "general") !== selectedCategory) return false;
    }

    // file type filter
    if (selectedFileType !== "all") {
      const ext = (rec.file_type || "other").toLowerCase();
      if (ext !== selectedFileType) return false;
    }

    const conf = getConfidence(rec);
    const minConf = confidenceMin.trim() === "" ? null : Number(confidenceMin);
    const maxConf = confidenceMax.trim() === "" ? null : Number(confidenceMax);
    const invalidConf =
      minConf != null &&
      maxConf != null &&
      !Number.isNaN(minConf) &&
      !Number.isNaN(maxConf) &&
      minConf > maxConf;
    if (!invalidConf && (minConf != null || maxConf != null)) {
      if (conf == null) return false;
      if (minConf != null && conf < minConf) return false;
      if (maxConf != null && conf > maxConf) return false;
    }

    const score =
      rec.quality_score ??
      rec.quality_scores?.overall ??
      null;
    const minQual = qualityMin.trim() === "" ? null : Number(qualityMin);
    const maxQual = qualityMax.trim() === "" ? null : Number(qualityMax);
    const invalidQual =
      minQual != null &&
      maxQual != null &&
      !Number.isNaN(minQual) &&
      !Number.isNaN(maxQual) &&
      minQual > maxQual;
    if (!invalidQual && (minQual != null || maxQual != null)) {
      if (score == null) return false;
      if (minQual != null && score < minQual) return false;
      if (maxQual != null && score > maxQual) return false;
    }

    return true;
  });

  const sortKey = (searchParams.get("sort") || "").toLowerCase();
  const sorted = [...filtered].sort((a, b) => {
    const aTime = new Date(a.timestamp).getTime();
    const bTime = new Date(b.timestamp).getTime();

    const aScore = a.quality_score ?? a.quality_scores?.overall ?? 0;
    const bScore = b.quality_score ?? b.quality_scores?.overall ?? 0;

    if (sortKey === "newest") {
      return bTime - aTime;
    }

    if (sortKey === "trending") {
      if (bScore !== aScore) return bScore - aScore;
      return bTime - aTime;
    }

    return 0;
  });

  return (
    <>
      <div className="metadata-page">
        <h1>Shannova Data Marketplace</h1>
        {sortKey === "trending" && (
          <p className="marketplace-sort-note">
            Trending datasets (sorted by quality score)
          </p>
        )}
        {sortKey === "newest" && (
          <p className="marketplace-sort-note">
            Newest datasets (sorted by most recent)
          </p>
        )}

      {/* Top-level category boxes */}
      <div className="category-grid">
        <button
          onClick={() => setSelectedCategory("all")}
          className={`category-box ${selectedCategory === "all" ? "selected" : ""}`}
        >
          All categories
        </button>

        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={`category-box ${selectedCategory === cat ? "selected" : ""}`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Sub-bin + confidence filters */}
      <div className="marketplace-filter-row">
        <div className="marketplace-filter-block">
          <label className="marketplace-filter-label">File type</label>
          <div className="filter-pills" role="tablist" aria-label="File type">
            {FILE_TYPES.map((t) => {
              const label = t === "all" ? "All" : t.toUpperCase();
              const isActive = selectedFileType === t;
              return (
                <button
                  key={t}
                  type="button"
                  className={`filter-pill ${isActive ? "selected" : ""}`}
                  onClick={() => setSelectedFileType(t)}
                  aria-pressed={isActive}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <div className="filter-range-grid">
        <div className="marketplace-filter-block">
          <label className="marketplace-filter-label">Confidence range</label>
          <div className="filter-range">
            <input
              type="number"
              min={CONFIDENCE_MIN}
              max={CONFIDENCE_MAX}
              step="0.01"
              placeholder="0.00"
              value={confidenceMin}
              onChange={(e) => setConfidenceMin(e.target.value)}
              onBlur={(e) => {
                const value = e.target.value.trim();
                if (value === "") return;
                const num = Number(value);
                if (Number.isNaN(num)) return;
                const clamped = Math.min(CONFIDENCE_MAX, Math.max(CONFIDENCE_MIN, num));
                setConfidenceMin(clamped.toFixed(2));
              }}
              className="filter-range-input"
              aria-label="Confidence minimum"
            />
            <span className="filter-range-sep">–</span>
            <input
              type="number"
              min={CONFIDENCE_MIN}
              max={CONFIDENCE_MAX}
              step="0.01"
              placeholder="1.00"
              value={confidenceMax}
              onChange={(e) => setConfidenceMax(e.target.value)}
              onBlur={(e) => {
                const value = e.target.value.trim();
                if (value === "") return;
                const num = Number(value);
                if (Number.isNaN(num)) return;
                const clamped = Math.min(CONFIDENCE_MAX, Math.max(CONFIDENCE_MIN, num));
                setConfidenceMax(clamped.toFixed(2));
              }}
              className="filter-range-input"
              aria-label="Confidence maximum"
            />
            <button
              type="button"
              className="filter-range-clear"
              onClick={() => {
                setConfidenceMin("");
                setConfidenceMax("");
              }}
            >
              Clear
            </button>
          </div>
          {confidenceMin !== "" &&
            confidenceMax !== "" &&
            Number(confidenceMin) > Number(confidenceMax) && (
              <p className="filter-range-warning">
                Min must be less than or equal to Max.
              </p>
            )}
        </div>

        <div className="marketplace-filter-block">
          <label className="marketplace-filter-label">Quality range</label>
          <div className="filter-range">
            <input
              type="number"
              min={QUALITY_MIN}
              max={QUALITY_MAX}
              step="0.01"
              placeholder="0.00"
              value={qualityMin}
              onChange={(e) => setQualityMin(e.target.value)}
              onBlur={(e) => {
                const value = e.target.value.trim();
                if (value === "") return;
                const num = Number(value);
                if (Number.isNaN(num)) return;
                const clamped = Math.min(QUALITY_MAX, Math.max(QUALITY_MIN, num));
                setQualityMin(clamped.toFixed(2));
              }}
              className="filter-range-input"
              aria-label="Quality minimum"
            />
            <span className="filter-range-sep">–</span>
            <input
              type="number"
              min={QUALITY_MIN}
              max={QUALITY_MAX}
              step="0.01"
              placeholder="100.00"
              value={qualityMax}
              onChange={(e) => setQualityMax(e.target.value)}
              onBlur={(e) => {
                const value = e.target.value.trim();
                if (value === "") return;
                const num = Number(value);
                if (Number.isNaN(num)) return;
                const clamped = Math.min(QUALITY_MAX, Math.max(QUALITY_MIN, num));
                setQualityMax(clamped.toFixed(2));
              }}
              className="filter-range-input"
              aria-label="Quality maximum"
            />
            <button
              type="button"
              className="filter-range-clear"
              onClick={() => {
                setQualityMin("");
                setQualityMax("");
              }}
            >
              Clear
            </button>
          </div>
          {qualityMin !== "" &&
            qualityMax !== "" &&
            Number(qualityMin) > Number(qualityMax) && (
              <p className="filter-range-warning">
                Min must be less than or equal to Max.
              </p>
            )}
        </div>
      </div>

      <p className="marketplace-summary">
        Showing {sorted.length} of {data.length} datasets
        {selectedCategory !== "all" && ` in "${selectedCategory}"`}
      </p>

      {downloadError && <p className="status-text error">{downloadError}</p>}

      {sorted.length === 0 ? (
        <p>No datasets found for this selection yet.</p>
      ) : (
        <table className="metadata-table">
          <thead>
            <tr>
              <th>Filename</th>
              <th>Category</th>
              <th>Type</th>
              <th>Quality</th>
              <th>Price</th>
              <th>Confidence</th>
              <th>Status</th>
              <th>Timestamp</th>
              <th>Download</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((rec) => {
              const score =
                rec.quality_score ??
                rec.quality_scores?.overall ??
                0;

              const conf = getConfidence(rec);

              return (
                <tr key={rec.hash}>
                  <td><Link href={`/selling/${rec.hash}`}>
                      {rec.filename}
                    </Link>
                  </td>
                  <td>{rec.category ?? "—"}</td>
                  <td>{rec.file_type ?? "—"}</td>
                  <td>{score.toFixed(2)}</td>
                  <td>{formatAskPrice(getAskPrice(rec))}</td>
                  <td>{conf != null ? conf.toFixed(2) : "—"}</td>
                  <td
                    className={
                      rec.status === "passed"
                        ? "status-passed"
                        : rec.status === "failed"
                        ? "status-failed"
                        : "status-pending"
                    }
                  >
                    {rec.status}
                  </td>
                  <td>{new Date(rec.timestamp).toLocaleString()}</td>
                  <td>
                    <button
                      type="button"
                      className="button-secondary"
                      onClick={() => handleDownload(rec.hash)}
                      disabled={downloadingHash === rec.hash}
                    >
                      {downloadingHash === rec.hash ? "Preparing..." : "Download"}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
      </div>
    </>
  );
}
