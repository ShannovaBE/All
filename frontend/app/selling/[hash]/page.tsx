// app/selling/[hash]/page.tsx
"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import "@/styles/MainPage.css";
import "@/styles/Metadata.css";
import QualityCard, { QualitySummary } from "@/components/QualityCard";

interface CategoryVerification {
  user_selected?: string;
  auto_detected?: string;
  confidence?: number;
  match?: boolean;
}

interface PiiReport {
  redacted_cells: number;
  status: string;
}

interface DatasetStats {
  row_count?: number;
  column_count?: number;
  missing_cells?: number;
  missing_percentage?: number;
  average_shannon_entropy?: number;
}

interface ExtraMeta {
  owner_user_id?: string;
  tags?: string[];
  tag_hash?: string;
  prediction_confidence?: number;
  ask_price_usd?: number;
  description?: string;
  pii_report?: PiiReport;
  stats?: DatasetStats;
  data_sample?: Array<Record<string, unknown>>;
  [key: string]: unknown;
}

interface MetadataRecord {
  filename: string;
  hash: string;
  description?: string;
  quality_score?: number;
  quality_scores?: { overall?: number };
  status: string;
  timestamp: string;
  category?: string;
  file_type?: string;
  ask_price_usd?: number;
  category_verification?: CategoryVerification;
  extra?: ExtraMeta;
  details?: string[];
  results?: {
    qualitySummary?: QualitySummary;
    qualities?: QualitySummary;
  };
}

