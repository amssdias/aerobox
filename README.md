[![🔍 Validate Code and Migrations](https://github.com/amssdias/aerobox/actions/workflows/django-ci.yml/badge.svg?branch=master&event=push)](https://github.com/amssdias/aerobox/actions/workflows/django-ci.yml)

[![Django](https://img.shields.io/badge/Django-4.2-092E20?style=for-the-badge&logo=django)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.15-E83E3E?style=for-the-badge&logo=django)](https://www.django-rest-framework.org/)

[![Celery](https://img.shields.io/badge/Celery-4caf50?logo=celery&logoColor=white)](https://docs.celeryproject.org/)
![Django Translations](https://img.shields.io/badge/Django--Translations-i18n-important?logo=django&color=092E20)

![Python Badge](https://img.shields.io/badge/Python-3.9-blue?logo=python)
[![Docker](https://badgen.net/badge/icon/docker?icon=docker&label)](https://https://docker.com/)
![AWS S3](https://img.shields.io/badge/AWS_S3-FF9900?style=flat&logo=amazon-aws&logoColor=white)
[![Stripe](https://img.shields.io/badge/Stripe-6772E5?style=flat&logo=stripe&logoColor=white)](https://stripe.com/)


# Aerobox

Aerobox is a Django application powered by Django REST Framework (DRF) that allows users to securely log in and store files in the cloud. It provides robust endpoints for authentication and file management, designed for simplicity and efficiency.

## 🎯 Purpose

This project was built to explore scalable SaaS architecture patterns including:

- Modular app design
- Stripe webhook handling
- Feature-based plan configuration
- S3 storage abstraction
- Background task orchestration

## 🚀 Features

- Secure file uploads to AWS S3 (presigned URLs)
- Folder hierarchy with nested structure
- Share links with expiration and password protection
- Subscription plans with Stripe integration
- Storage limits per plan
- Soft delete & restore functionality
- Role-based feature configuration
- Full test coverage with CI pipeline

## 🏗 Architecture

- **Backend:** Django + Django REST Framework
- **Storage:** AWS S3
- **Background tasks:** Celery + Redis
- **Payments:** Stripe Webhooks
- **Database:** PostgreSQL
- **Testing:** Django TestCase + coverage
- **CI/CD:** GitHub Actions

![Aerobox Architecture](docs/images/architecture.png)

### 🏗️ Installation

[Check here how to install](https://github.com/amssdias/aerobox/wiki/Installation-&-Setup)
