---
marp: true
theme: default
class: lead
---

# Shannova: Path to Production
## Critical Missing Features & GDPR Compliance Roadmap

---

## 1. Phase 1: Critical Architecture (Must Do)

These items are required to prevent server crashes, massive cloud bills, or data breaches.

- **Background Processing (Pub/Sub):** AI models must run asynchronously. Currently, uploads hold the HTTP request open, which will crash the server on large files.
- **Direct-to-Storage Uploads:** Browsers must upload directly to Google Cloud Storage via Signed URLs to bypass FastAPI server RAM limits.
- **Rate Limiting:** Implement IP-based limits (e.g., Cloud Armor) to prevent DDoS attacks from exploiting expensive AI compute time.
- **Authentication:** Re-enable and harden OAuth/Login to securely track dataset ownership.

---

## 2. Phase 2: Marketplace Mechanics (Core Business)

Without these, Shannova cannot facilitate trades or generate revenue.

- **Payment Gateway:** Implement Stripe Connect to split payments between the data Seller and Shannova (Platform Fee).
- **Access Control Gating:** The backend must cryptographically verify a purchase record in PostgreSQL before issuing a Cloud Storage download link.
- **Dataset Previews:** Extract and display the first 20 rows of a dataset so buyers can "Try before they buy."
- **Advanced Search:** Implement Algolia or Typesense to allow users to search through dataset descriptions and AI-generated tags.

---

## 3. Phase 3: AI & Security Polishing

- **Malware Scanning:** Implement automated ClamAV scanning on the Cloud Storage bucket to prevent the distribution of malicious macros or ZIP bombs.
- **MIME-Type Hardening:** Strictly reject unsupported proprietary file types before they crash the AI pipelines.
- **Model Fine-Tuning:** Continuously train the Beta and Gamma models on the specific types of data uploaded to the platform to push accuracy from 90% to 99%.

---

## 4. Phase 4: Frontend, UX, & Operations

- **Financial Dashboards:** Provide UI for Sellers to view earnings and Buyers to view purchase history.
- **Progress Bars:** Implement WebSocket or Polling connections to show users real-time AI processing steps (e.g., "Scrubbing PII...").
- **CI/CD Pipelines:** Set up GitHub Actions for automated testing and deployment.
- **Automated Backups:** Configure daily snapshots for the Google Cloud SQL database.

---

## 5. GDPR Compliance Guarantee (EU Regulation)

To ensure the EU has **zero grounds** to penalize Shannova for brokering data, the platform must adopt a "Privacy by Design" architecture. 

Currently, the Gamma engine redacts data *reactively*. To achieve absolute GDPR compliance, you must implement the following:

### A. The "Quarantine" Bucket Architecture
Uploaded data must **never** touch the main public marketplace bucket immediately.
1. Data uploads to a highly-secured `shannova-quarantine` bucket.
2. The Gamma engine processes it in memory, redacting all PII.
3. Only the *scrubbed* version is saved to the `shannova-datasets-public` bucket.
4. The original file in the quarantine bucket is **permanently and automatically deleted** within 60 seconds.

---

## 6. GDPR Compliance (Continued)

### B. "Right to be Forgotten" (Article 17)
- Even with Gamma scrubbing PII, a user might accidentally upload a CSV containing a highly specific, identifying story in a text column.
- **Requirement:** You must build an automated "Takedown API." If an EU citizen reports their data is in a dataset, Shannova must be able to instantly delete that specific dataset hash from Cloud Storage and all buyer libraries.

### C. Explicit Data Provenance (Article 30)
- You cannot sell stolen data. 
- **Requirement:** During the upload flow, the seller must check a legally binding box confirming they have the *Data Subject's explicit consent* to monetize the data. The backend must log the Seller's IP address, Timestamp, and User ID as a cryptographic audit trail to prove Shannova acted in good faith if the data is contested.