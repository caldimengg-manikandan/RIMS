# CALRIMS - Automated Recruitment System

An AI-powered, fully automated recruitment platform with intelligent interviews, resume screening, data-driven hiring decisions, and a **premium user experience**.

## 🌟 Recent Architecture & UI Upgrades

We have recently overhauled the frontend to deliver a state-of-the-art visual experience:

- **Unified Global Navigation**: A responsive, dynamically contextual Global Navbar (`GlobalNavbar`) that provides seamless, uninterrupted navigation across Landing, Authentication, and Dashboard views.
- **Premium Theming**: Perfectly balanced Dark and Light modes featuring customized, glare-free navy (`blue-950`) color hierarchies, immersive glassmorphism (`backdrop-blur-xl`), and meticulously standardized 40x40 interactive layout icons.
- **Immersive Authentication**: Completely redesigned, two-column interactive login and registration flows featuring dynamic animations and AI-generated HR branding.

## Project Overview

This is a production-ready recruitment system consisting of:

1. **MySQL Database** - Relational database for persistent storage
2. **Python FastAPI Backend** - RESTful API with AI integration
3. **Next.js 16 Frontend** - Modern React UI for candidates and HR

### Key Features

- **AI-Powered Interviews**: Adaptive, intelligent interviews that adjust questions based on responses
- **Resume Screening**: Automatic parsing and skill matching against job requirements
- **Role-Based Access**: Separate interfaces for candidates and HR managers
- **Real-Time Pipeline**: Track applications through the hiring funnel
- **Interview Reports**: Comprehensive AI-generated assessments with recommendations
- **Data-Driven Decisions**: Detailed analytics and candidate scoring

---

## Directory Structure

```
├── /
│   ├── app/                          # Next.js frontend
│   │   ├── auth/                     # Authentication pages
│   │   │   ├── login/
│   │   │   └── register/
│   │   ├── dashboard/                # Protected dashboard
│   │   │   ├── candidate/            # Candidate views
│   │   │   └── hr/                   # HR views
│   │   ├── page.tsx                  # Landing page
│   │   ├── layout.tsx                # Root layout (now including Global Navbar)
│   │   └── globals.css               # Global styles (custom premium palettes)
│   ├── lib/
│   │   ├── auth-context.tsx          # Auth state management
│   │   ├── api-client.ts             # API client utility
│   │   └── utils.ts                  # Helper functions
│   ├── components/                   # Core components (Global Navbar, Sidebar, etc.)
│   ├── .env.local                    # Frontend env vars
│   ├── package.json
│   └── tsconfig.json
│
├── backend/                          # Python FastAPI backend
│   ├── app/
│   │   ├── main.py                   # FastAPI application
│   │   ├── config.py                 # Settings
│   │   ├── database.py               # Database connection
│   │   ├── models.py                 # SQLAlchemy models
│   │   ├── auth.py                   # JWT authentication
│   │   ├── schemas.py                # Pydantic schemas
│   │   ├── routes/                   # API endpoints
│   │   └── services/
│   │       └── ai_service.py         # AI integration (Groq/OpenAI)
│   ├── requirements.txt              # Python dependencies
│   ├── .env                          # Local env vars
│   └── scripts/                      # Deployment & Dev scripts
│
├── frontend/                         # Next.js frontend
│   ├── app/                          # Next.js pages & layouts
│   ├── components/                   # UI components
│   └── lib/                          # API client & utilities
│
└── README.md                         # This file
```

---

## System Architecture

```
┌─────────────────────────────────────────┐
│  Next.js Frontend (React + TypeScript)  │
│  - Candidate Portal                     │
│  - HR Dashboard                         │
└──────────────┬──────────────────────────┘
               │ (REST API with JWT)
┌──────────────▼──────────────────────────┐
│  Python FastAPI Backend                 │
│  - Authentication                       │
│  - Job Management                       │
│  - Application Handling                 │
│  - AI Interview Engine                  │
│  - Report Generation                    │
│  - Decision Making                      │
└──────────────┬──────────────────────────┘
               │ (SQLAlchemy ORM)
┌──────────────▼──────────────────────────┐
│  MySQL Database (rims_db)               │
│  - Users, Jobs, Applications            │
│  - Interviews, Reports, Decisions       │
└──────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│  OpenAI GPT-4o (External AI Service)     │
│  - Resume Parsing                        │
│  - Question Generation                   │
│  - Answer Evaluation                     │
│  - Report Generation                     │
└──────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- Node.js 18+ (for Next.js)
- Python 3.9+ (for FastAPI)
- PostgreSQL 12+ (database)
- OpenAI API key (for AI features)

### 1. Database Setup

```bash
# Ensure MySQL is running locally (default port 3306)
# Create the database 'rims_db'
mysql -u root -p -e "CREATE DATABASE rims_db;"
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows: venv\Scripts\activate)
source venv/bin/activate

# Copy example env or create .env
# Edit .env with your settings:
# DATABASE_URL=mysql+pymysql://root:password@localhost/rims_db
# GROQ_API_KEY=gsk_your_key

# Install dependencies
pip install -r requirements.txt

# Run server (tables are auto-created on startup)
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 10000
```

Server: `http://localhost:10000`
API Docs: `http://localhost:10000/docs`

### 3. Frontend Setup

```bash
# From root directory

# Install dependencies
npm install

# Create .env.local
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:10000" > .env.local

# Run dev server
npm run dev
```

Frontend: `http://localhost:3000`

### 4. Test the System

**Test Credentials** (created automatically by backend):

Candidate:

- Email: `candidate@example.com`
- Password: `password123`

HR Manager:

- Email: `hr@company.com`
- Password: `password123`

---

## Support & Documentation

- **API Documentation**: `http://localhost:10000/docs` (Swagger UI)
- **Frontend Dashboard**: `http://localhost:3000`

---

## License

This project was built with React, Next.js, and Python and is ready for production use.

---

**Happy Hiring! 🚀**
