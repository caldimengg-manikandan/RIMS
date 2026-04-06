#!/usr/bin/env python3
"""
RIMS Email Diagnostics — standalone script.

Performs:
  1. Provider detection (Resend vs SMTP)
  2. SMTP health check (connect + login)
  3. Test email send via SMTP
  4. Full JSON report

Usage:
    cd backend
    python scripts/email_diag.py                       # sends to SMTP_FROM address
    python scripts/email_diag.py you@example.com       # sends to specified address

No web server or auth required.
"""

from __future__ import annotations

import json
import os
import smtplib
import sys
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# ── Bootstrap: make `app.*` importable ──────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Bypass start.ps1 guard (we are a diagnostic script, not a server)
os.environ.setdefault("BACKEND_START_MODE", "script")

from dotenv import load_dotenv

_env_path = BACKEND_DIR / ".env"
if _env_path.exists():
    load_dotenv(_env_path, override=False)


# ── Load & normalise credentials ────────────────────────────────────
def _env(key: str) -> str:
    return (os.getenv(key) or "").strip()


SMTP_HOST = _env("SMTP_HOST")
SMTP_PORT = int(_env("SMTP_PORT") or "587")
SMTP_USER = _env("SMTP_USER")
# Gmail App Passwords are pasted with spaces; strip them.
SMTP_PASSWORD_RAW = os.getenv("SMTP_PASSWORD") or ""
SMTP_PASSWORD = SMTP_PASSWORD_RAW.replace(" ", "").strip()
SMTP_FROM = _env("SMTP_FROM") or SMTP_USER

RESEND_API_KEY = _env("RESEND_API_KEY")
RESEND_FROM = _env("RESEND_FROM")


# ── Detect provider availability ────────────────────────────────────
def _resend_configured() -> bool:
    return bool(RESEND_API_KEY and RESEND_FROM)


def _smtp_configured() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


# ── Gmail quota detection ───────────────────────────────────────────
def _is_gmail_quota(err: BaseException | str) -> bool:
    msg = str(err)
    return ("Daily user sending limit exceeded" in msg) or (
        "5.4.5" in msg and "sending limit" in msg
    )


# ── SMTP health check ──────────────────────────────────────────────
def smtp_health() -> dict:
    if not _smtp_configured():
        return {
            "status": "error",
            "error": "SMTP_HOST / SMTP_USER / SMTP_PASSWORD not fully configured",
        }
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as srv:
            srv.ehlo()
            srv.starttls()
            srv.ehlo()
            srv.login(SMTP_USER, SMTP_PASSWORD)
        return {"status": "ok", "error": ""}
    except Exception as exc:
        return {
            "status": "error",
            "error": f"[{exc.__class__.__name__}] {exc}\n{traceback.format_exc()}",
        }


# ── SMTP send ───────────────────────────────────────────────────────
def smtp_send(to_email: str) -> dict:
    if not _smtp_configured():
        return {
            "success": False,
            "deferred": False,
            "error": "SMTP not configured",
        }
    try:
        msg = MIMEMultipart()
        msg["Subject"] = "RIMS Email Diagnostics — test message"
        msg["From"] = SMTP_FROM
        msg["To"] = to_email
        msg.attach(
            MIMEText(
                "<html><body>"
                "<h2>RIMS Email Diagnostics</h2>"
                "<p>If you can read this, SMTP delivery is working.</p>"
                f"<p><small>Sent via {SMTP_HOST}:{SMTP_PORT} as {SMTP_USER}</small></p>"
                "</body></html>",
                "html",
            )
        )
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as srv:
            srv.starttls()
            srv.login(SMTP_USER, SMTP_PASSWORD)
            srv.send_message(msg)
        return {"success": True, "deferred": False, "error": ""}
    except Exception as exc:
        deferred = _is_gmail_quota(exc)
        return {
            "success": False,
            "deferred": deferred,
            "error": f"[{exc.__class__.__name__}] {exc}\n{traceback.format_exc()}",
        }


# ── Resend check ────────────────────────────────────────────────────
def resend_status() -> dict:
    if not _resend_configured():
        reason_parts = []
        if not RESEND_API_KEY:
            reason_parts.append("RESEND_API_KEY missing")
        if not RESEND_FROM:
            reason_parts.append("RESEND_FROM missing")
        return {
            "status": "skipped",
            "error": f"Resend disabled: {'; '.join(reason_parts)}",
        }
    # If configured, we could try a domains list call, but the user said skip Resend.
    return {"status": "ok", "error": ""}


# ── Main ────────────────────────────────────────────────────────────
def main() -> None:
    to_email = sys.argv[1] if len(sys.argv) > 1 else SMTP_FROM

    print(f"\n{'='*60}")
    print(f"  RIMS Email Diagnostics")
    print(f"{'='*60}")
    print(f"  SMTP_HOST       : {SMTP_HOST}")
    print(f"  SMTP_PORT       : {SMTP_PORT}")
    print(f"  SMTP_USER       : {SMTP_USER}")
    print(f"  SMTP_PASSWORD   : {'*' * len(SMTP_PASSWORD)} ({len(SMTP_PASSWORD)} chars, spaces removed)")
    print(f"  SMTP_FROM       : {SMTP_FROM}")
    print(f"  RESEND_API_KEY  : {'set' if RESEND_API_KEY else '(empty)'}")
    print(f"  RESEND_FROM     : {RESEND_FROM or '(empty — Resend disabled)'}")
    print(f"  Target email    : {to_email}")
    print(f"{'='*60}\n")

    # 1. Resend status
    print("[1/3] Checking Resend configuration...")
    resend_info = resend_status()
    print(f"      → {resend_info['status']}  {resend_info.get('error', '')}")

    # 2. SMTP health check
    print("[2/3] SMTP health check (connect + STARTTLS + AUTH)...")
    health = smtp_health()
    print(f"      → {health['status']}")
    if health["status"] != "ok":
        print(f"      ERROR: {health['error']}")

    # 3. Test send
    provider_used = "smtp"  # Resend is skipped when not configured
    print(f"[3/3] Sending test email to {to_email} via {provider_used}...")
    send_result = smtp_send(to_email)
    if send_result["success"]:
        print(f"      → SUCCESS — check {to_email} inbox (and spam folder)")
    else:
        print(f"      → FAILED")
        if send_result["deferred"]:
            print(f"      → DEFERRED (Gmail daily quota limit)")
        print(f"      ERROR: {send_result['error']}")

    # Build final JSON report
    root_cause = ""
    if health["status"] != "ok":
        root_cause = f"SMTP health check failed: {health['error'][:200]}"
    elif not send_result["success"]:
        if send_result["deferred"]:
            root_cause = "Gmail daily sending quota exceeded (550 5.4.5)"
        else:
            root_cause = f"SMTP send failed: {send_result['error'][:200]}"

    report = {
        "smtp": {
            "status": health["status"],
            "error": health["error"] if health["status"] != "ok" else (send_result.get("error") or ""),
            "success": send_result["success"],
            "deferred": send_result["deferred"],
        },
        "resend": resend_info,
        "provider_used": provider_used,
        "root_cause": root_cause or "none — email sent successfully",
    }

    print(f"\n{'='*60}")
    print("  REPORT (JSON)")
    print(f"{'='*60}")
    print(json.dumps(report, indent=2))
    print()


if __name__ == "__main__":
    main()
