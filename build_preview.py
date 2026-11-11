# -*- coding: utf-8 -*-
"""把 events_active.json 渲染成一个手机端可交互原型 preview.html"""
import json
import os
from datetime import date

BASE = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(BASE, "data", "events_active.json"), encoding="utf-8"))
PAYLOAD = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>上海展会 · 原型</title>
<style>
:root{
  --bg:#0A0C0F; --surface:#14171C; --surface2:#1A1E24;
  --line:rgba(255,255,255,.07); --line2:rgba(255,255,255,.12);
  --text:#E9EBEE; --muted:#878E98; --dim:#5E656E;
  --accent:#2DD4A7; --accent-dim:rgba(45,212,167,.14);
  --warn:#F5A524;
}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;height:100%}
body{
  background:#060709;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;
  display:flex;align-items:center;justify-content:center;padding:28px 0;color:var(--text);
}
.phone{
  width:390px;height:844px;background:var(--bg);border-radius:44px;position:relative;
  overflow:hidden;display:flex;flex-direction:column;
  box-shadow:0 0 0 10px #17191d,0 0 0 11px #2a2d33,0 30px 80px rgba(0,0,0,.8);
}
.notch{position:absolute;top:0;left:50%;transform:translateX(-50%);width:126px;height:26px;
  background:#17191d;border-radius:0 0 18px 18px;z-index:30}
.statusbar{height:52px;display:flex;align-items:flex-end;justify-content:space-between;
  padding:0 26px 6px;font-size:12px;font-weight:500;color:var(--text);flex:none}
.statusbar .right{display:flex;gap:5px;align-items:center;opacity:.9}
.bar{display:flex;gap:2px;align-items:flex-end}
.bar i{display:block;width:3px;background:currentColor;border-radius:1px}
.bar i:nth-child(1){height:4px}.bar i:nth-child(2){height:6px}
.bar i:nth-child(3){height:8px}.bar i:nth-child(4){height:10px}

header{padding:6px 20px 0;flex:none}
.title{display:flex;align-items:baseline;gap:8px;margin-bottom:14px}
.title h1{font-size:24px;font-weight:600;margin:0;letter-spacing:.5px}
.title span{font-size:12px;color:var(--muted)}
.search{
  height:38px;background:var(--surface2);border-radius:11px;display:flex;align-items:center;
  gap:8px;padding:0 12px;color:var(--dim);font-size:13.5px;border:1px solid transparent;
}
.search svg{flex:none;opacity:.6}
.chips{display:flex;gap:8px;overflow-x:auto;padding:14px 20px 12px;flex:none;
  scrollbar-width:none;}
.chips::-webkit-scrollbar{display:none}
.chip{
  flex:none;padding:7px 14px;border-radius:20px;background:var(--surface2);
  font-size:13px;color:var(--muted);border:1px solid transparent;white-space:nowrap;
  transition:all .15s;
}
.chip.on{background:var(--accent-dim);color:var(--accent);border-color:rgba(45,212,167,.35)}
.chips.venue{padding-top:0;padding-bottom:14px}
.chips.venue .chip{font-size:12px;padding:5px 11px;border-radius:16px;color:var(--dim)}
.chips.venue .chip.on{color:var(--accent);background:var(--accent-dim)}

main{flex:1;overflow-y:auto;padding:0 20px 96px;scrollbar-width:none}
main::-webkit-scrollbar{display:none}

.daygroup{position:sticky;top:0;background:var(--bg);padding:10px 0 8px;z-index:5;
  display:flex;align-items:center;gap:8px}
.daygroup .d{font-size:13px;font-weight:600;color:var(--text)}
.daygroup .w{font-size:12px;color:var(--dim)}
.daygroup .rel{font-size:11px;color:var(--accent);background:var(--accent-dim);
  padding:2px 7px;border-radius:6px;margin-left:auto}
.daygroup .rel.gray{color:var(--muted);background:var(--surface2)}

.card{display:flex;gap:12px;padding:13px 0;border-bottom:1px solid var(--line);cursor:pointer}
.card:active{opacity:.65}
.datebox{flex:none;width:42px;text-align:center;padding-top:1px}
.datebox .m{font-size:10px;color:var(--dim);letter-spacing:.5px}
.datebox .n{font-size:19px;font-weight:600;line-height:1.1;color:var(--text);font-variant-numeric:tabular-nums}
.card.live .datebox .n{color:var(--accent)}
.body{flex:1;min-width:0}
.name{font-size:14.5px;font-weight:500;line-height:1.45;margin-bottom:6px;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.meta{display:flex;flex-wrap:wrap;gap:5px 10px;font-size:11.5px;color:var(--muted)}
.meta b{font-weight:400;color:#A7AEB8}
.tag{font-size:10.5px;padding:2px 6px;border-radius:5px;background:var(--surface2);color:var(--muted)}
.tag.feat{background:rgba(245,165,36,.16);color:var(--warn);font-weight:500}
.tag.topic{background:rgba(167,139,250,.14);color:#A78BFA}
.tag.live{background:var(--accent-dim);color:var(--accent)}
.fbar{display:inline-block;width:3px;height:12px;background:var(--warn);border-radius:2px;
  margin-right:7px;vertical-align:-1px}
.card.feat{background:linear-gradient(90deg,rgba(245,165,36,.055),rgba(245,165,36,0) 55%)}
.card.feat .name{color:#FBF3E4}

.sheet{
  position:absolute;inset:0;background:rgba(0,0,0,.55);z-index:40;display:none;
  align-items:flex-end;backdrop-filter:blur(2px);
}
.sheet.show{display:flex}
.panel{background:var(--surface);width:100%;border-radius:22px 22px 0 0;padding:8px 20px 26px;
  max-height:78%;overflow-y:auto;animation:up .22s ease-out}
@keyframes up{from{transform:translateY(30px);opacity:.6}to{transform:none;opacity:1}}
.grab{width:36px;height:4px;border-radius:2px;background:var(--line2);margin:0 auto 16px}
.panel h2{font-size:17px;line-height:1.5;margin:0 0 14px;font-weight:600}
.row{display:flex;gap:12px;padding:11px 0;border-top:1px solid var(--line);font-size:13px}
.row .k{flex:none;width:56px;color:var(--dim);font-size:12.5px}
.row .v{flex:1;color:#C9CED6;line-height:1.55;word-break:break-all}
.row .v a{color:var(--accent);text-decoration:none}
.actions{display:flex;gap:10px;margin-top:20px}
.btn{flex:1;height:44px;border-radius:12px;border:none;font-size:14px;font-weight:500;
  font-family:inherit;background:var(--surface2);color:var(--text);cursor:pointer}
.btn.primary{background:var(--accent);color:#04231A}

.tabbar{
  position:absolute;bottom:0;left:0;right:0;height:76px;background:rgba(10,12,15,.92);
  border-top:1px solid var(--line);display:flex;align-items:flex-start;padding-top:10px;
  z-index:20;backdrop-filter:blur(12px);
}
.tab{flex:1;text-align:center;font-size:10.5px;color:var(--dim);display:flex;
  flex-direction:column;align-items:center;gap:4px}
.tab.on{color:var(--accent)}
.homebar{position:absolute;bottom:7px;left:50%;transform:translateX(-50%);
  width:130px;height:5px;border-radius:3px;background:#3a3f46;z-index:25}
.empty{text-align:center;color:var(--dim);font-size:13px;padding:60px 0}
</style>
</head>
<body>
<div class="phone">
  <div class="notch"></div>
  <div class="statusbar">
    <span>9:41</span>
    <span class="right">
      <span class="bar"><i></i><i></i><i></i><i></i></span>
      <svg width="15" height="11" viewBox="0 0 15 11" fill="none"><path d="M1 4.2a9 9 0 0 1 13 0M3.4 6.8a5.6 5.6 0 0 1 8.2 0M6 9.2a2.2 2.2 0 0 1 3 0" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>
      <svg width="24" height="11" viewBox="0 0 24 11" fill="none"><rect x=".5" y=".5" width="20" height="10" rx="2.5" stroke="currentColor" opacity=".4"/><rect x="2" y="2" width="15" height="7" rx="1.5" fill="currentColor"/><path d="M22 4v3a2 2 0 0 0 0-3z" fill="currentColor" opacity=".5"/></svg>
    </span>
  </div>

  <header>
    <div class="title"><h1>上海展会</h1><span id="cnt"></span></div>
    <div class="search">
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none"><circle cx="6.5" cy="6.5" r="4.8" stroke="currentColor" stroke-width="1.4"/><path d="M10.2 10.2L13 13" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>
      搜索展会、场馆或主办方
    </div>
  </header>

  <nav class="chips" id="chipsTopic"></nav>
  <nav class="chips venue" id="chipsVenue"></nav>
  <main id="list"></main>

  <div class="tabbar">
    <div class="tab on">
      <svg width="19" height="19" viewBox="0 0 19 19" fill="none"><path d="M2.5 5h14M2.5 9.5h14M2.5 14h9" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>
      时间轴
    </div>
    <div class="tab">
      <svg width="19" height="19" viewBox="0 0 19 19" fill="none"><rect x="2.5" y="3.5" width="14" height="13" rx="2.5" stroke="currentColor" stroke-width="1.6"/><path d="M6 2v3M13 2v3M2.5 8h14" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>
      日历
    </div>
    <div class="tab">
      <svg width="19" height="19" viewBox="0 0 19 19" fill="none"><path d="M9.5 15.5s-6-3.6-6-7.4a3.4 3.4 0 0 1 6-2 3.4 3.4 0 0 1 6 2c0 3.8-6 7.4-6 7.4z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>
      关注
    </div>
  </div>
  <div class="homebar"></div>

  <div class="sheet" id="sheet">
    <div class="panel" id="panel"></div>
  </div>
</div>

<script>
const DATA = __DATA__;
const WEEK = ["周日","周一","周二","周三","周四","周五","周六"];
const SRC = {GOV:"市商务委会展平台", NECC:"国家会展中心官网", SNIEC:"新国际博览中心官网"};
const TOPIC_ORDER = ["全部","重磅","进行中","一周内","AI","机器人","算力","半导体","新能源",
  "汽车","低空经济","医疗健康","宠物","动漫游戏","食品饮料","家居建材","时尚纺织","文创艺术","出海跨境"];
const FIXED = ["全部","重磅","进行中","一周内"];
const hasT = t => DATA.events.some(e => (e.topics || []).includes(t));
const AI_SET = ["AI", "机器人", "算力"];
const isAI = e => (e.topics || []).some(t => AI_SET.includes(t));
const TOPICS = TOPIC_ORDER.filter(t => FIXED.includes(t) || hasT(t));
const VENUES = [...new Set(DATA.events.map(e => e.venue_short))];
const VENUE_CHIPS = ["全部场馆"].concat(VENUES);
let curTopic = "全部", curVenue = "全部场馆";
const today = new Date(); today.setHours(0,0,0,0);
const pd = s => { const [y,m,d] = s.split("-").map(Number); return new Date(y, m-1, d); };
const days = s => Math.round((pd(s) - today) / 86400000);

document.getElementById("cnt").textContent =
  DATA.count + " 场进行中与待开展 · " + DATA.events.filter(e => e.featured).length + " 场重磅";

function buildChips(){
  document.getElementById("chipsTopic").innerHTML = TOPICS.map(t =>
    `<div class="chip${t===curTopic?" on":""}" data-t="${t}">${t}</div>`).join("");
  document.getElementById("chipsVenue").innerHTML = VENUE_CHIPS.map(v =>
    `<div class="chip${v===curVenue?" on":""}" data-v="${v}">${v}</div>`).join("");
}
buildChips();

document.getElementById("chipsTopic").onclick = e => {
  const el = e.target.closest(".chip"); if(!el) return;
  curTopic = el.dataset.t; buildChips(); render();
};
document.getElementById("chipsVenue").onclick = e => {
  const el = e.target.closest(".chip"); if(!el) return;
  curVenue = el.dataset.v; buildChips(); render();
};

function filter(list){
  let r = list;
  if(curTopic === "重磅") r = r.filter(e => e.featured);
  else if(curTopic === "进行中") r = r.filter(e => e.status === "ongoing");
  else if(curTopic === "一周内") r = r.filter(e => days(e.start) >= 0 && days(e.start) <= 7);
  else if(curTopic === "AI") r = r.filter(isAI);
  else if(curTopic !== "全部") r = r.filter(e => (e.topics || []).includes(curTopic));
  if(curVenue !== "全部场馆") r = r.filter(e => e.venue_short === curVenue);
  return r;
}

function render(){
  const list = filter(DATA.events).sort((a,b)=> a.start.localeCompare(b.start));
  const box = document.getElementById("list");
  if(!list.length){ box.innerHTML = '<div class="empty">暂无符合条件的展会</div>'; return; }
  let html = "", last = "";
  for(const e of list){
    if(e.start !== last){
      last = e.start;
      const d = pd(e.start), diff = days(e.start);
      const rel = e.status === "ongoing" ? "进行中"
        : diff === 0 ? "今天" : diff === 1 ? "明天"
        : diff > 0 ? diff + " 天后" : "";
      html += `<div class="daygroup"><span class="d">${d.getMonth()+1}月${d.getDate()}日</span>`
           + `<span class="w">${WEEK[d.getDay()]}</span>`
           + (rel ? `<span class="rel${e.status==="ongoing"?"":" gray"}">${rel}</span>` : "")
           + `</div>`;
    }
    const d = pd(e.start);
    const ai = isAI(e);
    html += `<div class="card${e.status==="ongoing"?" live":""}${e.featured?" feat":""}" data-id="${e.id}">
      <div class="datebox"><div class="m">${d.getMonth()+1}月</div><div class="n">${d.getDate()}</div></div>
      <div class="body">
        <div class="name">${e.featured?'<i class="fbar"></i>':""}${e.name}</div>
        <div class="meta">
          <span><b>${e.venue_short}</b>${e.district ? " · " + e.district : ""}</span>
          ${e.halls ? `<span>${e.halls.split("、").length} 个馆</span>` : ""}
          ${e.featured ? `<span class="tag feat">${e.featured_tag || "重磅"}</span>` : ""}
          ${ai ? '<span class="tag topic">AI</span>' : ""}
          <span class="tag">${e.category}</span>
          ${e.status==="ongoing" ? '<span class="tag live">进行中</span>' : ""}
        </div>
      </div>
    </div>`;
  }
  box.innerHTML = html;
}
render();

document.getElementById("list").onclick = e => {
  const card = e.target.closest(".card"); if(!card) return;
  openDetail(DATA.events.find(x => x.id === card.dataset.id));
};

function openDetail(e){
  const d1 = pd(e.start), d2 = pd(e.end);
  const dur = Math.round((d2 - d1)/86400000) + 1;
  const hallList = e.halls ? e.halls.split("、").filter(Boolean) : [];
  document.getElementById("panel").innerHTML = `
    <div class="grab"></div>
    <h2>${e.name}</h2>
    <div class="row"><div class="k">时间</div><div class="v">${e.start}${e.end!==e.start?" 至 "+e.end:""}<br>共 ${dur} 天${e.status==="ongoing"?" · 正在进行":days(e.start)>0?" · "+days(e.start)+" 天后开始":""}</div></div>
    <div class="row"><div class="k">场馆</div><div class="v">${e.venue}（${e.district}）${hallList.length?"<br>"+hallList.length+" 个展馆："+hallList.join("、"):""}</div></div>
    <div class="row"><div class="k">分类</div><div class="v">${e.category}${e.official_type ? " · " + e.official_type : ""}</div></div>
    ${(e.topics||[]).length?`<div class="row"><div class="k">主题</div><div class="v">${e.topics.map(t => `<span class="tag topic" style="margin:0 6px 4px 0;display:inline-block">${t}</span>`).join("")}</div></div>`:""}
    ${e.featured?`<div class="row"><div class="k">分量</div><div class="v"><span class="tag feat">${e.featured_tag||"重磅"}</span></div></div>`:""}
    ${e.organizer?`<div class="row"><div class="k">主办</div><div class="v">${e.organizer}</div></div>`:""}
    ${e.website?`<div class="row"><div class="k">链接</div><div class="v"><a href="${e.website}" target="_blank">${e.website.includes("sww.sh.gov.cn") ? "市商务委备案详情页" : e.website}</a></div></div>`:""}
    <div class="row"><div class="k">来源</div><div class="v">${e.source.split("+").map(s => SRC[s] || s).join(" · ")}</div></div>
    <div class="actions">
      <button class="btn">加提醒</button>
      <button class="btn primary">加入日历</button>
    </div>`;
  document.getElementById("sheet").classList.add("show");
}
document.getElementById("sheet").onclick = e => {
  if(e.target.id === "sheet") document.getElementById("sheet").classList.remove("show");
};
</script>
</body>
</html>
"""

out = os.path.join(BASE, "preview.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(HTML.replace("__DATA__", PAYLOAD))
print("preview.html written, %.1f KB, %d events" % (os.path.getsize(out) / 1024.0, data["count"]))
