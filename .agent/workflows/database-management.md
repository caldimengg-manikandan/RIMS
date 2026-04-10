---
description: How to manage and sync database schema and migrations
---

This workflow ensures consistency between the SQLAlchemy models (local) and the Supabase database schema.

### 1. Update SQLAlchemy Models
Modify the models in `backend/app/domain/models.py` as needed for new features or changes.

### 2. Generate Local Schema SQL
// turbo
Run the following command to update the official schema definition:
```bash
cd backend && venv/Scripts/python scripts/generate_schema.py > ../database/schema/schema.sql
```

### 3. Create Supabase Migration
If you need to apply changes to the Supabase environment, create a new migration file in `supabase/migrations/`:
```bash
# Example
touch supabase/migrations/$(date +%Y%m%d%H%M%S)_new_migration.sql
```
Copy the relevant DDL changes from `database/schema/schema.sql` into this new migration file.

### 4. Apply Migrations to Supabase (Optional)
If you have the Supabase CLI installed, you can push migrations:
```bash
supabase db push
```
