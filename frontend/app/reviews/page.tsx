"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import "@/styles/MainPage.css";
import "@/styles/Reviews.css";

type PublicUser = {
  id: string;
  username: string;
  email: string;
};

type PublicReview = {
  id: string;
  reviewer_name: string;
  review_text: string;
  rating: number;
  created_at: string | null;
};

type MyReview = {
  id: string;
  review_text: string;
  rating: number;
  status: "pending" | "approved" | "rejected";
  created_at: string | null;
  updated_at: string | null;
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

function Stars({
  rating,
  variant,
}: {
  rating: number;
  variant: "light" | "dark";
}) {
  const cls = variant === "dark" ? "stars stars--dark" : "stars";
  return (
    <span className={cls} aria-label={`${rating} out of 5 stars`}>
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

function formatDate(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
  });
}

function myReviewNote(status: MyReview["status"]): string {
  if (status === "approved") return "Your review is live.";
  if (status === "pending")
    return "Your review is being processed and will appear once it's ready.";
  return "Your review isn't visible yet. Please update it and submit again.";
}

export default function ReviewsPage() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const [user, setUser] = useState<PublicUser | null>(null);
  const [reviews, setReviews] = useState<PublicReview[]>([]);
  const [avgRating, setAvgRating] = useState(0);
  const [totalReviews, setTotalReviews] = useState(0);

  const [myReview, setMyReview] = useState<MyReview | null>(null);
  const [minLen, setMinLen] = useState(30);
  const [maxLen, setMaxLen] = useState(1000);

  const [rating, setRating] = useState(5);
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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
    let cancelled = false;
    async function loadReviews() {
      try {
        const res = await fetch(`${apiUrl}/reviews/public?limit=50`);
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || "Failed to load reviews");
        if (cancelled) return;
        setReviews((data.items || []) as PublicReview[]);
        setAvgRating(Number(data.avg_rating || 0));
        setTotalReviews(Number(data.total_reviews || 0));
      } catch (e: unknown) {
        if (!cancelled) setError(getErrorMessage(e, "Failed to load reviews"));
      }
    }
    loadReviews();
    return () => {
      cancelled = true;
    };
  }, [apiUrl]);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    const userId = user.id;
    async function loadMine() {
      try {
        const res = await fetch(`${apiUrl}/reviews/me`, {
          headers: { "X-User-Id": userId },
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || "Failed to load your review");
        if (cancelled) return;
        setMinLen(Number(data.min_len || 30));
        setMaxLen(Number(data.max_len || 1000));
        if (data.review) {
          setMyReview(data.review as MyReview);
          setRating(Number(data.review.rating || 5));
          setText(String(data.review.review_text || ""));
        } else {
          setMyReview(null);
        }
      } catch (e: unknown) {
        if (!cancelled) setError(getErrorMessage(e, "Failed to load your review"));
      }
    }
    loadMine();
    return () => {
      cancelled = true;
    };
  }, [apiUrl, user]);

  const avgRounded = useMemo(() => Math.round(avgRating * 10) / 10, [avgRating]);

  async function submit() {
    if (!user) return;
    setSaving(true);
    setStatus(null);
    setError(null);
    try {
      const res = await fetch(`${apiUrl}/reviews/me`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", "X-User-Id": user.id },
        body: JSON.stringify({ review_text: text, rating }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Failed to submit review");
      setMyReview(data.review as MyReview);
      setStatus("Thanks! Your review has been received.");
    } catch (e: unknown) {
      setError(getErrorMessage(e, "Failed to submit review"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="reviews-page">
      <section className="hero hero--compact">
        <div className="hero-inner">
          <p className="hero-kicker">Reviews</p>
          <h1 className="hero-title">
            What teams say
            <br />
            about Shannova
          </h1>
          <p className="hero-subtitle">
            Reviews shown here are from the most recent period. If you&apos;re signed in, you can
            leave one review and edit it anytime.
          </p>

          <div className="reviews-summary">
            <span className="reviews-summary-card">
              <Stars rating={Math.round(avgRating)} variant="light" />
              <strong>{avgRounded}</strong>
              <span style={{ opacity: 0.8 }}>avg rating</span>
            </span>
            <span className="reviews-summary-card">
              <strong>{totalReviews}</strong>
              <span style={{ opacity: 0.8 }}>reviews</span>
            </span>
          </div>
        </div>
      </section>

      <section className="reviews-light">
        <div className="reviews-light-inner">
          <h2 className="reviews-section-title">Customer reviews</h2>
          <p className="reviews-section-subtitle">
            Recent feedback from buyers and providers using the marketplace.
          </p>

          {error && <p className="status-text error">{error}</p>}

          <div className="reviews-grid">
            {reviews.map((r) => (
              <div key={r.id} className="review-card">
                <div className="review-card-top">
                  <div className="review-name">{r.reviewer_name}</div>
                  <div className="review-date">{formatDate(r.created_at)}</div>
                </div>
                <Stars rating={r.rating} variant="dark" />
                <p className="review-text" style={{ marginTop: 10 }}>
                  {r.review_text}
                </p>
              </div>
            ))}

            <div className="review-form">
              <h3>{user ? "Leave a review" : "Sign in to leave a review"}</h3>
              {!user ? (
                <>
                  <p className="review-note">You must be signed in to submit a review.</p>
                  <div style={{ marginTop: 12 }}>
                    <Link href="/login" className="light-primary-btn">
                      Sign in
                    </Link>
                  </div>
                </>
              ) : (
                <>
                  <div className="rating-row">
                    <span style={{ fontWeight: 800 }}>Rating</span>
                    <div
                      className="stars stars--dark"
                      role="radiogroup"
                      aria-label="Star rating"
                    >
                      {Array.from({ length: 5 }).map((_, i) => {
                        const value = i + 1;
                        const filled = value <= rating;
                        return (
                          <button
                            key={value}
                            type="button"
                            className="star-button"
                            onClick={() => setRating(value)}
                            aria-label={`${value} star`}
                            aria-checked={value === rating}
                            role="radio"
                          >
                            <span
                              className={`star ${filled ? "is-filled" : ""}`}
                              aria-hidden="true"
                            >
                              {STAR}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <textarea
                    className="review-textarea"
                    value={text}
                    maxLength={maxLen}
                    onChange={(e) => setText(e.target.value)}
                    placeholder={`Write your review (min ${minLen} characters).`}
                    aria-busy={saving}
                  />

                  <div className="review-form-row">
                    <span className="review-counter">
                      {text.trim().length}/{maxLen}
                    </span>
                    <button
                      type="button"
                      className="review-submit"
                      onClick={submit}
                      disabled={saving}
                    >
                      {saving ? "Submitting..." : myReview ? "Update review" : "Submit review"}
                    </button>
                  </div>

                  {myReview && <p className="review-note">{myReviewNote(myReview.status)}</p>}
                  {status && <p className="status-text success">{status}</p>}
                  {error && <p className="status-text error">{error}</p>}
                </>
              )}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
