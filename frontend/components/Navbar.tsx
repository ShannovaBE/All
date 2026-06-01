// components/Navbar.tsx
"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

interface PublicUser {
  id: string;
  username: string;
  email: string;
  plan?: string;
}

export default function Navbar() {
  const [user, setUser] = useState<PublicUser | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [marketOpen, setMarketOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const marketButtonRef = useRef<HTMLButtonElement | null>(null);
  const marketRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;

    // Support both keys just in case of legacy typo
    const raw =
      localStorage.getItem("shannova_user") || localStorage.getItem("shanova_user");

    if (!raw) {
      setUser(null);
      return;
    }

    try {
      const parsed = JSON.parse(raw) as PublicUser;
      setUser(parsed);
    } catch {
      // ignore bad data
      setUser(null);
    }
  }, []);

  useEffect(() => {
    if (!user) {
      setIsAdmin(false);
      return;
    }

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    let cancelled = false;
    const userId = user.id;

    async function loadMe() {
      try {
        const res = await fetch(`${apiUrl}/me`, {
          headers: { "X-User-Id": userId },
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || "Failed to load session");
        if (!cancelled) setIsAdmin(Boolean(data.is_admin));
      } catch {
        if (!cancelled) setIsAdmin(false);
      }
    }

    loadMe();
    return () => {
      cancelled = true;
    };
  }, [user]);

  useEffect(() => {
    if (!menuOpen && !marketOpen) return;

    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setMenuOpen(false);
        setMarketOpen(false);
        menuButtonRef.current?.focus();
      }
    }

    function onPointerDown(e: MouseEvent) {
      const target = e.target as Node | null;
      if (!target) return;
      if (menuRef.current?.contains(target)) return;
      if (menuButtonRef.current?.contains(target)) return;
      if (marketRef.current?.contains(target)) return;
      if (marketButtonRef.current?.contains(target)) return;
      setMenuOpen(false);
      setMarketOpen(false);
    }

    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("mousedown", onPointerDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("mousedown", onPointerDown);
    };
  }, [menuOpen, marketOpen]);

  function handleLogout() {
    if (typeof window !== "undefined") {
      localStorage.removeItem("shannova_user");
      localStorage.removeItem("shanova_user"); // clean legacy key too
      setUser(null);
      setMenuOpen(false);
      setMarketOpen(false);
      window.location.href = "/";
    }
  }

  return (
    <nav className="navbar">
      <div className="nav-left">
        <div className="nav-logo">
          <Link href="/" className="big_name">
            Shannova
          </Link>
        </div>

        <ul className="nav-links">
          <li>
            <Link href="/">Home</Link>
          </li>
          <li className="nav-dropdown">
            <button
              ref={marketButtonRef}
              type="button"
              className="nav-dropdown-button"
              aria-haspopup="menu"
              aria-expanded={marketOpen}
              onClick={() => {
                setMarketOpen((v) => !v);
                setMenuOpen(false);
              }}
            >
              Marketplace
              <span className="nav-menu-caret" aria-hidden="true">
                {"\u25BE"}
              </span>
            </button>

            {marketOpen && (
              <div ref={marketRef} className="nav-menu-panel" role="menu">
                <Link
                  href="/upload"
                  className="nav-menu-item"
                  role="menuitem"
                  onClick={() => setMarketOpen(false)}
                >
                  List
                </Link>
                <Link
                  href="/selling"
                  className="nav-menu-item"
                  role="menuitem"
                  onClick={() => setMarketOpen(false)}
                >
                  Browse
                </Link>
                <Link
                  href="/gdpr-compliant"
                  className="nav-menu-item"
                  role="menuitem"
                  onClick={() => setMarketOpen(false)}
                >
                  GDPR compliant
                </Link>
              </div>
            )}
          </li>
          <li>
            <Link href="/about">About</Link>
          </li>
          <li>
            <Link href="/how-it-works">How it works</Link>
          </li>
          <li>
            <Link href="/reviews">Reviews</Link>
          </li>
        </ul>
      </div>

      <div className="nav-right">
        {user ? (
          <div className="nav-user-logged-in">
            <Link href="/history" className="nav-right-link">
              My datasets
            </Link>

            <div className="nav-menu">
              <button
                ref={menuButtonRef}
                type="button"
                className="nav-menu-button"
                aria-haspopup="menu"
                aria-expanded={menuOpen}
                onClick={() => {
                  setMenuOpen((v) => !v);
                  setMarketOpen(false);
                }}
              >
                {user.username}
                <span className="nav-menu-caret" aria-hidden="true">
                  {"\u25BE"}
                </span>
              </button>

              {menuOpen && (
                <div ref={menuRef} className="nav-menu-panel" role="menu">
                  <Link
                    href="/account"
                    className="nav-menu-item"
                    role="menuitem"
                    onClick={() => setMenuOpen(false)}
                  >
                    My account
                  </Link>
                  {isAdmin && (
                    <Link
                      href="/admin/reviews"
                      className="nav-menu-item"
                      role="menuitem"
                      onClick={() => setMenuOpen(false)}
                    >
                      Review moderation
                    </Link>
                  )}
                  <button
                    type="button"
                    className="nav-menu-item nav-menu-item--danger"
                    role="menuitem"
                    onClick={handleLogout}
                  >
                    Log out
                  </button>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="nav-auth-buttons">
            <Link href="/login" className="nav-auth-button nav-auth-button--outline">
              Login
            </Link>
            <Link href="/register" className="nav-auth-button nav-auth-button--solid">
              Sign up
            </Link>
          </div>
        )}
      </div>
    </nav>
  );
}
