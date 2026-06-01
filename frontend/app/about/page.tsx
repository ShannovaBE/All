import Link from "next/link";
import "@/styles/AboutPage.css";

const FAQ_GROUPS: Array<{
  title: string;
  items: Array<{ q: string; a: string }>;
}> = [
  {
    title: "Getting Started",
    items: [
      {
        q: "What is Shannova?",
        a: "Shannova is a secure platform connecting data providers with AI/ML buyers for compliant trading of anonymized datasets, ensuring full IP protection and privacy under PIPEDA and GDPR.",
      },
      {
        q: "Who can use Shannova?",
        a: "Data providers (businesses with vetted datasets) and buyers (AI teams, researchers) worldwide; quick signup with KYC for providers to maintain compliance.",
      },
      {
        q: "How do I sign up?",
        a: "Visit our homepage, click “Get Started,” enter basic info, and verify via email. Providers submit business docs for approval within 24 hours.",
      },
    ],
  },
  {
    title: "Listing & Selling Data",
    items: [
      {
        q: "How do I list a dataset?",
        a: "Upload your anonymized file with metadata (size, domain, price), run our auto-compliance scan, set licensing terms, and go live—earn royalties on every sale.",
      },
      {
        q: "What types of datasets can I list?",
        a: "Aggregated, anonymized data in CSV/JSON and many other formats for AI use cases like healthcare, finance, or marketing—must pass privacy/IP checks.",
      },
      {
        q: "How are royalties paid?",
        a: "Automatic payouts monthly via PayPal/Stripe in CAD/EUR, with transparent dashboard tracking sales and splits (you set your margin).",
      },
    ],
  },
  {
    title: "Buying & Using Data",
    items: [
      {
        q: "How do I find and buy datasets?",
        a: "Search by industry/filter, preview samples, review license terms, and purchase instantly—download via secure link or API.",
      },
      {
        q: "What licenses are available?",
        a: "Flexible options: one-time use, perpetual, or subscription-based, all with clear usage rights and audit trails for your compliance.",
      },
      {
        q: "Is the data safe for AI training?",
        a: "Yes—every dataset undergoes automated privacy scans to eliminate PII risks, backed by Canadian/EU standards.",
      },
    ],
  },
  {
    title: "Compliance & Security",
    items: [
      {
        q: "How do you ensure compliance?",
        a: "Built-in tools check for PIPEDA, GDPR, and IP compliance at upload/preview; we provide certifications and logs for your records.",
      },
      {
        q: "What if there’s a data issue?",
        a: "Full refunds within 7 days, plus support team mediation; our escrow holds funds until buyer confirmation.",
      },
      {
        q: "Do you store my data long-term?",
        a: "No—datasets are hosted transiently for trading; providers control deletion, and we use end-to-end encryption.",
      },
    ],
  },
  {
    title: "Support & Pricing",
    items: [
      {
        q: "How much does it cost?",
        a: "Free for providers to list/browse; buyers pay per dataset (provider-set pricing) with no platform fees on first 5 trades.",
      },
    ],
  },
];

export default function AboutPage() {
  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#12274a",
        color: "rgba(248,250,252,0.92)",
      }}
    >
      <section style={{ padding: "72px 20px 44px", background: "#12274a" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1.4fr 0.6fr",
              gap: 34,
              alignItems: "start",
            }}
          >
            <div>
              <p
                style={{
                  margin: "0 0 14px",
                  fontSize: 12,
                  letterSpacing: "0.18em",
                  textTransform: "uppercase",
                  color: "rgba(248,250,252,0.62)",
                }}
              >
                About Shannova
              </p>

              <h1
                style={{
                  margin: "0 0 16px",
                  fontSize: "clamp(44px, 5.8vw, 78px)",
                  lineHeight: 1.02,
                  letterSpacing: "-0.03em",
                  fontWeight: 600,
                }}
              >
                Your trusted data marketplace
              </h1>

              <p
                style={{
                  margin: 0,
                  maxWidth: 700,
                  fontSize: 13,
                  lineHeight: 1.8,
                  color: "rgba(248,250,252,0.72)",
                }}
              >
                We make buying and selling data simple, secure, and fully
                compliant. Access high-quality, privacy-safe datasets for
                business use—no personal information, always ready for global
                markets.
              </p>

              <div style={{ marginTop: 22, display: "flex", gap: 14, flexWrap: "wrap" }}>
                <Link
                  href="/selling"
                  style={{
                    textDecoration: "none",
                    fontWeight: 700,
                    borderRadius: 10,
                    padding: "10px 14px",
                    background: "rgba(255,255,255,0.95)",
                    color: "#12274a",
                    boxShadow: "0 10px 18px rgba(18,39,74,0.28)",
                  }}
                >
                  Browse datasets
                </Link>
                <Link
                  href="/upload"
                  style={{
                    textDecoration: "none",
                    fontWeight: 700,
                    borderRadius: 10,
                    padding: "10px 14px",
                    background: "rgba(255,255,255,0.08)",
                    color: "rgba(248,250,252,0.92)",
                    border: "1px solid rgba(255,255,255,0.28)",
                  }}
                >
                  List a dataset
                </Link>
              </div>
            </div>

            <div>
              <p
                style={{
                  margin: "0 0 10px",
                  fontSize: 11,
                  letterSpacing: "0.14em",
                  textTransform: "uppercase",
                  color: "rgba(248,250,252,0.58)",
                }}
              >
                Available data types
              </p>

              <div style={{ display: "grid", gap: 10, maxWidth: 260 }}>
                {["Market analytics", "Synthetic records", "Verified quality"].map(
                  (label) => (
                    <span
                      key={label}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        justifyContent: "flex-start",
                        padding: "8px 10px",
                        borderRadius: 10,
                        fontSize: 11,
                        letterSpacing: "0.08em",
                        textTransform: "uppercase",
                        color: "rgba(248,250,252,0.9)",
                        background: "rgba(255,255,255,0.08)",
                        border: "1px solid rgba(255,255,255,0.18)",
                      }}
                    >
                      {label}
                    </span>
                  )
                )}
              </div>
            </div>
          </div>

          <div
            style={{
              marginTop: 24,
              borderTop: "1px solid rgba(255,255,255,0.18)",
            }}
          />
        </div>
      </section>

      <section className="about-faq-section">
        <div className="about-faq-inner">
          <h2 id="faqs" className="about-faq-title">
            FAQs
          </h2>
          <p className="about-faq-subtitle">
            Quick answers across onboarding, selling, buying, compliance, and
            pricing—designed to help you get moving fast.
          </p>

          <div className="about-faq-grid">
            {FAQ_GROUPS.map((group) => (
              <div key={group.title} className="about-faq-group">
                <h3 className="about-faq-group-title">{group.title}</h3>
                {group.items.map((item) => (
                  <div key={item.q} className="about-faq-item">
                    <p className="about-faq-q">{item.q}</p>
                    <p className="about-faq-a">{item.a}</p>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
