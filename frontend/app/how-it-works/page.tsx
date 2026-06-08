import Link from "next/link";
import "@/styles/MainPage.css";
import "@/styles/HowItWorks.css";

const STEPS = [
  {
    title: "Sign Up & Verify",
    body: "Quick registration with KYC for providers (e.g., business docs) and basic info for buyers to ensure regulatory fit.",
  },
  {
    title: "List or Discover Data",
    body: "Providers upload anonymized datasets with metadata (size, domain, compliance certs); buyers filter by industry, format, or price.",
  },
  {
    title: "Review & Audit",
    body: "Automated previews plus compliance scans (PIPEDA/GDPR checks); buyers see licensing terms upfront.",
  },
  {
    title: "License & Pay",
    body: "Choose perpetual/one-time use licenses; secure checkout with royalties auto-split to providers.",
  },
  {
    title: "Access & Track",
    body: "Instant download/API access; dashboard for usage logs, renewals, and support.",
  },
  {
    title: "Scale Securely",
    body: "Providers get ongoing royalties; buyers get audit trails for their compliance needs.",
  },
];

export default function HowItWorksPage() {
  return (
    <div className="page">
      <section className="hero hero--compact">
        <div className="hero-inner">
          <p className="hero-kicker">How it works</p>
          <h1 className="hero-title">
            Compliant data trading
            <br />
            end to end
          </h1>
          <p className="hero-subtitle">
            Shannova streamlines compliant data trading—providers list vetted
            datasets, buyers license them instantly, all backed by ironclad IP
            and privacy protections.
          </p>

          <div className="cta-row">
            <Link href="/register" className="primary-btn">
              Get started
            </Link>
            <Link href="/selling" className="secondary-link">
              Browse marketplace <span aria-hidden="true">→</span>
            </Link>
          </div>
        </div>
      </section>

      <section className="home-section home-section--light">
        <div className="home-section-inner">
          <p className="section-kicker">Process</p>
          <h2 className="section-title">A 6-step flow you can trust</h2>
          <p className="section-subtitle">
            From verification through licensing and audit trails, each step is
            designed to keep data privacy-safe and business-ready.
          </p>

          <div className="hiw-flow-grid" aria-label="How Shannova works">
            {STEPS.map((s, idx) => (
              <div key={s.title} className="hiw-step-card">
                <div className="hiw-step-top">
                  <div className="hiw-step-num" aria-hidden="true">
                    {idx + 1}
                  </div>
                  <h3 className="hiw-step-title">{s.title}</h3>
                </div>
                <p className="hiw-step-desc">{s.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

