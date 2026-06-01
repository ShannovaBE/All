"use client";

import { useState } from "react";
import "@/styles/Auth.css";

interface PublicUser {
  id: string;
  username: string;
  email: string;
  plan?: string;
}

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus(null);
    setError(null);

    try {
      const res = await fetch(`${apiUrl}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Login failed");
      }

      const data = await res.json();
      const user: PublicUser = data.user;

      // store "session" in localStorage
      if (typeof window !== "undefined") {
        localStorage.setItem("shannova_user", JSON.stringify(user));
      }

      setStatus(`Logged in as ${user.username}`);
      // optional: redirect to selling
      window.location.href = "/selling";
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Login failed";
      setError(message);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card" role="region" aria-label="Login">
        <div className="auth-header">
          <h1 className="auth-title">Welcome back</h1>
          <p className="auth-subtitle">Sign in to continue to Shannova.</p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
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
            Password
            <div className="auth-password-row">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="auth-input auth-input--last"
                autoComplete="current-password"
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
            Log in
          </button>
        </form>

        {status && <p className="status-text success">{status}</p>}
        {error && <p className="status-text error">{error}</p>}

        <p className="auth-bottom-text">
          Don&apos;t have an account? <a href="/register">Sign up</a>
        </p>
      </div>
    </div>
  );
}
