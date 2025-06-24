RESPONSE_SCHEMA_GET_PRESIGNED_URL = {
    "type": "object",
    "properties": {
        "presigned_url": {"type": "string", "format": "url", "example": "https://s3.amazonaws.com/..."},
        "id": {"type": "integer", "example": 1},
        "file_name": {"type": "string", "example": "example.jpg"},
        "path": {"type": "string", "example": "somefolder/test.png"},
        "size": {"type": "integer", "format": "bytes", "example": 204800},
        "content_type": {"type": "string", "example": "image/jpeg"},
        "created_at": {"type": "datetime"},
    },
}
