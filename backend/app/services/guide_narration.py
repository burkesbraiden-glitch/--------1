import hashlib
import json


class NarrationError(Exception):
    def __init__(self, code, message):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def _clean_text_list(value):
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def build_narration_text(*, plan, guide):
    destination = plan.destination.strip() if isinstance(getattr(plan, "destination", None), str) else ""
    child_intro = _clean_text_list(getattr(guide, "child_intro", None))
    questions = _clean_text_list(getattr(guide, "questions", None))
    focus_items = _clean_text_list(getattr(guide, "focus_items", None))

    if not destination or not child_intro:
        raise NarrationError(
            "NARRATION_CONTENT_INSUFFICIENT",
            "Guide content is insufficient for narration",
        )

    parts = [f"我们现在来到{destination}。", "和孩子一起慢慢看看这里藏着的细节吧。"]
    parts.extend(child_intro)

    if focus_items:
        parts.append(f"接下来可以特别留意{'、'.join(focus_items)}。")
    if questions:
        parts.append(f"你可以问问孩子：{questions[0]}")
    parts.append("不用急着找到答案，先把看到的细节说出来，也是一种很棒的发现。")
    return "".join(parts)


def build_audio_source_hash(
    *,
    narration_text,
    language,
    voice_profile_id,
    tts_config_version,
    output_format,
):
    payload = {
        "language": language,
        "narrationText": narration_text,
        "outputFormat": output_format,
        "ttsConfigVersion": tts_config_version,
        "voiceProfileId": voice_profile_id,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
