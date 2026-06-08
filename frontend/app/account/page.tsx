"use client";

import { useEffect, useMemo, useState } from "react";
import RequireAuth from "@/components/RequireAuth";
import "@/styles/Account.css";
import "@/styles/Plans.css";

type Plan = "free" | "basic" | "business" | "enterprise";

type PublicUser = {
  id: string;
  username: string;
  email: string;
  plan?: Plan | string;
};

const PLANS: Array<{
  key: Plan;
  name: string;
  price: string;
  priceSub?: string;
  desc: string;
}> = [
  {
    key: "free",
    name: "Free",
    price: "$0",
    priceSub: "/ mo",
    desc: "Get started with limited free access.",
  },
  {
    key: "basic",
    name: "Basic",
    price: "$9",
    priceSub: "/ mo",
    desc: "Unlimited downloads and all categories.",
  },
  {
    key: "business",
    name: "Business",
    price: "$49",
    priceSub: "/ mo",
    desc: "Advanced features for teams and sellers.",
  },
  {
    key: "enterprise",
    name: "Enterprise",
    price: "Custom",
    desc: "Custom solutions for larger organizations.",
  },
];

export default function AccountPage() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const [user, setUser] = useState<PublicUser | null>(null);
  const [selectedPlan, setSelectedPlan] = useState<Plan>("free");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [deleteMode, setDeleteMode] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState("");

  function errorMessage(err: unknown): string {
    if (err && typeof err === "object" && "message" in err) {
      const msg = (err as { message?: unknown }).message;
      if (typeof msg === "string") return msg;
    }
    return "Something went wrong";
  }

  useEffect(() => {
    const raw =
      localStorage.getItem("shannova_user") || localStorage.getItem("shanova_user");
    if (!raw) return;
    try {
      const parsed = JSON.parse(raw) as PublicUser;
      setUser(parsed);
      const plan = (parsed.plan || "free").toString().toLowerCase() as Plan;
      if (PLANS.some((p) => p.key === plan)) setSelectedPlan(plan);
    } catch {
      setUser(null);
    }
  }, []);

  const currentPlanLabel = useMemo(() => {
    const plan = (user?.plan || "free").toString().toLowerCase();
    return PLANS.find((p) => p.key === plan)?.name || "Free";
  }, [user?.plan]);

  async function savePlan() {
    if (!user) return;
    setStatus(null);
    setError(null);

    try {
      const res = await fetch(`${apiUrl}/users/${user.id}/plan`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "X-User-Id": user.id,
        },
        body: JSON.stringify({ plan: selectedPlan }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to update plan");
      }

      const data = await res.json();
      const updated = data.user as PublicUser;
      setUser(updated);
      localStorage.setItem("shannova_user", JSON.stringify(updated));
      setStatus("Plan updated.");
    } catch (err: unknown) {
      setError(errorMessage(err));
    }
  }

  async function deleteAccount() {
    if (!user) return;
    setStatus(null);
    setError(null);

    try {
      const res = await fetch(`${apiUrl}/users/${user.id}`, {
        method: "DELETE",
        headers: { "X-User-Id": user.id },
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to delete account");
      }

      localStorage.removeItem("shannova_user");
      localStorage.removeItem("shanova_user");
      window.location.href = "/";
    } catch (err: unknown) {
      setError(errorMessage(err));
    }
  }

  return (
    <RequireAuth>
      <div className="account-page">
        <div className="account-card">
          <h1 className="account-title">Account</h1>
          <p className="account-subtitle">
            Manage your plan and account settings.
          </p>

          <div className="account-grid">
            <div className="account-panel">
              <h2 className="account-panel-title">Profile</h2>
              <div className="account-kv">
                <div>
                  <strong>Username:</strong> {user?.username}
                </div>
                <div>
                  <strong>Email:</strong> {user?.email}
                </div>
                <div>
                  <strong>Current plan:</strong> {currentPlanLabel}
                </div>
              </div>

              <p className="account-note">
                Plan changes update your local session and the backend user store.
              </p>
            </div>

            <div className="account-panel">
              <h2 className="account-panel-title">Plan</h2>

              <div className="plans" style={{ borderTop: "none", paddingTop: 0 }}>
                <div className="plans-grid">
                  {PLANS.map((p) => (
                    <button
                      key={p.key}
                      type="button"
                      className={`plan-card ${
                        selectedPlan === p.key ? "plan-card--selected" : ""
                      }`}
                      onClick={() => setSelectedPlan(p.key)}
                    >
                      <div className="plan-top">
                        <h3 className="plan-name">{p.name}</h3>
                        <div className="plan-price">
                          {p.price}
                          {p.priceSub ? (
                            <span className="plan-price-sub"> {p.priceSub}</span>
                          ) : null}
                        </div>
                      </div>
                      <p className="plan-desc">{p.desc}</p>
                    </button>
                  ))}
                </div>
              </div>

              <div className="account-actions">
                <button
                  type="button"
                  className="account-btn account-btn--primary"
                  onClick={savePlan}
                >
                  Save plan
                </button>
              </div>
            </div>

            <div className="account-panel">
              <h2 className="account-panel-title">Danger zone</h2>
              <p className="account-note">
                Deleting your account removes your user record. You will be logged out
                immediately.
              </p>

              {!deleteMode ? (
                <div className="account-actions">
                  <button
                    type="button"
                    className="account-btn account-btn--danger"
                    onClick={() => {
                      setDeleteMode(true);
                      setDeleteConfirm("");
                    }}
                  >
                    Delete account
                  </button>
                </div>
              ) : (
                <div className="account-confirm">
                  <input
                    className="account-input"
                    value={deleteConfirm}
                    onChange={(e) => setDeleteConfirm(e.target.value)}
                    placeholder='Type "DELETE" to confirm'
                    aria-label='Type "DELETE" to confirm account deletion'
                  />
                  <div className="account-actions">
                    <button
                      type="button"
                      className="account-btn account-btn--danger"
                      disabled={deleteConfirm !== "DELETE"}
                      onClick={deleteAccount}
                    >
                      Confirm delete
                    </button>
                    <button
                      type="button"
                      className="account-btn"
                      onClick={() => setDeleteMode(false)}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>

          {status && <p className="status-text success">{status}</p>}
          {error && <p className="status-text error">{error}</p>}
        </div>
      </div>
    </RequireAuth>
  );
}
