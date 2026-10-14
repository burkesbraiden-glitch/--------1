"""Stable, server-owned product constants."""


EXPECTED_TASK_COUNT = 3


CHILD_PRIVACY_CONSENT_VERSION = "1.0"

# Persist only stable identifiers; the app maps each identifier to its local
# avatar asset and current visual treatment.
CHILD_AVATAR_PRESETS = (
    "avatar_01",
    "avatar_02",
    "avatar_03",
    "avatar_04",
    "avatar_05",
    "avatar_06",
)
CHILD_AVATAR_PRESET_KEYS = frozenset(CHILD_AVATAR_PRESETS)
