// app/history/page.tsx
"use client";

import { useEffect, useState } from "react";
import "@/styles/MainPage.css";
import "@/styles/Metadata.css";
import "@/styles/Marketplace.css";
import Link from "next/link";

interface CategoryVerification {
  user_selected?: string;
  auto_detected?: string;
  confidence?: number;
  match?: boolean;
}

interface ExtraMeta {
  owner_user_id?: string;
  tags?: string[];
  tag_hash?: string;
  prediction_confidence?: number;
  ask_price_usd?: number;
}

interface MetadataRecord {
  filename: string;
  hash: string;
  description?: string;
  quality_score?: number;
  quality_scores?: { overall?: number };
  status: string;
  timestamp: string;
  created_at?: string;
  size_bytes?: number;
  bytes?: number;
  results?: { quality_score?: number };
  category?: string;
  file_type?: string;
  ask_price_usd?: number;
  category_verification?: CategoryVerification;
  extra?: ExtraMeta;
}

interface PublicUser {
  id: string;
  username: string;
  email: string;
}

export default function HistoryPage() {
  const [user, setUser] = useState<PublicUser | null>(null);
  const [data, setData] = useState<MetadataRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [sortKey, setSortKey] = useState<string>("date_desc");
  const [selectedRecord, setSelectedRecord] = useState<MetadataRecord | null>(null);
  const [isEditingDesc, setIsEditingDesc] = useState(false);
  const [descDraft, setDescDraft] = useState("");
  const [descError, setDescError] = useState<string | null>(null);
  const [descSaving, setDescSaving] = useState(false);
  const [descSuccess, setDescSuccess] = useState<string | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteSaving, setDeleteSaving] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleteSuccess, setDeleteSuccess] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const BIN_CATEGORIES = [
    "medical",
    "finance",
    "retail",
    "text",
    "images",
    "geospatial",
    "general",
  ];

  function getErrorMessage(error: unknown, fallback: string) {
    if (error instanceof Error) {
      return error.message || fallback;
    }
    if (typeof error === "string" && error.trim().length > 0) {
      return error;
    }
    return fallback;
  }

  function getAskPrice(rec: MetadataRecord): number | null {
    const value = rec.ask_price_usd ?? rec.extra?.ask_price_usd ?? null;
    return typeof value === "number" ? value : null;
  }

  function formatAskPrice(price: number | null): string {
    if (price == null) return "—";
    return `$${price.toFixed(2)}`;
  }

  // 1️⃣ Load user from localStorage
  useEffect(() => {
    if (typeof window === "undefined") return;

    const raw =
      localStorage.getItem("shannova_user") ||
      localStorage.getItem("shanova_user"); // legacy typo just in case

    if (!raw) {
      setUser(null);
      setLoading(false);
      return;
    }

    try {
      const parsed = JSON.parse(raw) as PublicUser;
      setUser(parsed);
    } catch {
      setUser(null);
    }
  }, []);

  useEffect(() => {
    if (!descSuccess) return;
    const timer = window.setTimeout(() => setDescSuccess(null), 1800);
    return () => window.clearTimeout(timer);
  }, [descSuccess]);

  useEffect(() => {
    if (!deleteSuccess) return;
    const timer = window.setTimeout(() => setDeleteSuccess(null), 2000);
    return () => window.clearTimeout(timer);
  }, [deleteSuccess]);

  // 2️⃣ Once we know the user, fetch their datasets
