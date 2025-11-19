# Request schemas will be added here

from services.media.app.schemas.request.MediaGenerateSchema import (
    MediaGenerateSchema,
    MediaType,
)
from services.media.app.schemas.request.QrCodeGenerateSchema import (
    QrCodeGenerateSchema,
)

__all__ = [
    "MediaGenerateSchema",
    "MediaType",
    "QrCodeGenerateSchema",
]

