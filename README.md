# Gonzaga Club Event Django App

A Django port of the Streamlit Gonzaga University Club Tracker with authentication, club leadership, events, membership tracking, capacity/waitlist handling, event categories/tags, cover images, and post-event attendance check-in.

## Features

- Gonzaga-only signup domains: `gonzaga.edu` and `zagmail.gonzaga.edu` by default
- Dashboard counts and recent memberships/upcoming events
- Club CRUD, club rosters, and membership enrollment/removal
- Admin-assigned club leaders using `ClubLeadership`
- Event CRUD with many-to-many clubs, cover images, categories, tags, capacity limits, RSVP waitlist, and attendance check-in
- Permissions: superusers manage everything; club leaders manage only their clubs/events
- Django admin configured for quick administration
- Railway and PythonAnywhere friendly settings

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
python -m pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000.

## Railway deployment

1. Create a Railway project and connect this repo/package.
2. Add PostgreSQL.
3. Set environment variables from `.env.example` (`SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `DATABASE_URL`).
4. Railway uses `Procfile`: `python manage.py migrate && gunicorn club_event_site.wsgi`.

## PythonAnywhere deployment

1. Upload the project and create a virtualenv.
2. Install requirements: `python -m pip install -r requirements.txt`.
3. Configure the WSGI file to point to `club_event_site.settings`.
4. Set environment variables in the Web tab or `.env` file.
5. Run `python manage.py migrate` and `python manage.py collectstatic`.
6. Map `/static/` to `STATIC_ROOT` and `/media/` to `MEDIA_ROOT`.

## Notes

- Use Django admin to assign leaders: add a `ClubLeadership` row linking a user to a club.
- Students are Django users/profiles. This avoids duplicate login and student records.
- Cover images use local media storage by default. For production at scale, swap to S3/cloud storage.
