"use client";

import { useState } from "react";
import "@/styles/Auth.css";
import "@/styles/Plans.css";

type Plan = "free" | "basic" | "business" | "enterprise";

export default function RegisterPage() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [plan, setPlan] = useState<Plan>("free");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus(null);
    setError(null);

    try {
      const res = await fetch(`${apiUrl}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, email, password, plan }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Registration failed");
      }

      setStatus("Account created! You can now log in.");
      setUsername("");
      setEmail("");
      setPassword("");
      setPlan("free");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Registration failed";
      setError(message);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card" role="region" aria-label="Register">
        <div className="auth-header">
          <h1 className="auth-title">Create your account</h1>
          <p className="auth-subtitle">
            Join Shannova to access compliant datasets and tools.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="plans" role="group" aria-label="Choose a plan">
            <p className="plans-kicker">Choose a plan</p>
            <div className="plans-grid">
              <button
                type="button"
                className={`plan-card ${plan === "free" ? "plan-card--selected" : ""}`}
                onClick={() => setPlan("free")}
              >
                <div className="plan-top">
                  <h3 className="plan-name">Free</h3>
                  <div className="plan-price">
                    $0 <span className="plan-price-sub">/ mo</span>
                  </div>
                </div>
                <p className="plan-desc">Get started with limited free access.</p>
              </button>

              <button
                type="button"
                className={`plan-card ${plan === "basic" ? "plan-card--selected" : ""}`}
                onClick={() => setPlan("basic")}
              >
                <div className="plan-top">
                  <h3 className="plan-name">Basic</h3>
                  <div className="plan-price">
                    $9 <span className="plan-price-sub">/ mo</span>
                  </div>
                </div>
                <p className="plan-desc">Unlimited downloads and all categories.</p>
              </button>

              <button
                type="button"
                className={`plan-card ${plan === "business" ? "plan-card--selected" : ""}`}
                onClick={() => setPlan("business")}
              >
                <div className="plan-top">
                  <h3 className="plan-name">Business</h3>
                  <div className="plan-price">
                    $49 <span className="plan-price-sub">/ mo</span>
                  </div>
                </div>
                <p className="plan-desc">Advanced features for teams and sellers.</p>
              </button>

              <button
                type="button"
                className={`plan-card ${
                  plan === "enterprise" ? "plan-card--selected" : ""
                }`}
                onClick={() => setPlan("enterprise")}
              >
                <div className="plan-top">
                  <h3 className="plan-name">Enterprise</h3>
                  <div className="plan-price">Custom</div>
                </div>
                <p className="plan-desc">Custom solutions for larger organizations.</p>
              </button>
            </div>
          </div>

          <label className="auth-label">
            Username
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              className="auth-input"
              autoComplete="username"
            />
          </label>

          <label className="auth-label">
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="auth-input"
              autoComplete="email"
            />
          </label>

          <label className="auth-label">
            Password
            <div className="auth-password-row">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="auth-input auth-input--last"
                autoComplete="new-password"
              />
              <button
                type="button"
                className="auth-toggle"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          </label>

          <button type="submit" className="auth-submit">
            Sign up ({plan})
          </button>
        </form>

        {status && <p className="status-text success">{status}</p>}
        {error && <p className="status-text error">{error}</p>}

        <p className="auth-bottom-text">
          Already have an account? <a href="/login">Log in</a>
        </p>
      </div>
    </div>
  );
}
