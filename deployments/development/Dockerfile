FROM python:3.9-slim-bullseye

# Install PostgreSQL client and development libraries
RUN apt-get update && apt-get install -y \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

RUN pip install pipenv

# Copy the Pipfile and Pipfile.lock
COPY Pipfile Pipfile.lock ./

# Install all packages (including development packages) system-wide
RUN pipenv install --dev --system

# Copy app
COPY . .

ENV DJANGO_SETTINGS_MODULE=config.settings.settings_development

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
