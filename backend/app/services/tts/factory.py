from app.services.tts.edge_tts_provider import EdgeTTSConfig, EdgeTTSProvider
from app.services.tts_provider import TTSProviderError, UnconfiguredTTSProvider


def _provider_name(config):
    value = config.get("TTS_PROVIDER", "unconfigured")
    return value.strip().casefold() if isinstance(value, str) else "unconfigured"


def create_tts_provider(config):
    provider_name = _provider_name(config)
    if provider_name == "edge":
        return EdgeTTSProvider(
            config=EdgeTTSConfig(
                base_url=config.get("EDGE_TTS_BASE_URL", ""),
                voice=str(config.get("EDGE_TTS_VOICE", "zh-CN-XiaoxiaoNeural")),
                speed=config.get("EDGE_TTS_SPEED", 1.0),
                pitch=str(config.get("EDGE_TTS_PITCH", "0")),
                style=str(config.get("EDGE_TTS_STYLE", "general")),
                timeout_seconds=config.get("EDGE_TTS_TIMEOUT_SECONDS", 30),
            )
        )
    if provider_name in {"fake", "unconfigured", ""}:
        # Tests inject their own provider. This keeps explicit non-production
        # configuration offline and prevents a fabricated audio implementation.
        return UnconfiguredTTSProvider()
    raise TTSProviderError("TTS_PROVIDER_CONFIG_INVALID", "Unsupported TTS provider", retryable=False)
