PALACE_DESTINATIONS = {"故宫", "故宫博物院"}


PALACE_TASKS = [
    {
        "sort_order": 1,
        "title": "找屋顶上的小兽",
        "subtitle": "在屋顶上找一找那些小兽",
        "duration": "约10分钟",
        "task_type": "观察任务",
        "summary": "故宫屋顶上有一排可爱又神秘的小兽，快和孩子一起找一找吧！",
        "objective": "找到屋顶小兽，观察它们的排列",
        "steps": ["抬头看看屋檐边缘", "数一数有几只", "留意最大的那一只在哪里"],
        "questions": ["为什么它们站在屋顶上？", "你觉得它们在守护什么？"],
        "record_mode": "拍照片，或说出你最喜欢的一只并写下来。",
        "theme": "beasts",
    },
    {
        "sort_order": 2,
        "title": "拍一扇宫门",
        "subtitle": "找到一扇喜欢的宫门并拍下来",
        "duration": "约8分钟",
        "task_type": "拍照任务",
        "summary": "故宫里有很多高高的宫门，红色门板和金色门钉藏着好看的细节。",
        "objective": "找到一扇喜欢的宫门，观察门上的颜色和纹样",
        "steps": ["站远一点看整体", "走近观察门钉、门环和门框上的颜色"],
        "questions": ["这扇门为什么这么高？", "门上的圆点像什么？"],
        "record_mode": "拍下宫门照片，写一句你发现的细节。",
        "theme": "gate",
    },
    {
        "sort_order": 3,
        "title": "讲一个故事",
        "subtitle": "说说你看到的一个角落",
        "duration": "约12分钟",
        "task_type": "表达任务",
        "summary": "选一个你喜欢的角落，用自己的话讲一个发生在故宫里的小故事。",
        "objective": "用观察到的细节讲出一个短故事",
        "steps": ["先选一个角落", "说出那里有什么", "想一想谁可能来过、发生了什么"],
        "questions": ["如果你是这里的小主人，今天会邀请谁来做客？"],
        "record_mode": "录下想法或写下故事开头，也可以配一张照片。",
        "theme": "story",
    },
]


def normalize_destination(destination):
    return (destination or "").strip()


def normalize_interests_text(interests):
    if not isinstance(interests, list):
        return "喜欢的事物"
    normalized = [str(item).strip() for item in interests if str(item).strip()]
    return "、".join(normalized) if normalized else "喜欢的事物"


def with_age_group(task, age_group):
    copied = dict(task)
    copied["age_group"] = age_group
    return copied


def palace_tasks(age_group):
    return [with_age_group(task, age_group) for task in PALACE_TASKS]


def fallback_tasks(destination, age_group, interests):
    interests_text = normalize_interests_text(interests)
    return [
        {
            "sort_order": 1,
            "title": "发现一个代表细节",
            "subtitle": f"在{destination}找到一个最吸引你的细节",
            "age_group": age_group,
            "duration": "约10分钟",
            "task_type": "观察任务",
            "summary": f"和孩子一起在{destination}慢慢看，选出一个能代表这里的小细节。",
            "objective": f"观察{destination}的代表性细节，并说出它特别在哪里",
            "steps": ["先环顾四周", "选择一个最想靠近看的细节", "说出它的形状、位置或用途"],
            "questions": [f"这个细节为什么会出现在{destination}？", "如果把它画下来，你会先画哪一部分？"],
            "record_mode": "拍下细节照片，写一句你发现的特别之处。",
            "theme": "detail",
        },
        {
            "sort_order": 2,
            "title": "寻找颜色和形状",
            "subtitle": f"找一找{destination}里的颜色、形状或建筑特征",
            "age_group": age_group,
            "duration": "约8分钟",
            "task_type": "寻找任务",
            "summary": f"{destination}里藏着许多颜色和形状线索，可以和孩子一起像侦探一样寻找。",
            "objective": f"结合{interests_text}，找到至少一种颜色、形状或空间特征",
            "steps": ["先找一种最明显的颜色", "再找一个重复出现的形状", "说说它们让你想到什么"],
            "questions": [f"你能在{destination}找到和{interests_text}有关的线索吗？", "这些颜色和形状让这里看起来更安静、热闹，还是神秘？"],
            "record_mode": "拍一张颜色或形状照片，写下它像什么。",
            "theme": "shape",
        },
        {
            "sort_order": 3,
            "title": "说出今天的发现",
            "subtitle": "把观察到的内容讲给家人听",
            "age_group": age_group,
            "duration": "约12分钟",
            "task_type": "表达任务",
            "summary": f"离开{destination}前，邀请孩子用自己的话讲出今天最想记住的一件事。",
            "objective": "把观察、感受和想象整理成一段亲子表达",
            "steps": ["选一个最难忘的发现", "说出它在哪里", "补充一句自己的感受或想象"],
            "questions": ["今天哪一个发现最值得放进探索相册？", "下次再来，你还想继续找什么？"],
            "record_mode": "写下发现，也可以配一张照片作为探索相册素材。",
            "theme": "expression",
        },
    ]


def generate_task_definitions(plan):
    destination = normalize_destination(plan.destination)
    if destination in PALACE_DESTINATIONS:
        return palace_tasks(plan.age_group)
    return fallback_tasks(destination, plan.age_group, plan.interests or [])
