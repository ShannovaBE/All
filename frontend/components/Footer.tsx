"use client";

import Link from "next/link";
import { useState } from "react";

export default function Footer() {
  const [email, setEmail] = useState("");

  return (
    <footer className="site-footer">
      <div className="footer-inner">
      <div className="footer-top">
        <div className="footer-links">
          <a className="footer-link" href="mailto:shannova@proton.me">
            shannova@proton.me
          </a>
          <a
            className="footer-link"
            href="https://www.instagram.com/shannnova?igsh=MWZvYXEzcGR5YXJuNg=="
            target="_blank"
            rel="noreferrer"
          >
            Instagram
          </a>
          <a
            className="footer-link"
            href="https://www.linkedin.com/company/shannova"
            target="_blank"
            rel="noreferrer"
          >
            LinkedIn
          </a>
        </div>

          <div className="footer-newsletter">
            <h3 className="footer-title">Stay informed</h3>
            <p className="footer-subtitle">
              Get updates on new data sets and features.
            </p>

            <form
              className="footer-form"
              onSubmit={(e) => {
                e.preventDefault();
              }}
            >
              <label className="sr-only" htmlFor="footer-email">
                Email
              </label>
              <input
                id="footer-email"
                type="email"
                inputMode="email"
                autoComplete="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="footer-input"
              />
              <button type="submit" className="footer-button">
                Subscribe
              </button>
            </form>

            <Link href="/about#faqs" className="footer-privacy">
              View our policy for details.
            </Link>
          </div>
        </div>

        <div className="footer-bottom">
          <div className="footer-brand">
            <span className="footer-mark" aria-hidden="true" />
            <span className="footer-brand-name">SHANNOVA</span>
          </div>

          <div className="footer-meta">
            <span>© {new Date().getFullYear()} Shannova. All rights reserved.</span>
            <span className="footer-meta-sep" aria-hidden="true">
              ·
            </span>
            <span>Site by Taylor Kim</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
