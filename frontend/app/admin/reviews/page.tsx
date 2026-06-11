"use client";

import RequireAuth from "@/components/RequireAuth";
import { useEffect, useMemo, useState } from "react";
import "@/styles/MainPage.css";
import "@/styles/Reviews.css";

type PublicUser = { id: string; username: string; email: string };

type ReviewRow = {
  id: string;
  user_id: string;
  reviewer_name: string;
  review_text: string;
  rating: number;
  status: string;
  view_status?: string;
  created_at: string | null;
  updated_at?: string | null;
};

const STAR = "\u2605";

function getErrorMessage(error: unknown, fallback: string) {
  if (error instanceof Error) {
    return error.message || fallback;
  }
  if (typeof error === "string" && error.trim().length > 0) {
    return error;
  }
  return fallback;
}

function Stars({ rating }: { rating: number }) {
  return (
    <span className="stars stars--dark" aria-label={`${rating} out of 5 stars`}>
      {Array.from({ length: 5 }).map((_, i) => (
        <span
          key={i}
          className={`star ${i + 1 <= rating ? "is-filled" : ""}`}
          aria-hidden="true"
        >
          {STAR}
        </span>
      ))}
    </span>
  );
}

export default function AdminReviewsPage() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const [user, setUser] = useState<PublicUser | null>(null);
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);
  const [visibilityMonths, setVisibilityMonths] = useState<number>(24);
  const [stats, setStats] = useState<{
    visible_avg_rating: number;
    visible_count: number;
    lifetime_avg_rating: number;
    lifetime_count: number;
    approved_lifetime_avg_rating: number;
    approved_lifetime_count: number;
  } | null>(null);

  const [statusFilter, setStatusFilter] = useState<
    "pending" | "visible" | "archived" | "rejected" | "all"
  >("pending");
  const [items, setItems] = useState<ReviewRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    const raw =
      localStorage.getItem("shannova_user") || localStorage.getItem("shanova_user");
    if (!raw) return;
    try {
      setUser(JSON.parse(raw) as PublicUser);
    } catch {
      setUser(null);
    }
  }, []);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    const userId = user.id;
    async function loadMe() {
      try {
        const res = await fetch(`${apiUrl}/me`, { headers: { "X-User-Id": userId } });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || "Not authorized");
        if (!cancelled) {
          setIsAdmin(Boolean(data.is_admin));
          setVisibilityMonths(Number(data.review_visibility_months || 24));
        }
      } catch {
        if (!cancelled) setIsAdmin(false);
      }
    }
    loadMe();
    return () => {
      cancelled = true;
    };
  }, [apiUrl, user]);

  async function load() {
    if (!user) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiUrl}/admin/reviews?status=${statusFilter}`, {
        headers: { "X-User-Id": user.id, "X-Username": user.username },
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Failed to load reviews");
      setItems((data.items || []) as ReviewRow[]);
      if (data.stats) setStats(data.stats);
      if (data.visibility_months) setVisibilityMonths(Number(data.visibility_months));
    } catch (e: unknown) {
      setError(getErrorMessage(e, "Failed to load reviews"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (isAdmin) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id, statusFilter, isAdmin]);

  const countLabel = useMemo(
    () => `${items.length} ${statusFilter}`,
    [items.length, statusFilter]
  );

  async function moderate(id: string, nextStatus: "approved" | "rejected") {
    if (!user) return;
    setStatus(null);
    setError(null);
    try {
      const res = await fetch(`${apiUrl}/admin/reviews/${id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "X-User-Id": user.id,
          "X-Username": user.username,
        },
        body: JSON.stringify({ status: nextStatus }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Failed to update review");
      setStatus(nextStatus === "approved" ? "Review set to visible." : "Review rejected.");
      await load();
    } catch (e: unknown) {
      setError(getErrorMessage(e, "Failed to update review"));
    }
  }

  async function remove(id: string) {
    if (!user) return;
    setStatus(null);
    setError(null);
    try {
      const res = await fetch(`${apiUrl}/admin/reviews/${id}`, {
        method: "DELETE",
        headers: { "X-User-Id": user.id, "X-Username": user.username },
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Failed to delete review");
      setStatus("Review deleted.");
      await load();
    } catch (e: unknown) {
      setError(getErrorMessage(e, "Failed to delete review"));
    }
  }

  return (
    <RequireAuth>
      <div className="reviews-light" style={{ paddingTop: 86 }}>
        <div className="reviews-light-inner">
          <h1 className="reviews-section-title">Review moderation</h1>
          <p className="reviews-section-subtitle">
            Manage review visibility and moderation. Reviews become public only when set to{" "}
            <strong>visible</strong>.
          </p>

          {isAdmin === null && <p className="status-text loading">Checking access...</p>}
          {isAdmin === false && (
            <p className="status-text error">Not authorized to view this page.</p>
          )}

          {isAdmin && stats && (
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 18 }}>
              <span className="reviews-summary-card" style={{ borderColor: "rgba(18,39,74,0.16)" }}>
                <strong>{Math.round(stats.visible_avg_rating * 10) / 10}</strong>
                <span style={{ opacity: 0.8 }}>visible avg ({stats.visible_count})</span>
              </span>
              <span className="reviews-summary-card" style={{ borderColor: "rgba(18,39,74,0.16)" }}>
                <strong>{Math.round(stats.approved_lifetime_avg_rating * 10) / 10}</strong>
                <span style={{ opacity: 0.8 }}>
                  lifetime (visible+archived) ({stats.approved_lifetime_count})
                </span>
              </span>
              <span className="reviews-summary-card" style={{ borderColor: "rgba(18,39,74,0.16)" }}>
                <strong>{Math.round(stats.lifetime_avg_rating * 10) / 10}</strong>
                <span style={{ opacity: 0.8 }}>all statuses ({stats.lifetime_count})</span>
              </span>
              <span style={{ alignSelf: "center", color: "rgba(18,39,74,0.72)" }}>
                Visibility window: {visibilityMonths} months
              </span>
            </div>
          )}

          {isAdmin && (
            <>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 18 }}>
                {(["pending", "visible", "archived", "rejected", "all"] as const).map((k) => (
                  <button
                    key={k}
                    type="button"
                    className="review-submit"
                    onClick={() => setStatusFilter(k)}
                    style={{
                      background: statusFilter === k ? "#12274a" : "rgba(18,39,74,0.1)",
                      color: statusFilter === k ? "#fff" : "#12274a",
                      boxShadow: "none",
                    }}
                  >
                    {k}
                  </button>
                ))}
                <span style={{ alignSelf: "center", marginLeft: 6, color: "rgba(18,39,74,0.72)" }}>
                  {countLabel}
                </span>
              </div>

              {loading && <p className="status-text loading">Loading...</p>}
              {status && <p className="status-text success">{status}</p>}
              {error && <p className="status-text error">{error}</p>}

              <div className="reviews-grid">
                {items.map((r) => (
                  <div key={r.id} className="review-card">
                    <div className="review-card-top">
                      <div className="review-name">{r.reviewer_name}</div>
                      <div className="review-date">
                        {r.created_at ? new Date(r.created_at).toLocaleString() : ""}
                      </div>
                    </div>
                    <Stars rating={r.rating} />
                    <p className="review-text" style={{ marginTop: 10 }}>
                      {r.review_text}
                    </p>
                    <p className="review-note" style={{ marginTop: 10 }}>
                      Status: <strong>{r.view_status || r.status}</strong>
                    </p>

                    <div style={{ marginTop: 14, display: "flex", gap: 10, flexWrap: "wrap" }}>
                      <button
                        type="button"
                        className="review-submit"
                        onClick={() => moderate(r.id, "approved")}
                        style={{ height: 38 }}
                      >
                        Make visible
                      </button>
                      <button
                        type="button"
                        className="review-submit"
                        onClick={() => moderate(r.id, "rejected")}
                        style={{
                          height: 38,
                          background: "rgba(239,68,68,0.12)",
                          color: "#b91c1c",
                          boxShadow: "none",
                        }}
                      >
                        Reject
                      </button>
                      <button
                        type="button"
                        className="review-submit"
                        onClick={() => remove(r.id)}
                        style={{
                          height: 38,
                          background: "transparent",
                          color: "#b91c1c",
                          border: "1px solid rgba(239,68,68,0.35)",
                          boxShadow: "none",
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </RequireAuth>
  );
}
