import Link from "next/link";
import Image from "next/image";
import "../styles/MainPage.css";

export default function Home() {
  return (
    <div className="page">
      <section className="hero">
        <div className="hero-inner">
          <p className="hero-kicker">Business-ready data marketplace</p>

          <h1 className="hero-title">
            Buy and sell
            <br />
            trusted datasets
          </h1>

          <p className="hero-subtitle">
            Access and trade GDPR-compliant datasets for business. No personal
            data. Filter by category, quality, or synthetic type. Sell your own
            or find exclusive company data.
          </p>

          <div className="cta-row">
            <Link href="/selling" className="primary-btn">
              Browse
            </Link>

            <Link href="/upload" className="secondary-link">
              List data <span aria-hidden="true">→</span>
            </Link>
          </div>
        </div>
      </section>

      <section className="home-section home-section--light">
        <div className="home-section-inner">
          <p className="section-kicker">Browse by data type</p>
          <h2 className="section-title">Data for sale, sorted your way</h2>
          <p className="section-subtitle">
            Shop and sell curated, compliant datasets for business. Filter by
            category, quality, or synthetic status. All listings are
            GDPR-compliant and free of personal data.
          </p>

          <div className="section-cta">
            <Link href="/selling" className="light-primary-btn">
              Browse all
            </Link>
          </div>

          <div className="market-card-grid">
            <Link
              href={{ pathname: "/selling", query: { sort: "trending" } }}
              className="market-card"
            >
              <div className="market-card-media">
                <Image
                  src="/trending-card.svg"
                  alt="Trending datasets preview"
                  width={1200}
                  height={760}
                />
              </div>

              <div className="market-card-meta">
                <span className="market-chip">Synthetic</span>
                <span className="market-chip market-chip--muted">5 min read</span>
              </div>

              <h3 className="market-card-title">Trending datasets now available</h3>
              <p className="market-card-desc">
                Access top-quality datasets for analytics and business use. All
                data is privacy-safe and ready for global compliance.
              </p>
              <span className="market-card-link">
                Details <span aria-hidden="true">→</span>
              </span>
            </Link>

            <Link
              href={{ pathname: "/selling", query: { sort: "newest" } }}
              className="market-card"
            >
              <div className="market-card-media">
                <Image
                  src="/newest-card.svg"
                  alt="Newest datasets preview"
                  width={1200}
                  height={760}
                />
              </div>

              <div className="market-card-meta">
                <span className="market-chip">Real-world</span>
                <span className="market-chip market-chip--muted">5 min read</span>
              </div>

              <h3 className="market-card-title">Newest data on the market</h3>
              <p className="market-card-desc">
                Find the latest datasets from verified sellers. Instantly access
                structured, privacy-compliant data for your business needs.
              </p>
              <span className="market-card-link">
                Details <span aria-hidden="true">→</span>
              </span>
            </Link>
          </div>
        </div>
      </section>

      <section className="home-section home-section--navy">
        <div className="home-section-inner faq-split">
          <div className="faq-left">
            <h2 className="faq-title">Data marketplace FAQs</h2>
            <p className="faq-desc">
              Get quick answers about buying, selling, and compliance for
              datasets on our platform.
            </p>
            <Link href="/about" className="faq-btn">
              See all FAQs
            </Link>
          </div>

          <div className="faq-right">
            <div className="faq-item">
              <h3>How do I purchase data?</h3>
              <p>
                Browse by category or quality, add your chosen data set to cart,
                and check out securely.
              </p>
            </div>
            <div className="faq-item">
              <h3>Can I list my data for sale?</h3>
              <p>
                Yes—upload your data, ensure it meets compliance, and start
                selling to businesses.
              </p>
            </div>
            <div className="faq-item">
              <h3>Is the data GDPR compliant?</h3>
              <p>
                All data sets are reviewed for GDPR compliance and contain no
                personal data.
              </p>
            </div>
            <div className="faq-item">
              <h3>What data types are offered?</h3>
              <p>
                Access synthetic and real-world data sets across industries,
                ready for business use.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