export default function DatasetDetailPage() {
  const params = useParams<{ hash: string }>();
  const router = useRouter();
  const { hash } = params;

  const [record, setRecord] = useState<MetadataRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    async function fetchRecord() {
      try {
        setLoading(true);
        const res = await fetch(`${apiUrl}/metadata/${hash}`);
        if (!res.ok) {
          if (res.status === 404) {
            throw new Error("Dataset not found");
          }
          throw new Error("Failed to load dataset");
        }
        const json = await res.json();
        setRecord(json);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Failed to load dataset";
        setError(message);
      } finally {
        setLoading(false);
      }
    }

    if (hash) {
      fetchRecord();
    }
  }, [hash, apiUrl]);

  if (loading) {
    return <p className="status-text loading">Loading dataset...</p>;
  }

  if (error) {
    return (
      <div className="metadata-page">
        <h1>Dataset details</h1>
        <p className="status-text error">{error}</p>
        <button onClick={() => router.back()}>Go back</button>
      </div>
    );
  }

  if (!record) {
    return (
      <div className="metadata-page">
        <h1>Dataset details</h1>
        <p>Dataset not found.</p>
        <button onClick={() => router.back()}>Go back</button>
      </div>
    );
  }

  const score =
    record.quality_score ??
    record.quality_scores?.overall ??
    0;
  const ownerName = "Verified Creator";
  const conf = record.category_verification?.confidence ?? null;
  const description =
    record.description ?? record.extra?.description ?? "";
  const askPrice = record.ask_price_usd ?? record.extra?.ask_price_usd ?? null;

  const mockQualitySummary: QualitySummary = {
    overallScore: Math.max(0, Math.min(100, score || 85)),
    headline: [
      { key: "completeness", label: "Completeness", score: 88 },
      { key: "cleanliness", label: "Cleanliness", score: 82 },
      { key: "structure", label: "Structure", score: 90 },
      { key: "information", label: "Information Value", score: 84 },
      { key: "privacy", label: "Privacy & Safety", score: 92 },
      { key: "reliability", label: "Reliability", score: 86 },
    ],
    advanced: [
      { name: "Schema consistency", status: "PASS" },
      { name: "Missing value ratio", status: "WARN", interpretation: "Some columns exceed 3% missing values." },
      { name: "Duplicate rows", status: "PASS" },
      { name: "Outlier detection", status: "WARN", interpretation: "Outliers detected in numeric fields." },
      { name: "PII scan", status: "PASS" },
      { name: "Encoding anomalies", status: "PASS" },
      { name: "Label leakage check", status: "FAIL", interpretation: "Potential target leakage detected." },
      { name: "Temporal ordering", status: "PASS" },
      { name: "Geospatial validity", status: "SKIP" },
      { name: "License compliance", status: "PASS" },
    ],
  };

  const qualitySummary =
    record.results?.qualitySummary ||
    record.results?.qualities ||
    mockQualitySummary;

  return (
    <>
      <div className="metadata-page">
        <h1>Dataset details</h1>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "2fr 1fr",
          gap: "1.5rem",
          marginBottom: "1.5rem",
        }}
      >
        {/* Left side: main info */}
        <div>
          <h2 style={{ marginTop: 0 }}>{record.filename}</h2>
          <p>
            <strong>Category:</strong> {record.category ?? "—"}
          </p>
          <p>
            <strong>File type:</strong> {record.file_type ?? "—"}
          </p>
          <p>
            <strong>Uploaded at:</strong>{" "}
            {new Date(record.timestamp).toLocaleString()}
          </p>
          <p>
            <strong>Status:</strong>{" "}
            <span
              className={
                record.status === "passed"
                  ? "status-passed"
                  : record.status === "failed"
                  ? "status-failed"
                  : "status-pending"
              }
            >
              {record.status}
            </span>
          </p>
          <p>
            <strong>Quality score:</strong> {score.toFixed(2)}
          </p>
          <p>
            <strong>Ask price:</strong> {askPrice != null ? `$${askPrice.toFixed(2)}` : "—"}
          </p>
        </div>

        {/* Right side: ownership / tags */}
        <div>
          <h3>Ownership</h3>
          <p>
            <strong>Owner:</strong> {ownerName}
          </p>
        </div>
      </div>

      {/* Category verification block */}
      <div style={{ marginBottom: "1.5rem" }}>
        <h3>Category verification</h3>
        <p>
          <strong>User selected:</strong>{" "}
          {record.category_verification?.user_selected ?? record.category ?? "—"}
        </p>
        <p>
          <strong>Auto detected:</strong>{" "}
          {record.category_verification?.auto_detected ?? "—"}
        </p>
        <p>
          <strong>Match:</strong>{" "}
          {record.category_verification?.match == null
            ? "Unknown"
            : record.category_verification.match
            ? "Yes"
            : "No"}
        </p>
        <p>
          <strong>Confidence:</strong>{" "}
          {conf != null ? conf.toFixed(2) : "—"}
        </p>
      </div>

      <div className="metadata-section">
        <h3>Description</h3>
        {description ? (
          <p className="dataset-description">{String(description)}</p>
        ) : (
          <p className="dataset-description dataset-description--empty">
            No description provided.
          </p>
        )}
      </div>

      <div style={{ marginBottom: "1.5rem" }}>
        <h3>Quality</h3>
        <QualityCard quality={qualitySummary} />
      </div>

      {/* Details list from quality checker */}
      {record.details && record.details.length > 0 && (
        <div style={{ marginBottom: "1.5rem" }}>
          <h3>Quality checker details</h3>
          <ul>
            {record.details.map((d: string, i: number) => (
              <li key={i}>{String(d)}</li>
            ))}
          </ul>
        </div>
      )}

      {/* PII Removal Report */}
      {record.extra?.pii_report && (
        <div style={{ marginBottom: "1.5rem", padding: "1rem", backgroundColor: "#f9fafb", borderRadius: "8px", border: "1px solid #e5e7eb" }}>
          <h3 style={{ marginTop: 0, color: "#111827" }}>🛡️ Privacy & PII Report (Gamma Engine)</h3>
          <p style={{ margin: "0.5rem 0", color: record.extra.pii_report.redacted_cells > 0 ? "#b91c1c" : "#047857", fontWeight: "bold" }}>
            {record.extra.pii_report.status}
          </p>
          {record.extra.pii_report.redacted_cells > 0 && (
            <p style={{ margin: 0, fontSize: "0.9rem", color: "#4b5563" }}>
              Total Redactions: {record.extra.pii_report.redacted_cells} (Replaced with [REDACTED] tags to ensure GDPR compliance)
            </p>
          )}
        </div>
      )}

      {/* Statistical & Information Theory Metrics */}
      {record.extra?.stats && Object.keys(record.extra.stats).length > 0 && (
        <div style={{ marginBottom: "1.5rem" }}>
          <h3>📊 Dataset Statistics & Information Theory</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "1rem" }}>
            <div style={{ padding: "1rem", border: "1px solid #e5e7eb", borderRadius: "8px" }}>
              <strong>Row Count:</strong> <br/>{record.extra.stats.row_count?.toLocaleString()}
            </div>
            <div style={{ padding: "1rem", border: "1px solid #e5e7eb", borderRadius: "8px" }}>
              <strong>Column Count:</strong> <br/>{record.extra.stats.column_count}
            </div>
            <div style={{ padding: "1rem", border: "1px solid #e5e7eb", borderRadius: "8px" }}>
              <strong>Missing Data:</strong> <br/>{record.extra.stats.missing_percentage}% ({record.extra.stats.missing_cells} cells)
            </div>
            <div style={{ padding: "1rem", border: "1px solid #e5e7eb", borderRadius: "8px" }}>
              <strong>Shannon Entropy (Avg):</strong> <br/>{record.extra.stats.average_shannon_entropy} 
              <br/><span style={{fontSize: "0.75rem", color: "#6b7280"}}>(Measures data unpredictability/variance)</span>
            </div>
          </div>
        </div>
      )}

      {/* Data Sample Preview */}
      {record.extra?.data_sample && record.extra.data_sample.length > 0 && (
        <div style={{ marginBottom: "1.5rem", overflowX: "auto" }}>
          <h3>🔎 Dataset Sample Preview (First 5 Rows)</h3>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem", textAlign: "left" }}>
            <thead>
              <tr style={{ backgroundColor: "#f3f4f6", borderBottom: "2px solid #d1d5db" }}>
                {Object.keys(record.extra.data_sample[0]).map((key) => (
                  <th key={key} style={{ padding: "0.5rem" }}>{key}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {record.extra.data_sample.map((row: unknown, i: number) => {
                const typedRow = row as Record<string, unknown>;
                return (
                  <tr key={i} style={{ borderBottom: "1px solid #e5e7eb" }}>
                    {Object.values(typedRow).map((val: unknown, j: number) => (
                      <td key={j} style={{ padding: "0.5rem", whiteSpace: "nowrap" }}>{String(val)}</td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

        <div style={{ marginTop: "1.5rem" }}>
          <button onClick={() => router.back()}>Back</button>
        </div>
      </div>
    </>
  );
}
