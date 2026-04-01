# Deployment Checklist

## Before Deployment:
- [ ] Update ALLOWED_HOSTS in settings.py
- [ ] Set DJANGO_ENV=production 
- [ ] Set your GEMINI_API_KEY
- [ ] Run `python manage.py collectstatic`
- [ ] Run `python manage.py migrate`
- [ ] Test all functionality locally

## Environment Variables to Set:
- SECRET_KEY
- DJANGO_ENV=production
- GEMINI_API_KEY
- DATABASE_URL 

## Render Dashboard Settings
- **Start Command**: `gunicorn prodvi_project.wsgi:application --workers 1 --timeout 120`
- **Recommended Plan**: Starter (or any tier with >= 500MB RAM)
