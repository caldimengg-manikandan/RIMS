with open("app/dashboard/hr/ingested-emails/page.tsx", "r", encoding="utf-8") as f:
    for idx, line in enumerate(f, 1):
        if "items.map" in line or "map(" in line or "Table" in line or "sender_email" in line:
            print(f"Line {idx}: {line.strip()}")
