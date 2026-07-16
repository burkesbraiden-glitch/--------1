PALACE_DESTINATIONS = {"故宫", "故宫博物院"}

PALACE_GUIDE = {
    "child_intro": [
        "故宫以前是皇帝和家人生活、工作的地方。",
        "屋顶、宫门和台阶里藏着很多古代礼仪。",
        "今天不用记很多名字，认真观察就很好。",
    ],
    "questions": [
        "你觉得这么大的宫殿是谁住的？",
        "你发现屋顶上有什么特别的东西？",
        "为什么这里很多地方都是红色和黄色？",
    ],
    "focus_items": ["屋顶", "宫门", "颜色"],
    "audio_url": None,
}


def normalize_destination(destination):
    if not isinstance(destination, str):
        return ""
    return "".join(destination.split())


def is_palace_destination(destination):
    normalized = normalize_destination(destination)
    return normalized in PALACE_DESTINATIONS


def copy_guide(template):
    return {
        "child_intro": list(template["child_intro"]),
        "questions": list(template["questions"]),
        "focus_items": list(template["focus_items"]),
        "audio_url": template["audio_url"],
    }


def first_interest(plan):
    interests = plan.interests if isinstance(plan.interests, list) else []
    for interest in interests:
        if isinstance(interest, str) and interest.strip():
            return interest.strip()
    return "孩子感兴趣的细节"


def generate_fallback_content(plan):
    destination = plan.destination.strip() if isinstance(plan.destination, str) else "这个地方"
    age_group = plan.age_group if isinstance(plan.age_group, str) else "7-12"
    interest = first_interest(plan)

    return {
        "child_intro": [
            f"{destination}是一个适合亲子一起慢慢观察的地方。",
            f"今天可以从{interest}开始看，把看到的细节说出来。",
            f"如果孩子暂时不知道答案，也可以先猜一猜，再一起寻找线索。",
        ],
        "questions": [
            f"你觉得{destination}里最先吸引你的是什么？",
            f"这里有没有和你平时生活不一样的地方？",
        ],
        "focus_items": [destination, interest, f"{age_group}岁孩子的发现"],
        "audio_url": None,
    }


def generate_guide_content(plan):
    if is_palace_destination(plan.destination):
        return copy_guide(PALACE_GUIDE)
    return generate_fallback_content(plan)
