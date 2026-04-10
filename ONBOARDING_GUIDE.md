# Onboarding Pipeline Guide

This guide explains the onboarding workflow and how to manage offer letter templates in the RIMS platform.

## 1. Onboarding Workflow Flow
The platform follows a structured, multi-step onboarding process to ensure compliance and clear communication with candidates.

| Step | Action | Description |
| :--- | :--- | :--- |
| **1. Request Offer** | HR / Admin | Click "Request Offer" on a candidate in the "hired" status. You must select a joining date. |
| **2. Template Snapshot** | System | The system takes a snapshot of the *current* global offer letter template from the Settings page. This ensures that even if you change the template later, existing offers remain consistent. |
| **3. Approval** | Super Admin | Super Admins review the offer request. Once approved, the system generates an immutable PDF contract. |
| **4. Email Notification** | System | An automated email is sent to the candidate with their unique offer PDF and a secure link to accept or reject the offer. |
| **5. Candidate Response** | Candidate | The candidate clicks the link in their email to accept or reject the offer. Their decision is logged along with their IP address for auditing. |
| **6. Dashboard Update** | System | The candidate's status automatically updates to "accepted" or "rejected" on the dashboard. |
| **7. Finalizing Join** | HR / System | On the joining date, the system automatically moves the candidate to "onboarded." Alternatively, HR can click "Finalize Join" manually. |

---

## 2. Managing Offer Letter Templates

### When to Edit the Template
The system now comes with a **Professional Business Template** as the default. You should edit this global template in the **Settings** dashboard **BEFORE** clicking "Request Offer" for a candidate. 
*   **Static Snapshotting**: Once an HR member requests an offer, the template is "locked" for that specific candidate. This prevents accidental changes to legal documents if the global company template is updated later.
*   **Dynamic Placeholders**: The professional template uses placeholders like `{{candidate_name}}`, `{{job_role}}`, and `{{company_name}}`. These are automatically replaced with real data during PDF generation.

### How to Edit
1.  Navigate to **Dashboard > Settings**.
2.  Scroll down to the **Offer Letter Template** section.
3.  Write your agreement in HTML format (using placeholders where necessary).
4.  Click **Save Settings**.

---

## 3. Reliability Monitoring
The **Reliability Monitoring** panel (accessible via the sidebar) is a tool for Super Admins to track background failures, specifically during AI resume parsing. If a candidate upload gets stuck or fails, you can "Force Retry" from that page to resume processing.
