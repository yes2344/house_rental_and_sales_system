# Local development

## Backend

1. Install PostgreSQL and start its local service.
2. Copy `.env.example` to `.env` if you have not already done so. Keep `DJANGO_DEBUG=True`.
3. Set `POSTGRES_PASSWORD` in `.env` to the password for your local PostgreSQL user. The defaults use database `house_db`, user `postgres`, host `localhost`, and port `5432`.
4. Create the local database if it does not exist:

   ```powershell
   createdb -U postgres house_db
   ```

   If `createdb` is not on `PATH`, use the PostgreSQL 18 installation path:

   ```powershell
   & 'C:\Program Files\PostgreSQL\18\bin\createdb.exe' -U postgres house_db
   ```

5. Apply migrations and start Django:

   ```powershell
   python manage.py migrate
   python manage.py runserver
   ```

With `DJANGO_DEBUG=True`, Django uses only the local `POSTGRES_*` settings and does not use `DATABASE_URL`. This prevents local development commands from modifying a hosted database. Deployed environments with `DJANGO_DEBUG=False` continue to use their configured `DATABASE_URL` or PostgreSQL variables.

## Frontend

In a second terminal:

```powershell
Set-Location frontend
npm install
npm run dev
```

The frontend's local API proxy targets Django at `http://127.0.0.1:8000` by default.
