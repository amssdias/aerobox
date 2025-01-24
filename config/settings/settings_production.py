from .base import *

DEBUG = False

# ====== Security for HTTPS Enforcement ======
# - SECURE_SSL_REDIRECT: Redirects all HTTP traffic to HTTPS, ensuring encrypted connections across the site.
# - SECURE_HSTS_SECONDS: Instructs browsers to remember to only connect to the site over HTTPS for the specified duration (1 year in seconds).
# - SECURE_HSTS_PRELOAD: Signals the site's readiness for inclusion in browser preload lists, enforcing HTTPS globally without needing an initial visit.
# - SECURE_HSTS_INCLUDE_SUBDOMAINS: Extends the HTTPS requirement to all subdomains, ensuring they also enforce HTTPS.
SECURE_SSL_REDIRECT = False # Use NGINX as reverse proxy
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_PRELOAD = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# ====== Cookie Security Settings ======
# - CSRF_COOKIE_SECURE: Ensures the CSRF cookie is only sent over HTTPS, protecting it from exposure over unencrypted connections.
# - SESSION_COOKIE_SECURE: Marks session cookies as HTTPS-only, preventing them from being sent over unsecured HTTP connections.
# - CSRF_TRUSTED_ORIGINS: Specifies trusted origins for cross-origin requests with CSRF protection.
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")

# ====== Header Security Settings ======
# - SECURE_BROWSER_XSS_FILTER: Enables the X-XSS-Protection header in compatible browsers to help prevent cross-site scripting (XSS) attacks.
# - SECURE_CONTENT_TYPE_NOSNIFF: Adds the X-Content-Type-Options header to prevent browsers from trying to guess the content type, reducing exposure to certain attack vectors.
# - X_FRAME_OPTIONS: Sets the X-Frame-Options header to "DENY", blocking the site from being embedded in iframes and protecting against clickjacking attacks.
# - SECURE_REFERRER_POLICY: Limits the referrer information sent in requests to the same origin only, reducing the potential for sensitive information leakage.
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
