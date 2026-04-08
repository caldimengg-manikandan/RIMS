# 🏛 RIMS (Recruit Intelligence Management System) - Client Setup Guide

## Introduction
RIMS is a high-performance, AI-driven recruitment platform designed to automate the entire candidate lifecycle—from application to onboarding. This guide will help you set up the production environment for your new enterprise recruitment system.

---

## 🚀 1. Database & Schema Initialization (Supabase)
The system uses **PostgreSQL** (via Supabase) for the "Source of Truth" database and **Supabase Storage** for candidate assets.

### **Step 1: Execute Production Schema**
1.  Navigate to your Supabase project's **SQL Editor**.
2.  Open the file: `setup/production_schema.sql`.
3.  Copy and paste the entire script into the editor and click **Run**.
4.  This will create all 20+ tables, indexes, and constraints required for the system.

### **Step 2: Create Storage Buckets (Mandatory)**
You **must** create the following 4 private buckets in the Supabase **Storage** tab for the system to function:
-   `resumes`: Stores PDF and DOCX candidate CVs.
-   `id-photos`: Stores candidate profile and ID card photos.
-   `id-cards`: Stores the generated PDF employee ID cards.
-   `videos`: (Optional) Stores recorded interview sessions.

---

## 🔑 2. Environment Configuration
The system relies on a `.env` file for all critical integrations.

1.  Navigate to the `backend/` directory.
2.  Copy `.env.example` to `.env`:
    ```bash
    cp .env.example .env
    ```
3.  Fill in your specific API keys:
    -   `DATABASE_URL`: Found in Supabase project settings (Project Settings > Database).
    -   `GROQ_API_KEY`: Obtain from [Groq Console](https://console.groq.com/).
    -   `ENCRYPTION_KEY`: Mandatory for safety. Use the command in the `.env` template to generate.
    -   `SMTP_PASSWORD`: If using Gmail, you must use an "App Password," not your primary account password.

---

## 🏃 3. Launching the System
Once the database and environment are ready, you can start the system using our production scripts.

### **Backend (FastAPI)**
```powershell
# Navigate to backend and start
.\start.ps1
```

### **Frontend (Next.js)**
```bash
# Navigate to frontend and start
npm install
npm run dev
```

---

## 🛠 4. Production Security Hardening
Before taking the system live:
1.  **CORS Enforcement**: Ensure `ALLOWED_ORIGINS` in your `.env` only contains your official production frontend domain.
2.  **Role-Based Access**: The first registered user via the Super Admin bootstrap in `.env` will have full control over the system. Ensure you change the Super Admin password immediately after onboarding yourself.
3.  **Audit Logs**: All critical HR actions are logged in the `audit_logs` table for compliance. Use local monitoring to trace these logs.

---

## 📄 Support & Technical Hand-off
This system is provided as a complete delivery with a symmetric backend/database mapping. For any architectural queries, refer to `backend/app/domain/models.py`.