useEffect(() => {
  if (!user) return; // either not logged in or still loading

  async function fetchHistory(userId: string) {
    try {
      setLoading(true);
      const res = await fetch(
        `${apiUrl}/metadata?owner_id=${encodeURIComponent(userId)}`
      );
      if (!res.ok) throw new Error("Failed to fetch history");
      const json = await res.json();
      setData(json.items || []);
    } catch (err: unknown) {
      setError(getErrorMessage(err, "Failed to load history"));
    } finally {
      setLoading(false);
    }
  }

  fetchHistory(user.id);
}, [user, apiUrl]);

  // 3️⃣ Render states
  if (!user && !loading) {
    return (
      <div className="metadata-page">
        <h1>Your upload history</h1>
        <p>You need to be logged in to see your upload history.</p>
        <p>
          <a href="/login">Go to login</a>
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <p className="status-text loading">Loading your datasets...</p>
    );
  }

  if (error) {
    return <p className="status-text error">{error}</p>;
  }

  const uniqueCategories = Array.from(
    new Set(
      data.map((rec) => (rec.category || "general").toLowerCase())
    )
  );

  const categoryOptions =
    uniqueCategories.length >= 8
      ? uniqueCategories.slice(0, 8)
      : BIN_CATEGORIES;

  const filtered = data.filter((rec) => {
    if (selectedCategory === "all") return true;
    return (rec.category || "general") === selectedCategory;
  });

  const sorted = filtered
    .map((rec, idx) => ({ rec, idx }))
    .sort((a, b) => {
      const getDateValue = (r: MetadataRecord) => {
        const raw = r.created_at || r.timestamp || "";
        const value = raw ? Date.parse(raw) : 0;
        return Number.isNaN(value) ? 0 : value;
      };
      const getQualityValue = (r: MetadataRecord) => {
        const value = r.quality_score ?? r.results?.quality_score ?? -1;
        return typeof value === "number" ? value : -1;
      };
      const getSizeValue = (r: MetadataRecord) => {
        const value = r.size_bytes ?? r.bytes ?? -1;
        return typeof value === "number" ? value : -1;
      };

      let diff = 0;
      switch (sortKey) {
        case "date_asc":
          diff = getDateValue(a.rec) - getDateValue(b.rec);
          break;
        case "date_desc":
          diff = getDateValue(b.rec) - getDateValue(a.rec);
          break;
        case "quality_asc":
          diff = getQualityValue(a.rec) - getQualityValue(b.rec);
          break;
        case "quality_desc":
          diff = getQualityValue(b.rec) - getQualityValue(a.rec);
          break;
        case "size_asc":
          diff = getSizeValue(a.rec) - getSizeValue(b.rec);
          break;
        case "size_desc":
          diff = getSizeValue(b.rec) - getSizeValue(a.rec);
          break;
        default:
          diff = 0;
      }

      if (diff !== 0) return diff;
      return a.idx - b.idx;
    })
    .map(({ rec }) => rec);


  const descriptionLimit = 1000;
  const selectedDescription = (selectedRecord?.description ?? "").trim();
  const draftTrimmed = descDraft.trim();
  const isDescUnchanged = draftTrimmed === selectedDescription;
  const isOwner = Boolean(
    selectedRecord?.extra?.owner_user_id && user?.id === selectedRecord.extra.owner_user_id
  );

  const handleEditDescription = () => {
    if (!selectedRecord) return;
    setIsEditingDesc(true);
    setDescError(null);
    setDescSuccess(null);
    setDescDraft(selectedRecord.description ?? "");
  };

  const handleCancelDescription = () => {
    setIsEditingDesc(false);
    setDescError(null);
    setDescSuccess(null);
    setDescDraft(selectedRecord?.description ?? "");
  };

  const handleOpenDelete = () => {
    if (!selectedRecord) return;
    setDeleteError(null);
    setDeleteOpen(true);
  };

  const handleCloseDelete = () => {
    if (deleteSaving) return;
    setDeleteOpen(false);
    setDeleteError(null);
  };

  const handleConfirmDelete = async () => {
    if (!selectedRecord || !user?.id || deleteSaving) return;

    try {
      setDeleteSaving(true);
      setDeleteError(null);
      const res = await fetch(`${apiUrl}/datasets/${selectedRecord.hash}`, {
        method: "DELETE",
        headers: {
          "X-User-Id": user.id,
        },
      });
      if (res.status === 403) {
        setDeleteError("You don't have permission to delete this dataset.");
        return;
      }
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to delete dataset");
      }
      setData((prev) => prev.filter((rec) => rec.hash !== selectedRecord.hash));
      setSelectedRecord(null);
      setDeleteOpen(false);
      setDeleteSuccess("Dataset deleted");
    } catch (err: unknown) {
      setDeleteError(getErrorMessage(err, "Failed to delete dataset"));
    } finally {
      setDeleteSaving(false);
    }
  };

  const handleSaveDescription = async () => {
    if (!selectedRecord || descSaving) return;
    const trimmed = descDraft.trim();
    const current = (selectedRecord.description ?? "").trim();
    if (trimmed === current) {
      return;
    }
    if (trimmed.length > descriptionLimit) {
      setDescError("Description is too long.");
      return;
    }

    let userId: string | null = null;
    let username: string | null = null;
    if (typeof window !== "undefined") {
      const raw =
        localStorage.getItem("shannova_user") ||
        localStorage.getItem("shanova_user");
      if (raw) {
        try {
          const parsed = JSON.parse(raw) as { id?: string; username?: string };
          userId = parsed.id || null;
          username = parsed.username || null;
        } catch {
          // ignore
        }
      }
    }

    try {
      setDescSaving(true);
      setDescError(null);
      setDescSuccess(null);
      const res = await fetch(`${apiUrl}/datasets/${selectedRecord.hash}/description`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          ...(userId ? { "X-User-Id": userId } : {}),
          ...(username ? { "X-Username": username } : {}),
        },
        body: JSON.stringify({ description: trimmed }),
      });
      if (res.status === 403) {
        setDescError("You don't have permission to edit this dataset");
        return;
      }
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to update description");
      }
      const updated = { ...selectedRecord, description: trimmed };
      setSelectedRecord(updated);
      setData((prev) => prev.map((r) => (r.hash == updated.hash ? updated : r)));
      setIsEditingDesc(false);
      setDescSuccess("Description updated");
    } catch (err: unknown) {
      setDescError(getErrorMessage(err, "Failed to update description"));
    } finally {
      setDescSaving(false);
    }
  };

  const sortLabelMap: Record<string, string> = {
    date_desc: "Date (Newest → Oldest)",
    date_asc: "Date (Oldest → Newest)",
    quality_desc: "Quality (High → Low)",
    quality_asc: "Quality (Low → High)",
    size_desc: "Size (Large → Small)",
    size_asc: "Size (Small → Large)",
  };

  return (
    <div className="metadata-page">
      <h1>{user?.username}&apos;s upload history</h1>
      <p style={{ marginBottom: "1rem" }}>
        Showing {filtered.length} of {data.length} dataset
        {data.length === 1 ? "" : "s"} uploaded by you.
      </p>

      <div className="category-grid">
        <button
          onClick={() => setSelectedCategory("all")}
          className={`category-box ${selectedCategory === "all" ? "selected" : ""}`}
        >
          All
        </button>

        {categoryOptions.map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={`category-box ${selectedCategory === cat ? "selected" : ""}`}
          >
            {cat}
          </button>
        ))}
      </div>

      <div className="marketplace-filter-row">
        <div className="marketplace-filter-block">
          <label className="marketplace-filter-label">Sort by</label>
          <div className="filter-pills" role="tablist" aria-label="Sort by">
            <button
              type="button"
              className={`filter-pill ${sortKey === "date_desc" ? "selected" : ""}`}
              onClick={() => setSortKey("date_desc")}
              aria-pressed={sortKey === "date_desc"}
            >
              Date: Newest
            </button>
            <button
              type="button"
              className={`filter-pill ${sortKey === "date_asc" ? "selected" : ""}`}
              onClick={() => setSortKey("date_asc")}
              aria-pressed={sortKey === "date_asc"}
            >
              Date: Oldest
            </button>
            <button
              type="button"
              className={`filter-pill ${sortKey === "quality_desc" ? "selected" : ""}`}
              onClick={() => setSortKey("quality_desc")}
              aria-pressed={sortKey === "quality_desc"}
            >
              Quality: High
            </button>
            <button
              type="button"
              className={`filter-pill ${sortKey === "quality_asc" ? "selected" : ""}`}
              onClick={() => setSortKey("quality_asc")}
              aria-pressed={sortKey === "quality_asc"}
            >
              Quality: Low
            </button>
            <button
              type="button"
              className={`filter-pill ${sortKey === "size_desc" ? "selected" : ""}`}
              onClick={() => setSortKey("size_desc")}
              aria-pressed={sortKey === "size_desc"}
            >
              Size: Large
            </button>
            <button
              type="button"
              className={`filter-pill ${sortKey === "size_asc" ? "selected" : ""}`}
              onClick={() => setSortKey("size_asc")}
              aria-pressed={sortKey === "size_asc"}
            >
              Size: Small
            </button>
          </div>
        </div>
        <p className="marketplace-summary">
          Sorted by: {sortLabelMap[sortKey]}
        </p>
      </div>

      {sorted.length === 0 ? (
        <p>You haven&apos;t uploaded any datasets yet.</p>
      ) : (
        <table className="metadata-table">
          <thead>
            <tr>
              <th>Filename</th>
              <th>Category</th>
              <th>Type</th>
              <th>Quality</th>
              <th>Price</th>
              <th>Status</th>
              <th>Tags</th>
              <th>Uploaded at</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((rec) => {
              const score =
                rec.quality_score ??
                rec.quality_scores?.overall ??
                0;

              const tags = rec.extra?.tags ?? [];

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
                  <td>{tags.length ? tags.join(", ") : "—"}</td>
                  <td>{new Date(rec.timestamp).toLocaleString()}</td>
                  <td>
                    <button
                      type="button"
                      className="details-button"
                      onClick={() => {
                        const nextSelected =
                          selectedRecord?.hash === rec.hash ? null : rec;
                        setSelectedRecord(nextSelected);
                        setIsEditingDesc(false);
                        setDescError(null);
                        setDescSuccess(null);
                        setDescDraft(nextSelected?.description ?? "");
                      }}
                    >
                      {selectedRecord?.hash === rec.hash ? "Hide" : "Details"}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}


      {selectedRecord && (
        <div className="metadata-section">
          <h3>Dataset details</h3>
          <div className="details-grid">
            <div>
              <strong>Name:</strong> {selectedRecord.filename}
            </div>
            <div>
              <strong>Category:</strong> {selectedRecord.category ?? "-"}
            </div>
            <div>
              <strong>Type:</strong> {selectedRecord.file_type ?? "-"}
            </div>
            <div>
              <strong>Status:</strong> {selectedRecord.status}
            </div>
            <div>
              <strong>Ask price:</strong> {formatAskPrice(getAskPrice(selectedRecord))}
            </div>
          </div>
          <div className="description-header">
            <h4>Description</h4>
            <div className="description-actions">
              <button
                type="button"
                className="details-button"
                onClick={handleEditDescription}
              >
                Edit
              </button>
              {isOwner && (
                <button
                  type="button"
                  className="details-button danger"
                  onClick={handleOpenDelete}
                >
                  Delete
                </button>
              )}
            </div>
          </div>
          {descSuccess && (
            <p className="description-success">{descSuccess}</p>
          )}
          {deleteSuccess && (
            <p className="description-success">{deleteSuccess}</p>
          )}

          {isEditingDesc ? (
            <div className="description-editor">
              <textarea
                className="description-textarea"
                value={descDraft}
                maxLength={descriptionLimit}
                onChange={(e) => setDescDraft(e.target.value)}
                rows={4}
                aria-busy={descSaving}
              />
              <div className="description-editor-row">
                <span className="description-counter">
                  {descDraft.length}/{descriptionLimit}
                </span>
                <div className="description-actions">
                  <button
                    type="button"
                    className="details-button"
                    onClick={handleCancelDescription}
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    className="details-button primary"
                    onClick={handleSaveDescription}
                    disabled={descSaving || isDescUnchanged}
                  >
                    {descSaving ? "Saving..." : "Save"}
                  </button>
                </div>
              </div>
              {descError && (
                <p className="description-error">{descError}</p>
              )}
            </div>
          ) : selectedRecord.description ? (
            <p className="dataset-description">{selectedRecord.description}</p>
          ) : (
            <p className="dataset-description dataset-description--empty">
              No description provided.
            </p>
          )}
        </div>
      )}

      {deleteOpen && (
        <div className="modal-backdrop" role="dialog" aria-modal="true">
          <div className="modal-card">
            <h4>Delete dataset?</h4>
            <p>
              Are you sure you want to delete this dataset? This cannot be undone.
            </p>
            {deleteError && (
              <p className="description-error">{deleteError}</p>
            )}
            <div className="modal-actions">
              <button
                type="button"
                className="details-button"
                onClick={handleCloseDelete}
                disabled={deleteSaving}
              >
                Cancel
              </button>
              <button
                type="button"
                className="details-button danger"
                onClick={handleConfirmDelete}
                disabled={deleteSaving}
              >
                {deleteSaving ? "Deleting..." : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
