import Link from "next/link";
import "@/styles/InfoPages.css";

export default function GdprCompliantPage() {
  return (
    <div className="info-page">
      <div className="info-inner">
        <section className="info-hero">
          <p className="info-kicker">Marketplace</p>
          <h1 className="info-title">GDPR compliant by default</h1>
          <p className="info-subtitle">
            Shannova is built for privacy-safe data trading. Listings are
            designed to avoid personal data, surface consent and licensing terms
            clearly, and provide audit-friendly provenance for buyers and
            sellers.
          </p>

          <div className="info-cta">
            <Link href="/selling" className="info-btn info-btn--solid">
              Browse datasets
            </Link>
            <Link href="/upload" className="info-btn">
              List a dataset
            </Link>
          </div>
        </section>

        <section className="info-section">
          <h2 className="info-section-title">What You Get</h2>
          <div className="info-grid">
            <div className="info-card">
              <h3>Privacy-first listings</h3>
              <p>
                Datasets are described with clear metadata and intended usage.
                The goal is to keep the marketplace free of personal data and
                focused on business-ready, compliant datasets.
              </p>
            </div>
            <div className="info-card">
              <h3>Transparent licensing</h3>
              <p>
                Buyers can review licensing and usage expectations up front—so
                teams can adopt data with fewer surprises later in procurement,
                legal, and compliance reviews.
              </p>
            </div>
            <div className="info-card">
              <h3>Audit-friendly provenance</h3>
              <p>
                Listings are structured to support traceability and audit trails
                across data ownership, transformations, and downstream use.
              </p>
            </div>
            <div className="info-card">
              <h3>Compliance support</h3>
              <p>
                Built-in checks and conventions help sellers publish safer data
                and help buyers adopt it responsibly across regulated
                environments.
              </p>
            </div>
          </div>
        </section>

        <section className="info-section">
          <h2 className="info-section-title">Good To Know</h2>
          <ul className="info-list">
            <li>
              GDPR compliance depends on your specific use case—especially if
              you combine datasets or enrich them with other sources.
            </li>
            <li>
              Always review licensing terms and your organization&apos;s policies
              before deploying data into production systems.
            </li>
            <li>
              If you need tailored compliance guidance, contact your legal or
              privacy team.
            </li>
          </ul>
        </section>
      </div>
    </div>
  );
}
