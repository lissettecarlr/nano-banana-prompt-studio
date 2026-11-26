"""图片生成适配层。渠道 SDK 只在真正生成时才导入。"""

from nano_banana.core.images.registry import (
    ProviderRegistry,
    UnknownProviderError,
    default_registry,
)
from nano_banana.core.images.types import (
    ImageBackend,
    ImageGenerationError,
    ImageRequest,
    ImageResult,
    OptionSpec,
    ProviderCredentials,
    ProviderSpec,
)

__all__ = [
    "ImageBackend",
    "ImageGenerationError",
    "ImageRequest",
    "ImageResult",
    "OptionSpec",
    "ProviderCredentials",
    "ProviderRegistry",
    "ProviderSpec",
    "UnknownProviderError",
    "default_registry",
]
