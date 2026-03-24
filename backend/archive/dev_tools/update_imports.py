import os
import re

import_replacements = {
    r'from app\.models': r'from app.domain.models',
    r'import app\.models': r'import app.domain.models',
    r'from app\.schemas': r'from app.domain.schemas',
    r'from app\.database': r'from app.infrastructure.database',
    r'from app\.config': r'from app.core.config',
    r'from app\.middleware': r'from app.core.middleware',
    r'from app\.rate_limiter': r'from app.core.rate_limiter',
    r'from app\.logging_config': r'from app.core.logging_config',
    r'from app\.auth': r'from app.core.auth',
    r'from app\.encryption': r'from app.core.encryption',
    r'from app\.migrations': r'from app.core.migrations',
    r'from app\.routes': r'from app.api'
}

def update_imports_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    for old, new in import_replacements.items():
        content = re.sub(old + r'(?![a-zA-Z0-9_])', new, content)

    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated: {filepath}")

def main():
    app_dir = os.path.join('d:', '\\Caldim', 'RIMS-main', 'RIMS-main', 'backend', 'app')
    for root, dirs, files in os.walk(app_dir):
        # Exclude venv if it magically ended up here, or __pycache__
        if '__pycache__' in root or 'venv' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                update_imports_in_file(os.path.join(root, file))

if __name__ == "__main__":
    main()
