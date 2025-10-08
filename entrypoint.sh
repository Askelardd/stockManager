#!/usr/bin/env bash
set -e

# Espera curta pela DB (compose já faz healthcheck, isto é extra)
if [ -n "$DATABASE_URL" ]; then
  echo "A aguardar DB..."
  for i in {1..30}; do
    python - <<'PY'
import os, sys, psycopg
from urllib.parse import urlparse
url = os.environ.get("DATABASE_URL")
if not url: sys.exit(0)
u = urlparse(url)
try:
  psycopg.connect(host=u.hostname, port=u.port or 5432, user=u.username, password=u.password, dbname=u.path.lstrip('/')).close()
  sys.exit(0)
except Exception as e:
  sys.exit(1)
PY
    ok=$?
    [ $ok -eq 0 ] && break
    sleep 1
  done
fi

python manage.py collectstatic --noinput
python manage.py migrate --noinput

# Lança Gunicorn
exec gunicorn ${DJANGO_WSGI_MODULE:-stockManager.wsgi}:application \
  --bind 0.0.0.0:8000 \
  --workers ${GUNICORN_WORKERS:-3} \
  --timeout ${GUNICORN_TIMEOUT:-60}
