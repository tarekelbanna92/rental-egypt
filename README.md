# Rental Egypt — Django + Heroku

## Local Setup

```bash
python -m venv .venv && source .venv/bin/activate  # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser  # create admin
python manage.py runserver
```

Visit http://127.0.0.1:8000

## Deploy to Heroku (Postgres)

```bash
heroku login
heroku create rentalegypt-mvp-<your-initials>
heroku buildpacks:set heroku/python
heroku addons:create heroku-postgresql:mini

# Set production env vars (adjust your domain names)
heroku config:set \
  DEBUG=0 \
  SECRET_KEY="$(python - <<'PY'
import secrets; print(secrets.token_urlsafe(50))
PY)" \
  ALLOWED_HOSTS=".herokuapp.com,www.rentalegypt.com,rentalegypt.com" \
  CSRF_TRUSTED_ORIGINS="https://*.herokuapp.com,https://www.rentalegypt.com,https://rentalegypt.com"

# Deploy
git init
heroku git:remote -a rentalegypt-mvp-<your-initials>
git add . && git commit -m "Initial Rental Egypt MVP"
git branch -M main
git push heroku main

# DB + static
heroku run python manage.py migrate
heroku run python manage.py createsuperuser
heroku run python manage.py collectstatic --noinput
```

### Connect your custom domain
```bash
# Add domain(s)
heroku domains:add www.rentalegypt.com
heroku domains:add rentalegypt.com

# Heroku will output DNS targets. In your DNS provider:
#  - Set CNAME for www -> the Heroku DNS Target
#  - Use ALIAS/ANAME (or root flattening) for apex rentalegypt.com -> the same target
# If ALIAS/ANAME isn't supported, point root to www using your DNS provider's URL redirect.
```
# rental-egypt
