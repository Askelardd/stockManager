FROM python:3.12-slim

# Dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependências Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiar projeto
COPY . /app/

# Criar utilizador não-root
RUN useradd -ms /bin/bash appuser
USER appuser

EXPOSE 8000

# Comando de arranque
CMD bash -c "python manage.py migrate && \
             python manage.py collectstatic --noinput && \
             gunicorn stockManager.wsgi:application --bind 0.0.0.0:8000 --workers 3"
