"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularRedocView, SpectacularAPIView
from rest_framework.authentication import SessionAuthentication
from config.permissions import IsSuperUser
from config.views.stripe_webhook import StripeWebhookView

urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/cloud/", include("apps.cloud_storage.urls")),
    path("api/payments/", include("apps.payments.urls")),
    path("api/subscriptions/", include("apps.subscriptions.urls")),
    path("api/users/", include("apps.users.urls")),
    path("api/stripe/webhook/", StripeWebhookView.as_view(), name="stripe-webhook"),
]

# Add documentation URLs with superuser restriction
urlpatterns += [
    path("api/schema/", SpectacularAPIView.as_view(permission_classes=[IsSuperUser]), name="schema"),
    path("api/docs/redoc/", SpectacularRedocView.as_view(url_name="schema", authentication_classes=[SessionAuthentication], permission_classes=[IsSuperUser]), name="redoc"),
]
