---
paths:
  - "db/migrate/**/*.rb"
  - "db/schema.rb"
---

# Migration Conventions

- Prefer reversible `change` migrations when the operation is safely reversible.
- Use explicit `up`/`down` for complex data migrations or irreversible operations.
- Add `null: false` for required columns, using a two-step add/backfill/constrain pattern on existing large tables.
- Add database-level defaults where appropriate and safe for the table size.
- Add indexes for frequently queried columns and association IDs.
- Add unique indexes for uniqueness validations.
- Use foreign keys for ordinary associations when appropriate; pair them with indexes.
- For tenant ownership (`account_id`), follow the multi-tenant convention: indexed UUID reference, `foreign_key: false`, unless explicitly approved.
- Use concurrent indexes for large PostgreSQL tables when needed, with `disable_ddl_transaction!`.
- Never modify a migration that has already been run; create a new migration.
- Backfill in batches for large tables.
