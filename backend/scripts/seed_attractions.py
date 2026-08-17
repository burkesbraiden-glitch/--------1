from app import create_app
from app.extensions import db
from app.models import Attraction, AttractionGuide


BEIJING_ATTRACTIONS = [
    {
        "name": "故宫博物院",
        "city": "北京",
        "district": "东城区",
        "address": None,
        "summary": "在宏大的宫殿建筑里，和孩子一起观察颜色、屋顶和古代礼仪。",
        "tags": ["历史", "古建筑"],
        "recommended_duration_minutes": 180,
        "cover_image": None,
        "guide": {
            "overview": "把故宫当成一座可以阅读的古代城市，从门、殿和屋顶寻找线索。",
            "highlights": ["屋顶小兽", "红墙黄瓦", "中轴线"],
            "visit_tips": ["优先选择一条清晰参观路线", "为观察和休息预留时间"],
            "family_tips": ["请孩子挑选一处建筑细节，画下来或说出自己的发现"],
        },
    },
    {
        "name": "景山公园",
        "city": "北京",
        "district": "西城区",
        "address": None,
        "summary": "在山顶眺望北京中轴线，用不同高度认识城市的空间。",
        "tags": ["园林", "城市观察"],
        "recommended_duration_minutes": 90,
        "cover_image": None,
        "guide": {
            "overview": "从登山和眺望开始，让孩子把宫殿、树木和城市方向连成一幅图。",
            "highlights": ["万春亭", "中轴线视野", "山林步道"],
            "visit_tips": ["根据孩子体力安排登山节奏", "在视野开阔处停下来辨认方向"],
            "family_tips": ["邀请孩子指出最想去观察的建筑或颜色"],
        },
    },
    {
        "name": "中国国家博物馆",
        "city": "北京",
        "district": "东城区",
        "address": None,
        "summary": "通过器物、图像和时间线，和孩子讨论文明如何被保存与讲述。",
        "tags": ["博物馆", "文物"],
        "recommended_duration_minutes": 180,
        "cover_image": None,
        "guide": {
            "overview": "不用追求看完所有展厅，选择少量文物认真比较形状、用途和故事。",
            "highlights": ["时间线", "器物纹样", "历史故事"],
            "visit_tips": ["先选一个主题再进入展厅", "观展中安排短暂休息"],
            "family_tips": ["让孩子选一件最想带回家的文物，并说明理由"],
        },
    },
    {
        "name": "天坛公园",
        "city": "北京",
        "district": "东城区",
        "address": None,
        "summary": "在祭祀建筑与古树之间，观察圆与方、声音与空间的关系。",
        "tags": ["古建筑", "园林"],
        "recommended_duration_minutes": 150,
        "cover_image": None,
        "guide": {
            "overview": "从建筑形状和步行路线出发，认识古人对天地与秩序的想象。",
            "highlights": ["祈年殿", "圜丘", "古柏"],
            "visit_tips": ["把一段步行留给慢慢观察建筑比例", "选择安静位置感受空间回声"],
            "family_tips": ["和孩子一起寻找圆形与方形的设计，并猜猜它们的含义"],
        },
    },
    {
        "name": "颐和园",
        "city": "北京",
        "district": "海淀区",
        "address": None,
        "summary": "在山水园林中观察借景、长廊和彩绘，感受人与自然的设计。",
        "tags": ["园林", "山水"],
        "recommended_duration_minutes": 180,
        "cover_image": None,
        "guide": {
            "overview": "沿着水边和长廊慢慢走，比较远景、近景和不同空间的感受。",
            "highlights": ["昆明湖", "长廊", "万寿山"],
            "visit_tips": ["选择一段重点区域深入游览", "遇到拥挤时改为观察湖面或彩绘"],
            "family_tips": ["请孩子找一幅最喜欢的彩绘，并编一个小故事"],
        },
    },
    {
        "name": "北海公园",
        "city": "北京",
        "district": "西城区",
        "address": None,
        "summary": "在湖岛、白塔和古典园林中，体验水面如何改变一座园子的风景。",
        "tags": ["园林", "湖泊"],
        "recommended_duration_minutes": 120,
        "cover_image": None,
        "guide": {
            "overview": "以湖水为线索，把岛、塔、桥和树的倒影连成一次轻松探索。",
            "highlights": ["白塔", "琼华岛", "湖岸景观"],
            "visit_tips": ["沿湖选择短路线，避免赶行程", "留意水面与建筑的倒影变化"],
            "family_tips": ["让孩子用三个词形容看到的湖面，并解释选择"],
        },
    },
    {
        "name": "恭王府博物馆",
        "city": "北京",
        "district": "西城区",
        "address": None,
        "summary": "在府邸和花园里比较居住空间、装饰细节与传统生活方式。",
        "tags": ["古建筑", "园林"],
        "recommended_duration_minutes": 120,
        "cover_image": None,
        "guide": {
            "overview": "从一扇门、一个院落或一块装饰开始，想象古代家庭怎样使用这些空间。",
            "highlights": ["府邸院落", "花园假山", "装饰纹样"],
            "visit_tips": ["选择少数院落细看，不必追求全部走遍", "尊重展览区域的参观提示"],
            "family_tips": ["和孩子比较这里的房间与今天家庭空间有什么不同"],
        },
    },
    {
        "name": "孔庙和国子监博物馆",
        "city": "北京",
        "district": "东城区",
        "address": None,
        "summary": "从碑刻、院落和学习空间出发，认识古代教育与尊师重学的传统。",
        "tags": ["教育", "历史"],
        "recommended_duration_minutes": 120,
        "cover_image": None,
        "guide": {
            "overview": "沿着院落和碑刻寻找学习的痕迹，讨论古今课堂有哪些相同与不同。",
            "highlights": ["大成殿", "碑刻", "辟雍"],
            "visit_tips": ["放慢脚步阅读少量碑刻和说明", "把问题留给孩子先观察再回答"],
            "family_tips": ["请孩子想象一堂古代课，并说出最想问老师的问题"],
        },
    },
]


def _next_id(model):
    if db.engine.dialect.name != "sqlite":
        return None
    return (db.session.query(db.func.max(model.id)).scalar() or 0) + 1


def seed_attractions():
    created_attractions = 0
    created_guides = 0

    for data in BEIJING_ATTRACTIONS:
        attraction = Attraction.query.filter_by(city=data["city"], name=data["name"]).first()
        if attraction is None:
            attraction = Attraction(
                id=_next_id(Attraction),
                name=data["name"],
                city=data["city"],
                district=data["district"],
                address=data["address"],
                summary=data["summary"],
                tags=data["tags"],
                recommended_duration_minutes=data["recommended_duration_minutes"],
                cover_image=data["cover_image"],
            )
            db.session.add(attraction)
            db.session.flush()
            created_attractions += 1

        if attraction.guide is None:
            guide = data["guide"]
            db.session.add(
                AttractionGuide(
                    id=_next_id(AttractionGuide),
                    attraction_id=attraction.id,
                    overview=guide["overview"],
                    highlights=guide["highlights"],
                    visit_tips=guide["visit_tips"],
                    family_tips=guide["family_tips"],
                )
            )
            created_guides += 1

    db.session.commit()
    return {"createdAttractions": created_attractions, "createdGuides": created_guides}


def main():
    app = create_app()
    with app.app_context():
        print(seed_attractions())


if __name__ == "__main__":
    main()
