# Render Deployment Guide

This guide will help you deploy Xcellar to Render.

## Prerequisites

1. A Render account
2. A PostgreSQL database on Render
3. (Optional) A Redis instance on Render

## Step 1: Create PostgreSQL Database

1. Go to your Render dashboard
2. Click "New +" → "PostgreSQL"
3. Choose a name and plan
4. Copy the **Internal Database URL** or individual connection details

## Step 2: Create Web Service

1. Connect your GitHub repository to Render
2. Create a new "Web Service"
3. Configure the service:
   - **Name**: `xcellar-api` (or your preferred name)
   - **Environment**: `Docker`
   - **Dockerfile Path**: `Dockerfile`
   - **Root Directory**: (leave empty)

## Step 3: Environment Variables

Add these environment variables in the Render dashboard:

### Required Variables

```
DJANGO_SETTINGS_MODULE=xcellar.settings.production
SECRET_KEY=your-super-secret-key-here-min-50-characters
DEBUG=False
ALLOWED_HOSTS=your-app-name.onrender.com,www.your-app-name.onrender.com
```

### Database Variables (from your PostgreSQL service)

```
DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=your-db-host.onrender.com
DB_PORT=5432
DB_SSLMODE=require
```

### Optional Variables

```
PORT=8000  # Render sets this automatically, but you can override
WEB_CONCURRENCY=4  # Number of gunicorn workers

# Redis (if you're using Redis on Render)
REDIS_HOST=your-redis-host.onrender.com
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password  # If Redis has a password

# Email Configuration (for password resets)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=Xcellar <noreply@yourdomain.com>

# Paystack (for payments)
PAYSTACK_SECRET_KEY=sk_test_...
PAYSTACK_PUBLIC_KEY=pk_test_...
PAYSTACK_WEBHOOK_SECRET=your-webhook-secret

# Twilio (for phone verification)
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_VERIFY_SERVICE_SID=your-verify-service-sid

# API Configuration
API_BASE_URL=https://your-app-name.onrender.com/api/v1
PASSWORD_RESET_URL=https://your-app-name.onrender.com/reset-password
```

## Step 4: Deploy

1. Click "Create Web Service"
2. Render will build and deploy your application
3. Wait for the build to complete

## Troubleshooting

### Database Connection Failed

If you see "Database connection failed!" errors:

1. **Check DB_SSLMODE**: Make sure `DB_SSLMODE=require` is set
2. **Check Database URL**: Ensure all database environment variables are correct
3. **Check Database Status**: Verify your PostgreSQL database is running
4. **Internal vs External URL**: Render databases have an internal URL that should be used within Render

### Port Binding Issues

The app should automatically bind to the `PORT` environment variable that Render provides. If you see port issues:

1. Verify the Dockerfile exposes port 8000
2. Check that gunicorn is being used (not runserver)
3. Ensure `PORT` environment variable is accessible

### Static Files Not Loading

1. The entrypoint script runs `collectstatic` automatically
2. Make sure `STATIC_ROOT` is set correctly in settings
3. Consider using a CDN or static file storage service for production

## Notes

- The entrypoint script automatically:
  - Waits for database to be ready
  - Runs migrations
  - Collects static files
  - Starts gunicorn with appropriate workers

- Render sets `PORT` automatically, no need to configure it manually
- For production, always use `DJANGO_SETTINGS_MODULE=xcellar.settings.production`
- SSL is required for Render's PostgreSQL databases

