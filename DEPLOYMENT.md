# MediTrack Deployment

This app is ready to deploy as a single Flask web service because the backend also serves the frontend files.

## Render setup

1. Push this repository to GitHub.
2. Create a new Render Blueprint or Web Service from the repo.
3. Use the `render.yaml` file at the repo root, or configure the service manually with:
   - Root directory: `hospital-warehouse`
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn wsgi:app`
4. Add these environment variables:
   - `APP_ENV=production`
   - `SECRET_KEY=<generated secret>`
   - `DEFAULT_ADMIN_PASSWORD=<strong password>`
   - `DATABASE_PATH=/var/data/hospital_data.db`
5. Attach a persistent disk and mount it at `/var/data` if you want SQLite data to survive redeploys and restarts.

## Notes

- On free Render web services, the filesystem is ephemeral and persistent disks are not available, so SQLite data will reset on restart or redeploy.
- For durable internet hosting on Render, use a paid web service with a persistent disk or migrate the app to Postgres later.
- Authentication tokens are still stored in memory, so users will be logged out after each restart.
