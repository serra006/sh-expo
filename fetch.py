# -*- coding: utf-8 -*-
"""上海展会信息抓取器
数据源:
  1. 国家会展中心(上海) NECC  - 展览排期 / 活动排期 / 会议排期, 分页 pageNo
  2. 上海新国际博览中心 SNIEC - 按月展会日历
产出: data/events.json
"""
import difflib
import json
import os
import re
import time
import hashlib
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup

try:
    import urllib3
    urllib3.disable_warnings()
except Exception:
    pass

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, "raw")
DATA = os.path.join(BASE, "data")
os.makedirs(RAW, exist_ok=True)
os.makedirs(DATA, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
TIMEOUT = 30
PAUSE = 0.4

NECC_BASE = "https://www.neccsh.com/cecsh/exhibitioninfo/exhibitionlist.jspx?v=1"
SNIEC_BASE = "https://www.sniec.net/cn/visit_exhibition.php?month=%s"

# NECC 三个 tab
NECC_TABS = [
    ("exhibition", "", "展览排期"),
    ("activity", "&channelIdStr=204", "活动排期"),
    ("meeting", "&channelIdStr=229", "会议排期"),
]

CATEGORY_RULES = [
    ("汽车交通", ["汽车", "车展", "汽配", "轮胎", "电动车", "新能源汽车", "轨道交通", "公交",
                  "客车", "车用", "商用车", "汽保", "改装车", "充电桩", "智能网联"]),
    ("工业制造", ["工业", "机械", "机床", "自动化", "机器人", "工业门", "轴承", "铸造", "锻造",
                  "焊接", "模具", "五金", "泵", "阀", "压缩机", "传动", "动力传动", "冶金",
                  "钢铁", "金属", "管材", "线缆", "紧固件", "3D打印", "包装", "工厂", "洁净",
                  "蒸发", "结晶", "精馏", "发泡", "零部件", "加工"]),
    ("电子信息", ["电子", "半导体", "集成电路", "光电", "显示", "连接器", "传感器", "通信",
                  "数据中心", "云计算", "物联网", "算力", "芯片", "PCB", "线束"]),
    ("科技互联网", ["人工智能", "AI", "智能", "科技", "互联网", "数字经济", "元宇宙", "区块链",
                    "软件", "信息", "未来", "创新", "无人", "低空", "航天"]),
    ("医疗健康", ["医疗", "医药", "口腔", "器械", "健康", "康复", "养老", "生物", "制药",
                  "诊断", "医院", "护理", "中药", "营养保健", "生化", "分析测试"]),
    ("能源环保", ["能源", "光伏", "储能", "氢能", "电池", "电力", "环保", "水处理", "节能",
                  "碳中和", "风电", "石油", "化工", "新材料", "锂电", "热能", "燃烧",
                  "焚烧", "固废", "废弃物", "资源利用", "热管理", "发电", "液冷"]),
    ("食品饮料", ["食品", "饮料", "酒", "茶", "咖啡", "烘焙", "餐饮", "糖", "冰激凌",
                  "乳", "肉", "果蔬", "调味", "食品配料"]),
    ("纺织服装", ["纺织", "服装", "面料", "纱线", "鞋", "箱包", "皮革", "家纺", "服饰"]),
    ("家居建材", ["家居", "家具", "建材", "门窗", "卫浴", "陶瓷", "地板", "照明", "灯饰",
                  "装饰", "厨房", "家电", "空调", "暖通"]),
    ("文化创意", ["文创", "文化", "艺术", "设计", "出版", "图书", "影视", "音乐", "印刷",
                  "广告", "标识", "婚礼", "婚庆", "珠宝", "首饰", "礼品"]),
    ("动漫游戏", ["动漫", "游戏", "漫画", "二次元", "电玩", "WEPLAY", "ChinaJoy", "IP展",
                  "潮玩", "手办"]),
    ("消费零售", ["零售", "连锁", "加盟", "自有品牌", "电商", "消费品", "宠物", "母婴",
                  "美妆", "日化", "清洁", "酒店", "餐饮连锁"]),
    ("农林牧渔", ["农业", "农产品", "园林", "花卉", "渔业", "畜牧", "林业", "灌溉"]),
    ("教育人才", ["教育", "人才", "培训", "留学", "招聘", "技能", "职业"]),
    ("建筑地产", ["建筑", "地产", "城", "工程", "钢结构", "混凝土", "石膏", "保温", "防水"]),
]


def guess_category(name):
    for cat, kws in CATEGORY_RULES:
        for kw in kws:
            if kw.lower() in name.lower():
                return cat
    return "综合其他"


# 主题标签: 跨类目的细分热点, 一场展会可命中多个
TOPIC_RULES = [
    ("AI", ["人工智能", "AI", "大模型", "智能体", "生成式", "机器学习", "深度学习",
            "AIGC", "脑机", "算法", "具身"]),
    ("机器人", ["机器人", "人形", "机械臂", "自动化产线"]),
    ("算力", ["算力", "数据中心", "液冷", "超节点", "云计算", "服务器", "边缘计算"]),
    ("半导体", ["半导体", "集成电路", "芯片", "光通信", "元器件", "光电", "传感器",
                "封装", "晶圆"]),
    ("新能源", ["储能", "氢能", "光伏", "锂电", "电池", "风电", "新能源", "碳中和",
                "充电桩", "能源"]),
    ("汽车", ["汽车", "车展", "汽配", "智能网联", "自动驾驶", "车用", "整车", "底盘"]),
    ("低空经济", ["低空", "无人机", "eVTOL", "通用航空", "飞行器"]),
    ("医疗健康", ["医疗", "医药", "器械", "生物", "诊断", "健康", "养老", "康复",
                  "口腔", "制药"]),
    ("宠物", ["宠物", "爬宠", "水族", "龟"]),
    ("动漫游戏", ["动漫", "游戏", "二次元", "潮玩", "手办", "电竞", "数字娱乐",
                  "IP"]),
    ("食品饮料", ["食品", "饮料", "茶业", "咖啡", "酒", "烘焙", "餐饮", "乳"]),
    ("家居建材", ["家居", "家具", "建材", "家电", "门窗", "卫浴", "照明", "暖通",
                  "采暖"]),
    ("时尚纺织", ["服装", "纺织", "珠宝", "时尚", "服饰", "面料", "箱包"]),
    ("文创艺术", ["艺术", "文创", "设计", "书展", "出版", "文化", "礼品"]),
    ("出海跨境", ["出海", "跨境", "电商", "外贸", "海外", "自有品牌"]),
]

# 知名度规则: (关键词, 短标签) —— 命中即视为重磅大展
FEATURED_RULES = [
    ("进口博览会", "国家级"),
    ("中国国际工业博览会", "国家级"),
    ("世界技能大赛", "国际赛事"),
    ("世界人工智能大会", "全球顶级"),
    ("外滩大会", "全球顶级"),
    ("数码互动娱乐", "亚洲最大"),
    ("ChinaJoy", "亚洲最大"),
    ("工程机械", "亚洲最大"),
    ("纺织机械", "全球旗舰"),
    ("家具博览会", "全球最大"),
    ("汽车配件", "全球最大"),
    ("Automechanika", "全球最大"),
    ("环球食品展", "亚太最大"),
    ("FHC", "亚太最大"),
    ("物流技术与运输", "亚洲旗舰"),
    ("电力设备及技术", "亚洲旗舰"),
    ("慕尼黑", "国际顶级"),
    ("分析生化", "国际顶级"),
    ("汽车工业展览会", "国际 A 级"),
    ("童书展", "亚太最大"),
    ("廿一当代艺术", "国内顶级"),
    ("设计周", "国际顶级"),
    ("轴承", "全球旗舰"),
    ("模具", "亚洲旗舰"),
    ("半导体", "国内旗舰"),
]


def guess_topics(name):
    t = name.lower()
    out = []
    for topic, kws in TOPIC_RULES:
        for kw in kws:
            if kw.lower() in t:
                out.append(topic)
                break
    return out


def featured_of(name, organizer=""):
    for kw, label in FEATURED_RULES:
        if kw.lower() in name.lower():
            return True, label
    if organizer and ("中华人民共和国" in organizer or "商务部" in organizer
                      or "工业和信息化部" in organizer):
        return True, "部委主办"
    return False, ""


def make_id(source, name, start):
    raw = "%s|%s|%s" % (source, name.strip(), start)
    return source + "-" + hashlib.md5(raw.encode("utf-8")).hexdigest()[:10]


# ---------------- 参加办法 ----------------
# level: trade=限专业观众/需审核  public=普通观众可进
# verified: True 表示有主办方官方公告依据，False 为行业惯例推断
# channels: 多通道报名。每通道独立标注开放与截止，避免"一条说明概括全部"造成误导
#   state: closed=已结束  open=开放中  soon=未开始  空=按日期推算/以公告为准
def _ch(name, who, where, window, steps="", note="", deadline="", state=""):
    return dict(name=name, who=who, where=where, window=window, steps=steps,
                note=note, deadline=deadline, state=state)


CIIE_CHANNELS = [
    _ch("专业观众注册", "企业、机构、商协会人员",
        "微信小程序「中国国际进口博览会」",
        "9 月上旬开放，10 月 20 日截止",
        steps="我的 → 专业观众注册（官网 ciie.org、官方 APP 同入口）",
        note="需提交单位资质材料，由交易商协会/交易团审核；审核通过才发证，持证才能进场",
        deadline="2026-10-20", state="closed"),
    _ch("普通观众（社会观众）预约", "个人观众",
        "微信小程序「中国国际进口博览会」",
        "9 月初开放预约，9 月内就约满关闭",
        steps="首页 → 观众预约（社会观众）",
        note="社会观众名额很少，开放后很快被约满；今年 9 月就已结束，不能补约，现场也不受理",
        state="closed"),
]

ADMISSION_RULES = [
    # 进博会：不卖票，两条通道都在 9 月开放、早已关闭
    (["进口博览会"], dict(
        level="trade", kind="需提前注册",
        summary="两条通道都已关闭，现在无法再申请。只有已通过审核、持证的专业观众能进场，现场不售票也不办证。",
        how="不卖票，只能提前注册；专业观众与普通观众分两条通道，开通时间都在 9 月，结束得都很早",
        where="微信小程序「中国国际进口博览会」",
        steps="我的 → 专业观众注册（官网 ciie.org 或官方 APP 同路径）",
        deadline="2026-10-20",
        fee="11/6–10 通票 200 元/人 · 11/8–10 100 元 · 单日 50 元",
        channels=CIIE_CHANNELS,
        verified=True)),
    # 工博会：预登记免费
    (["国际工业博览会"], dict(
        level="public", kind="预登记免费",
        summary="免费，但要提前实名预登记，现场凭身份证原件入场。",
        how="提前在线预登记免费，现场凭身份证原件刷闸机入场",
        where="官网或官方公众号「中国国际工业博览会」",
        steps="", deadline="", fee="", verified=True,
        channels=[_ch("观众预登记", "18 岁以上专业观众",
                      "官网或官方公众号「中国国际工业博览会」",
                      "开展前约 2 个月开放，开展前 1–3 天截止",
                      note="预登记免费；未预登记现场可能收门票或无法入场")])),
    # 车展：公众日售票
    (["国际汽车工业展览会", "汽车展览会"], dict(
        level="public", kind="购票入场",
        summary="公众日要买票，专业日需证件；热门日门票会提前售罄。",
        how="分专业日与公众日，公众日需购票；热门日建议提前买",
        where="官方小程序「上海车展」或大麦、猫眼",
        steps="", deadline="", fee="", verified=False,
        channels=[
            _ch("公众日门票", "所有人", "官方小程序「上海车展」或大麦、猫眼",
                "开展前约 1 个月开售，售完即止", note="周末与节假日票最紧张"),
            _ch("专业日证件", "汽车行业从业者", "车展官网 media/trade 入口",
                "开展前 2–3 个月开放申请", note="需单位信息审核，不对普通观众开放")])),
    (["ChinaJoy", "中国国际数码互动娱乐"], dict(
        level="public", kind="购票入场",
        summary="全程售票，热门日与限定周边常提前售罄。",
        how="需购票，热门场次常提前售罄",
        where="官方小程序或大麦、猫眼",
        steps="", deadline="", fee="", verified=False,
        channels=[_ch("门票", "所有人", "官方小程序或大麦、猫眼",
                      "开展前约 1 个月开售", note="周末场通常最先售罄")])),
    # 家博会 / 婚博会这类面向家庭消费的，普遍免费索票
    (["家博会", "家居博览会", "婚博会", "婚庆博览会"], dict(
        level="public", kind="免费索票",
        summary="免费，但要先在官网或公众号索票，现场凭票或身份证入场。",
        how="官网或小程序免费索票，现场凭票或身份证入场",
        where="官网或官方微信公众号",
        steps="", deadline="", fee="", verified=False,
        channels=[_ch("免费索票", "所有人", "官网或官方微信公众号",
                      "开展前 1–2 个月开放索票", note="现场通常也可扫码登记，但排队较久")])),
]

# 消费类展会（要买票）与专业展（免费预登记）的判别
CONSUMER_KEYWORDS = ["动漫", "漫画", "游戏展", "宠物", "潮玩", "玩具", "美食",
                     "吃货", "母婴", "婴童", "婚庆", "婚礼", "家居", "家装"]


def admission_of(name, category="", official_type=""):
    low = name.lower()
    for kws, rule in ADMISSION_RULES:
        for kw in kws:
            if kw.lower() in low:
                return dict(rule)
    # 消费类：一般售票
    if category in ("动漫游戏", "宠物") or any(k in name for k in CONSUMER_KEYWORDS):
        return dict(
            level="public", kind="购票入场",
            summary="面向大众售票，建议提前买，现场可能限流。",
            how="面向大众，需购票入场；建议提前在官方渠道买，现场可能限流",
            where="官方公众号或小程序，也可在大麦、猫眼搜展会名",
            steps="", deadline="", fee="", verified=False,
            channels=[_ch("门票", "所有人", "官方公众号或小程序，也可在大麦、猫眼搜展会名",
                          "开展前 1–2 个月开售", note="热门场次会提前售罄")])
    # 其余按专业展惯例：免费预登记，现场凭身份证
    return dict(
        level="public", kind="预登记免费",
        summary="免费，提前实名预登记最省事；现场凭身份证原件入场。",
        how="专业展惯例：提前在官网或公众号实名预登记可免费入场，现场凭身份证原件核验；未预登记可能需买现场票或无法入场",
        where="展会官网或官方微信公众号（用展会全名搜索）",
        steps="", deadline="", fee="", verified=False,
        channels=[_ch("观众预登记", "行业观众 / 一般观众",
                      "展会官网或官方微信公众号（用展会全名搜索）",
                      "开展前 1–2 个月开放，开展前 1–3 天截止",
                      note="预登记免费；逾期未登记可能需买现场票，热门展甚至会限流不让进")])


def get(url, retry=3):
    last = None
    for i in range(retry):
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            if r.status_code == 200:
                r.encoding = r.apparent_encoding or "utf-8"
                return r.text
            last = "HTTP %s" % r.status_code
        except Exception as e:
            last = repr(e)
        time.sleep(1.5 * (i + 1))
    print("  [FAIL] %s -> %s" % (url, last))
    return ""


def norm_date(s):
    s = s.strip().replace("/", "-").replace(".", "-")
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if not m:
        return None
    return "%s-%02d-%02d" % (m.group(1), int(m.group(2)), int(m.group(3)))


def parse_range(text):
    ds = re.findall(r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}", text)
    if not ds:
        return None, None
    a = norm_date(ds[0])
    b = norm_date(ds[1]) if len(ds) > 1 else a
    return a, b


def status_of(start, end, today=None):
    today = today or date.today().isoformat()
    if not start:
        return "unknown"
    if end and end < today:
        return "finished"
    if start <= today <= (end or start):
        return "ongoing"
    return "upcoming"


# ---------------- NECC ----------------

def parse_necc_table(html):
    soup = BeautifulSoup(html, "html.parser")
    out = []
    table = soup.find("table", class_="layui-table")
    if not table:
        return out
    body = table.find("tbody")
    if not body:
        return out
    for tr in body.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 3:
            continue
        name_el = tds[0].find(class_="exhibit-name")
        name = name_el.get_text(strip=True) if name_el else tds[0].get_text(strip=True)
        if not name:
            continue
        start, end = parse_range(tds[1].get_text(" ", strip=True))
        halls = tds[2].get_text(" ", strip=True).replace(" ", "")
        website = ""
        if len(tds) > 3:
            for a in tds[3].find_all("a"):
                href = (a.get("href") or "").strip()
                if href.startswith("http"):
                    website = href
                    break
        out.append({"name": name, "start": start, "end": end,
                    "halls": halls, "website": website})
    return out


def fetch_necc():
    events = []
    for key, extra, label in NECC_TABS:
        print("[NECC] %s" % label)
        first = get(NECC_BASE + extra)
        if not first:
            continue
        open(os.path.join(RAW, "necc_%s_p1.html" % key), "w", encoding="utf-8").write(first)
        m = re.search(r"var\s+totalPage\s*=\s*(\d+)", first)
        total = int(m.group(1)) if m else 1
        rows = parse_necc_table(first)
        print("  p1 -> %d rows, totalPage=%d" % (len(rows), total))
        for r in rows:
            r["kind"] = label
            events.append(r)
        for p in range(2, total + 1):
            html = get("%s%s&pageNo=%d" % (NECC_BASE, extra, p))
            rows = parse_necc_table(html)
            print("  p%d -> %d rows" % (p, len(rows)))
            if not rows:
                break
            for r in rows:
                r["kind"] = label
                events.append(r)
            time.sleep(PAUSE)
    for e in events:
        e["source"] = "NECC"
        e["venue"] = "国家会展中心（上海）"
        e["venue_short"] = "国展中心"
        e["district"] = "青浦区"
    return events


# ---------------- SNIEC ----------------

def parse_sniec(html):
    soup = BeautifulSoup(html, "html.parser")
    ul = soup.find("ul", id="upcom") or soup.find("ul", class_="visitlist")
    out = []
    if not ul:
        return out
    for li in ul.find_all("li", recursive=False):
        h1 = li.find("h1")
        if not h1:
            continue
        name = h1.get_text(" ", strip=True)
        text = li.get_text("\n", strip=True)
        span = li.find("span")
        span_txt = span.get_text(" ", strip=True) if span else text
        start, end = parse_range(span_txt)
        if not start:
            start, end = parse_range(text)
        organizer = ""
        mo = re.search(r"(?:Organi[sz]er|主办单位|主办方|组织机构)\s*[:：]\s*(.+)", text)
        if mo:
            organizer = mo.group(1).strip()
        website = ""
        for a in li.find_all("a"):
            href = (a.get("href") or "").strip()
            if "www." in href or href.startswith("http"):
                if "sniec.net" not in href:
                    website = href
                    break
        out.append({"name": name, "start": start, "end": end,
                    "organizer": organizer, "website": website,
                    "exhibition_id": str(li.get("rel", "")).strip("[]'\" ")})
    return out


def month_list(start_ym, months):
    y, m = start_ym
    res = []
    for _ in range(months):
        res.append("%04d-%02d" % (y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return res


def fetch_sniec(months=15):
    today = date.today()
    start_y, start_m = (today.year, today.month - 1)
    if start_m < 1:
        start_m = 12
        start_y -= 1
    targets = month_list((start_y, start_m), months + 1)
    events = []
    for ym in targets:
        print("[SNIEC] %s" % ym)
        html = get(SNIEC_BASE % ym)
        if not html:
            continue
        rows = parse_sniec(html)
        print("  -> %d rows" % len(rows))
        for r in rows:
            r["month"] = ym
            events.append(r)
        time.sleep(PAUSE)
    for e in events:
        e["source"] = "SNIEC"
        e["venue"] = "上海新国际博览中心"
        e["venue_short"] = "新国际"
        e["district"] = "浦东新区"
        e["kind"] = "展览排期"
    return events


# ---------------- GOV 上海市会展业公共信息服务平台 ----------------
# 市商务委备案数据, 覆盖全上海所有场馆, 字段含主办单位/展会类型/所属区

GOV_POST = "https://expo.sww.sh.gov.cn/browser/search-entp-index.jspx?code=SEARCH"
GOV_REFER = "https://expo.sww.sh.gov.cn/browser/searchlist.jsp"
GOV_DETAIL = "https://expo.sww.sh.gov.cn/browser/search-entp-expo.jspx?code=%s"

VENUE_FIX = [
    ("新国际博览中心", "上海新国际博览中心", "新国际"),
    ("世博展览馆", "上海世博展览馆", "世博展览馆"),
    ("国家会展中心", "国家会展中心（上海）", "国展中心"),
    ("世贸商城", "上海世贸商城展览馆", "世贸商城"),
    ("上海展览中心", "上海展览中心", "展览中心"),
    ("国际会议中心", "上海国际会议中心", "国际会议中心"),
    ("跨国采购会展中心", "上海跨国采购会展中心", "跨国采购"),
    ("光大会展中心", "上海光大会展中心", "光大"),
    ("汽车会展中心", "上海汽车会展中心", "汽车会展"),
]

VENUES = [
    ("上海新国际博览中心", "新国际", "浦东新区"),
    ("上海世博展览馆", "世博展览馆", "浦东新区"),
    ("国家会展中心（上海）", "国展中心", "青浦区"),
    ("上海世贸商城展览馆", "世贸商城", "长宁区"),
    ("上海展览中心", "展览中心", "静安区"),
    ("上海国际会议中心", "国际会议中心", "浦东新区"),
    ("上海跨国采购会展中心", "跨国采购", "普陀区"),
    ("上海光大会展中心", "光大", "徐汇区"),
]


def split_venue(place):
    """'世博展览馆(浦东新区)' -> ('上海世博展览馆','世博展览馆','浦东新区')"""
    place = re.sub(r"\s+", "", place or "")
    district = ""
    m = re.search(r"[（(]([^）)]*?区)[）)]", place)
    if m:
        district = m.group(1)
        place = place[:m.start()] + place[m.end():]
    venue, short = place, place
    for kw, v, s in VENUE_FIX:
        if kw in place:
            venue, short = v, s
            break
    if not district:
        md = re.search(r"([\u4e00-\u9fa5]{2,3}区)", place)
        if md:
            district = md.group(1)
    # 政府平台的"地点"常是完整地址, 归一到场馆类别词
    if len(short) > 10:
        for kw in ("艺术中心", "文化中心", "会展中心", "展览馆", "美术馆", "博览馆"):
            if kw in place:
                short = kw
                break
        else:
            short = "其他场馆"
    return venue or "上海", short, district


def parse_gov(html):
    soup = BeautifulSoup(html, "html.parser")
    table = None
    for t in soup.find_all("table"):
        th = t.find("th")
        if th and "展览会名称" in th.get_text():
            table = t
            break
    out = []
    if not table:
        return out
    for tr in table.find_all("tr"):
        a = tr.find("a", class_="ggxx")
        if not a:
            continue
        name = a.get_text(" ", strip=True)
        href = a.get("href") or ""
        code = href.split("code=")[-1] if "code=" in href else ""
        tds = tr.find_all("td")
        cells = [td.get_text(" ", strip=True).replace("\xa0", " ") for td in tds]
        org = cells[1] if len(cells) > 1 else ""
        place = cells[2] if len(cells) > 2 else ""
        otype = cells[3] if len(cells) > 3 else ""
        dtext = cells[4] if len(cells) > 4 else ""
        start, end = parse_range(dtext)
        if not name:
            continue
        venue, short, district = split_venue(place)
        out.append({"name": name, "start": start, "end": end,
                    "venue": venue, "venue_short": short, "district": district,
                    "organizer": org, "official_type": otype,
                    "website": GOV_DETAIL % code if code else "",
                    "place_raw": place, "halls": ""})
    return out


def fetch_gov(months=15):
    today = date.today()
    y, m = today.year, today.month - 1
    if m < 1:
        y, m = y - 1, 12
    targets = month_list((y, m), months + 1)
    s = requests.Session()
    headers = dict(HEADERS)
    headers["Referer"] = GOV_REFER
    headers["Content-Type"] = "application/x-www-form-urlencoded"
    events = []
    for ym in targets:
        y_, m_ = int(ym[:4]), int(ym[5:7])
        if m_ == 12:
            last = "%04d-12-31" % y_
        else:
            last = "%04d-%02d-%02d" % (y_, m_ + 1, 1)
            last = (date.fromisoformat(last).toordinal() - 1)
            last = date.fromordinal(last).isoformat()
        form = {"exhiName": "", "exhiCheck": "S", "sTime": ym + "-01", "eTime": last,
                "docno": "", "exhiClass": "", "exhiCorp": "", "exhiAddress": "",
                "exhiType": ""}
        try:
            r = s.post(GOV_POST, data=form, headers=headers, timeout=TIMEOUT, verify=False)
            r.encoding = r.apparent_encoding or "utf-8"
        except Exception as ex:
            print("  [FAIL] %s %r" % (ym, ex))
            continue
        rows = parse_gov(r.text)
        print("[GOV] %s -> %d rows" % (ym, len(rows)))
        for x in rows:
            x["source"] = "GOV"
            x["kind"] = "展览排期"
            events.append(x)
        time.sleep(PAUSE)
    return events


# ---------------- 合并 ----------------

def norm_name(n):
    n = re.sub(r"^第[一二三四五六七八九十百零\d]+届", "", n or "")
    n = re.sub(r"20\d\d", "", n)
    n = re.sub(r"[\s·・,，、（）()\-—/／:：'\"]", "", n)
    n = re.sub(r"(上海|中国|国际|亚洲|全球|世界)", "", n)
    return n.lower()


def same_event(a, b):
    if not a or not b:
        return False
    if a in b or b in a:
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.85


def merge(*sources):
    buckets = {}
    for src in sources:
        for e in src:
            name = re.sub(r"\s+", " ", e.get("name") or "").strip()
            if not name or not e.get("start"):
                continue
            e = dict(e)
            e["name"] = name
            buckets.setdefault((e.get("venue_short"), e["start"]), []).append(e)

    result = []
    for (vs, st), arr in buckets.items():
        groups = []
        for e in arr:
            nn = norm_name(e["name"])
            hit = None
            for g in groups:
                if same_event(nn, g["norm"]):
                    hit = g
                    break
            if hit:
                m = hit["event"]
                for f in ("halls", "organizer", "website", "official_type"):
                    if not m.get(f) and e.get(f):
                        m[f] = e[f]
                srcs = m["source"].split("+")
                if e.get("source") and e["source"] not in srcs:
                    m["source"] = m["source"] + "+" + e["source"]
                if len(e["name"]) > len(m["name"]):
                    m["name"] = e["name"]
                    hit["norm"] = norm_name(e["name"])
            else:
                groups.append({"norm": nn, "event": e})
        result.extend(g["event"] for g in groups)

    out = []
    for e in result:
        name = e["name"]
        feat, ftag = featured_of(name, e.get("organizer", ""))
        cat = guess_category(name)
        out.append({
            "id": make_id(e["source"], name, e["start"]),
            "name": name,
            "start": e["start"],
            "end": e.get("end") or e["start"],
            "venue": e.get("venue") or "上海",
            "venue_short": e.get("venue_short") or "其他场馆",
            "district": e.get("district", ""),
            "category": cat,
            "topics": guess_topics(name),
            "featured": feat,
            "featured_tag": ftag,
            "admit": admission_of(name, cat, e.get("official_type", "")),
            "halls": e.get("halls", ""),
            "organizer": e.get("organizer", ""),
            "official_type": e.get("official_type", ""),
            "website": e.get("website", ""),
            "kind": e.get("kind", "展览排期"),
            "source": e["source"],
            "status": status_of(e["start"], e.get("end")),
        })
    out.sort(key=lambda x: (x["start"], x["name"]))
    return out


def main():
    t0 = time.time()
    gov = fetch_gov()
    necc = fetch_necc()
    sniec = fetch_sniec()
    events = merge(gov, necc, sniec)
    payload = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "city": "上海",
        "count": len(events),
        "events": events,
    }
    out = os.path.join(DATA, "events.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    # App 首屏只需要未结束的场次, 单独产出一份精简数据
    active = [e for e in events if e["status"] != "finished"]
    payload_active = {
        "updated": payload["updated"],
        "city": "上海",
        "count": len(active),
        "events": active,
    }
    out2 = os.path.join(DATA, "events_active.json")
    with open(out2, "w", encoding="utf-8") as f:
        json.dump(payload_active, f, ensure_ascii=False, indent=1)
    print("active output: %s (%.1f KB, %d events)"
          % (out2, os.path.getsize(out2) / 1024.0, len(active)))
    print("\n===== DONE =====")
    print("GOV raw: %d, NECC raw: %d, SNIEC raw: %d, merged: %d"
          % (len(gov), len(necc), len(sniec), len(events)))
    print("output: %s (%.1f KB)" % (out, os.path.getsize(out) / 1024.0))
    print("elapsed: %.1fs" % (time.time() - t0))
    from collections import Counter
    print("venue:", Counter(e["venue_short"] for e in events).most_common())
    print("category:", Counter(e["category"] for e in events).most_common(8))
    print("status:", Counter(e["status"] for e in events).most_common())


if __name__ == "__main__":
    main()
