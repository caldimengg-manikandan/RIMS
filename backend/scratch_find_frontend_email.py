with open('../frontend/app/jobs/[id]/page.tsx', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        if '/apply' in line or 'email' in line.lower() or 'onsubmit' in line.lower() or 'formdata' in line.lower():
            if len(line.strip()) < 120:
                print(f"{i}: {line.strip()}")
