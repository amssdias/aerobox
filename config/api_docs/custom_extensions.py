from drf_spectacular.utils import extend_schema, OpenApiParameter

def api_users_tag():
    return extend_schema(tags=["API - Users"])
