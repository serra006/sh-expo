# -*- coding: utf-8 -*-
"""生成 APK 内置的 app 页面：全屏、无模拟外框、功能全部接通。

与 preview.html（桌面原型）的区别：
  - 去掉手机外框 / 假状态栏 / 假 Home 条，改成真机全屏 flex 布局
  - 搜索框变成真输入框，可搜名称、场馆、主办方、展馆号
  - 三个 Tab 全部实现：时间轴 / 日历（月视图）/ 关注
  - 提醒、加入系统日历、打开链接通过 JS Bridge 调原生
"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(BASE, "..", "data", "events_active.json"), encoding="utf-8"))
# 让内置数据带上当前发布版本：首次启动时 manifest 版本一致，就不必重下 140KB，
# 也不会弹一条「数据已更新」的无效横幅。只有线上真的变了才提示。
mf_path = os.path.join(BASE, "..", "public", "manifest.json")
if os.path.exists(mf_path):
    try:
        mf = json.load(open(mf_path, encoding="utf-8"))
        data["version"] = mf.get("version", "")
    except (ValueError, OSError):
        pass
PAYLOAD = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
<meta name="theme-color" content="#0A0C0F">
<title>上海展会</title>
<style>
:root{
  --bg:#0A0C0F; --surface:#14171C; --surface2:#1A1E24; --surface3:#20252C;
  --line:rgba(255,255,255,.07); --line2:rgba(255,255,255,.13);
  --text:#E9EBEE; --muted:#8A919B; --dim:#5E656E;
  --accent:#2DD4A7; --accent-dim:rgba(45,212,167,.14);
  --warn:#F5A524; --warn-dim:rgba(245,165,36,.15);
  --purple:#A78BFA;
}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent;
  -webkit-user-select:none;user-select:none}
html,body{margin:0;height:100%;overflow:hidden;background:var(--bg)}
body{
  font-family:system-ui,-apple-system,"PingFang SC","Noto Sans CJK SC","Microsoft YaHei",sans-serif;
  color:var(--text);display:flex;flex-direction:column;
  font-size:15px;-webkit-text-size-adjust:100%;
}

/* ---------- 顶栏 ---------- */
header{flex:none;padding:calc(10px + env(safe-area-inset-top)) 18px 0;background:var(--bg);
  border-bottom:1px solid transparent;transition:border-color .2s}
header.stuck{border-color:var(--line)}
.htop{display:flex;align-items:baseline;gap:9px}
.htop h1{font-size:21px;font-weight:600;margin:0;letter-spacing:.4px}
.htop .meta{font-size:11.5px;color:var(--dim);margin-left:auto;text-align:right;line-height:1.4}
.htop .meta .sync{display:block;font-size:10.5px;margin-top:2px;color:var(--dim)}

/* ---------- 更新提示条 ---------- */
.newbar{margin:0 18px 4px;padding:9px 12px;border-radius:10px;background:var(--accent-dim);
  border:1px solid rgba(45,212,167,.28);color:var(--accent);font-size:12.5px;
  display:flex;align-items:center;gap:8px}
.newbar.hide{display:none}
.newbar .x{margin-left:auto;color:var(--muted);font-size:14px;padding:0 4px}

/* ---------- 搜索 ---------- */
.search{margin:11px 0 0;height:38px;background:var(--surface2);border-radius:11px;
  display:flex;align-items:center;gap:8px;padding:0 11px;border:1px solid transparent;
  transition:border-color .18s,background .18s}
.search.focus{border-color:rgba(45,212,167,.35);background:var(--surface)}
.search svg{flex:none;color:var(--dim)}
.search input{flex:1;min-width:0;background:none;border:none;outline:none;color:var(--text);
  font-size:14px;font-family:inherit;-webkit-user-select:text;user-select:text;
  -webkit-appearance:none;appearance:none;padding:0;margin:0;line-height:1.3}
.search input::-webkit-search-cancel-button{display:none;-webkit-appearance:none}
.search input::placeholder{color:var(--dim)}
.search .clr{flex:none;width:18px;height:18px;border-radius:50%;background:var(--surface3);
  color:var(--muted);display:none;align-items:center;justify-content:center;font-size:12px;
  line-height:1;padding-bottom:1px}
.search.hasq .clr{display:flex}

/* ---------- 筛选 chips ---------- */
.chips{display:flex;gap:8px;overflow-x:auto;padding:12px 18px 10px;flex:none;
  scrollbar-width:none;-webkit-overflow-scrolling:touch}
.chips::-webkit-scrollbar{display:none}
.chip{flex:none;padding:6px 13px;border-radius:18px;background:var(--surface2);font-size:13px;
  color:var(--muted);border:1px solid transparent;white-space:nowrap;transition:all .15s}
.chip.on{background:var(--accent-dim);color:var(--accent);border-color:rgba(45,212,167,.32)}
.chip.on.warn{background:var(--warn-dim);color:var(--warn);border-color:rgba(245,165,36,.32)}
.chips.venue{padding-top:0;padding-bottom:12px}
.chips.venue .chip{font-size:12px;padding:5px 10px;border-radius:14px;color:var(--dim)}

/* ---------- 类型切换（展会 / 开发者大会） ---------- */
.kindbar{display:flex;gap:4px;margin:10px 18px 0;padding:4px;flex:none;
  background:var(--surface2);border-radius:12px}
.kindbar .kb{flex:1;text-align:center;padding:7px 0;border-radius:9px;font-size:13px;
  color:var(--dim);transition:all .18s;white-space:nowrap}
.kindbar .kb b{font-weight:600}
.kindbar .kb .n{font-size:11px;opacity:.65;margin-left:4px}
.kindbar .kb.on{background:var(--bg);color:var(--accent);box-shadow:0 1px 3px rgba(0,0,0,.18)}
.kindbar .kb.on .n{opacity:.85}

/* ---------- 列表 ---------- */
main{flex:1;overflow-y:auto;overflow-x:hidden;padding:0 18px;-webkit-overflow-scrolling:touch;
  overscroll-behavior-y:contain}
main::-webkit-scrollbar{display:none}
.pad{height:92px}

.daygroup{position:sticky;top:0;background:var(--bg);padding:9px 0 7px;z-index:5;
  display:flex;align-items:center;gap:8px}
.daygroup .d{font-size:13px;font-weight:600}
.daygroup .w{font-size:11.5px;color:var(--dim)}
.daygroup .rel{font-size:11px;color:var(--accent);background:var(--accent-dim);
  padding:2px 7px;border-radius:6px;margin-left:auto}
.daygroup .rel.gray{color:var(--muted);background:var(--surface2)}
.daygroup .rel.warn{color:var(--warn);background:var(--warn-dim)}

.card{display:flex;gap:12px;padding:13px 0;border-bottom:1px solid var(--line);
  position:relative}
.card:active{opacity:.6}
.card.feat{background:linear-gradient(90deg,rgba(245,165,36,.055),rgba(245,165,36,0) 58%)}
.datebox{flex:none;width:40px;text-align:center;padding-top:1px}
.datebox .m{font-size:10px;color:var(--dim);letter-spacing:.5px}
.datebox .n{font-size:19px;font-weight:600;line-height:1.15;
  font-variant-numeric:tabular-nums;font-feature-settings:"tnum"}
.card.live .datebox .n{color:var(--accent)}
.cardbody{flex:1;min-width:0}
.name{font-size:14.5px;font-weight:500;line-height:1.45;margin-bottom:6px;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.card.feat .name{color:#FBF3E4}
.fbar{display:inline-block;width:3px;height:12px;background:var(--warn);border-radius:2px;
  margin-right:6px;vertical-align:-1px}
.meta{display:flex;flex-wrap:wrap;gap:5px 9px;font-size:11.5px;color:var(--muted);
  align-items:center}
.meta b{font-weight:400;color:#A7AEB8}
.tag{font-size:10.5px;padding:2px 6px;border-radius:5px;background:var(--surface2);
  color:var(--muted);white-space:nowrap}
.tag.feat{background:var(--warn-dim);color:var(--warn);font-weight:500}
.tag.topic{background:rgba(167,139,250,.14);color:var(--purple)}
.tag.live{background:var(--accent-dim);color:var(--accent)}
.tag.fav{background:rgba(45,212,167,.10);color:var(--accent)}
.tag.trade{background:rgba(240,113,120,.16);color:#F07178}
.tag.open{background:var(--accent-dim);color:var(--accent)}
.tag.dead{background:rgba(240,113,120,.16);color:#F07178;margin-left:4px}
.tag.soon{background:rgba(245,165,36,.14);color:var(--warn);margin-left:4px}
.tag.ok{background:var(--accent-dim);color:var(--accent);margin-left:4px}
.summary{margin-top:6px;padding:7px 9px;border-radius:8px;background:rgba(240,113,120,.10);
  border-left:2px solid rgba(240,113,120,.55);font-size:12.5px;line-height:1.65;color:#F3B3B7}
.chan{border:1px solid var(--line2);border-radius:9px;padding:8px 9px;margin-bottom:7px;background:var(--surface2)}
.chan:last-child{margin-bottom:0}
.chan.off{opacity:.72}
.chan .ch{display:flex;align-items:center;gap:6px;flex-wrap:wrap;font-size:13px;color:var(--text);font-weight:600}
.chan .line{font-size:12.5px;line-height:1.62;color:var(--muted);margin-top:4px}
.chan .line b{color:var(--text);font-weight:500}
.hint{color:var(--dim);font-size:12px;line-height:1.6}
.mini{margin-top:9px;background:var(--surface2);border:1px solid var(--line2);color:var(--accent);
  font-size:12px;padding:7px 11px;border-radius:9px;font-family:inherit;display:inline-block}
.mini:active{opacity:.7}
.mini.inline{margin-top:0;margin-left:8px;padding:2px 8px;font-size:11.5px;vertical-align:1px}
.wxline b{font-weight:600}
.bell{position:absolute;right:0;top:14px;width:16px;height:16px;color:var(--accent);opacity:0}
.card.hasrem .bell{opacity:.85}
.card.hasrem .cardbody{padding-right:17px}

.empty{text-align:center;color:var(--dim);font-size:13.5px;padding:64px 20px;line-height:1.9}
.empty b{display:block;font-size:15px;color:var(--muted);font-weight:500;margin-bottom:6px}
.foot{text-align:center;color:var(--dim);font-size:11px;padding:22px 0 8px;line-height:1.8}

/* ---------- 月历 ---------- */
.calbar{display:flex;align-items:center;gap:10px;padding:4px 0 12px}
.calbar .ym{font-size:16px;font-weight:600;min-width:104px}
.calbar .nav{width:30px;height:30px;border-radius:9px;background:var(--surface2);
  display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:15px}
.calbar .nav:active{background:var(--surface3)}
.calbar .today-btn{margin-left:auto;font-size:12px;color:var(--accent);
  background:var(--accent-dim);padding:5px 11px;border-radius:9px}
.grid{display:grid;grid-template-columns:repeat(7,1fr);gap:2px 0;margin-bottom:6px}
.grid .wk{text-align:center;font-size:11px;color:var(--dim);padding:4px 0 6px}
.cell{position:relative;height:46px;display:flex;flex-direction:column;align-items:center;
  justify-content:center;gap:3px;border-radius:10px}
.cell.blank{visibility:hidden}
.cell .dn{font-size:14px;color:var(--muted);font-variant-numeric:tabular-nums}
.cell.out .dn{color:#3C424A}
.cell.today .dn{color:var(--accent);font-weight:600}
.cell.sel{background:var(--surface2)}
.cell.sel .dn{color:var(--text);font-weight:600}
.cell .dots{display:flex;gap:3px;height:5px;align-items:center}
.cell .dots i{width:4px;height:4px;border-radius:50%;background:#3E4650;display:block}
.cell .dots i.a{background:var(--warn)}
.cell .cnt{position:absolute;top:3px;right:5px;font-size:9px;color:var(--dim)}

/* ---------- 详情面板 ---------- */
.sheet{position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.58);z-index:40;display:none;
  align-items:flex-end}
.sheet.show{display:flex}
.panel{background:var(--surface);width:100%;border-radius:22px 22px 0 0;
  padding:8px 18px calc(22px + env(safe-area-inset-bottom));max-height:80%;
  overflow-y:auto;animation:up .22s ease-out;overscroll-behavior:contain}
@keyframes up{from{transform:translateY(34px);opacity:.55}to{transform:none;opacity:1}}
.grab{width:36px;height:4px;border-radius:2px;background:var(--line2);margin:0 auto 15px}
.panel h2{font-size:16.5px;line-height:1.5;margin:0 0 6px;font-weight:600}
.panel .subline{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px}
.row{display:flex;gap:12px;padding:11px 0;border-top:1px solid var(--line);font-size:13px}
.row .k{flex:none;width:52px;color:var(--dim);font-size:12.5px}
.row .v{flex:1;color:#C9CED6;line-height:1.6;word-break:break-word;-webkit-user-select:text;
  user-select:text}
.row .v a{color:var(--accent);text-decoration:none;word-break:break-all}
.actions{display:flex;gap:9px;margin-top:18px}
.btn{flex:1;height:44px;border-radius:12px;border:none;font-size:13.5px;font-weight:500;
  font-family:inherit;background:var(--surface2);color:var(--text);padding:0 6px}
.btn:active{opacity:.75}
.btn.primary{background:var(--accent);color:#04231A}
.btn.on{background:var(--accent-dim);color:var(--accent)}
.actions2{display:flex;gap:9px;margin-top:9px}
.entry{display:flex;flex-wrap:wrap;gap:8px}
.entry .btn{flex:0 0 auto;height:40px;padding:0 15px;font-size:13px;border:1px solid var(--line2)}
.entry .btn.primary{border-color:transparent;font-weight:600}

/* ---------- 底部 Tab ---------- */
.tabbar{flex:none;display:flex;background:rgba(10,12,15,.96);
  border-top:1px solid var(--line);padding-bottom:env(safe-area-inset-bottom);
  backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px)}
.tab{flex:1;padding:8px 0 9px;text-align:center;font-size:10.5px;color:var(--dim);
  display:flex;flex-direction:column;align-items:center;gap:3px;position:relative}
.tab.on{color:var(--accent)}
.tab .badge{position:absolute;top:5px;left:50%;margin-left:4px;min-width:15px;height:15px;
  border-radius:8px;background:var(--warn);color:#231502;font-size:9.5px;font-weight:600;
  display:flex;align-items:center;justify-content:center;padding:0 4px}

/* ---------- Toast ---------- */
.toast{position:fixed;left:50%;bottom:96px;transform:translateX(-50%) translateY(10px);
  background:rgba(32,37,44,.97);color:var(--text);font-size:13px;padding:10px 16px;
  border-radius:11px;z-index:90;opacity:0;transition:all .22s;pointer-events:none;
  max-width:78vw;text-align:center;line-height:1.5;border:1px solid var(--line2)}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
</style>
</head>
<body>

<header id="hdr">
  <div class="htop">
    <h1>上海展会</h1>
    <div class="meta" id="hmeta"></div>
  </div>
  <div class="search" id="searchBox">
    <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
      <circle cx="6.5" cy="6.5" r="4.8" stroke="currentColor" stroke-width="1.4"/>
      <path d="M10.2 10.2L13 13" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
    </svg>
    <input id="q" type="search" placeholder="搜索展会、场馆、主办方" autocomplete="off"
           autocorrect="off" autocapitalize="off" spellcheck="false">
    <div class="clr" id="clr">✕</div>
  </div>
</header>

    <nav class="kindbar" id="kindBar"></nav>
    <nav class="chips" id="chipsTopic"></nav>
    <nav class="chips venue" id="chipsVenue"></nav>

<div class="newbar hide" id="newbar"></div>

<main id="main"></main>

<div class="tabbar">
  <div class="tab on" data-tab="timeline">
    <svg width="19" height="19" viewBox="0 0 19 19" fill="none">
      <path d="M2.5 5h14M2.5 9.5h14M2.5 14h9" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
    </svg>时间轴
  </div>
  <div class="tab" data-tab="calendar">
    <svg width="19" height="19" viewBox="0 0 19 19" fill="none">
      <rect x="2.5" y="3.5" width="14" height="13" rx="2.5" stroke="currentColor" stroke-width="1.6"/>
      <path d="M6 2v3M13 2v3M2.5 8h14" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
    </svg>日历
  </div>
  <div class="tab" data-tab="fav">
    <svg width="19" height="19" viewBox="0 0 19 19" fill="none">
      <path d="M9.5 15.5s-6-3.6-6-7.4a3.4 3.4 0 0 1 6-2 3.4 3.4 0 0 1 6 2c0 3.8-6 7.4-6 7.4z"
            stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>
    </svg>关注
  </div>
</div>

<div class="sheet" id="sheet"><div class="panel" id="panel"></div></div>
<div class="toast" id="toast"></div>

<script>
/* 老 WebView 兜底 */
if (!String.prototype.padStart) {
  String.prototype.padStart = function(len, ch) {
    let s = String(this); ch = ch || " ";
    while (s.length < len) s = ch + s;
    return s;
  };
}
let DATA = __DATA__;
let EVENTS = DATA.events || [];
const MIN_COUNT = 30;
// 分发端点：GitHub Pages 优先，jsDelivr / raw 兜底；manifest 还能下发新端点覆盖这里。
const REMOTE_ENDPOINTS = [
  "https://serra006.github.io/sh-expo/public",
  "https://cdn.jsdelivr.net/gh/serra006/sh-expo@main/public",
  "https://raw.githubusercontent.com/serra006/sh-expo/main/public"
];
const WEEK = ["周日","周一","周二","周三","周四","周五","周六"];
const SRC = {GOV:"市商务委会展平台", NECC:"国家会展中心官网", SNIEC:"新国际博览中心官网"};
const TOPIC_ORDER = ["全部","重磅","进行中","一周内","AI","机器人","算力","半导体","新能源",
  "汽车","低空经济","医疗健康","宠物","动漫游戏","食品饮料","家居建材","时尚纺织","文创艺术","出海跨境"];
const FIXED = ["全部","重磅","进行中","一周内"];
const AI_SET = ["AI","机器人","算力"];
const isAI = e => (e.topics || []).some(t => AI_SET.includes(t));
function hasT(t){ return EVENTS.some(e => (e.topics || []).includes(t)); }
let TOPICS = TOPIC_ORDER.slice();
let VENUES = [];

const today = new Date(); today.setHours(0,0,0,0);
const YMD = d => d.getFullYear() + "-" + String(d.getMonth()+1).padStart(2,"0") + "-" + String(d.getDate()).padStart(2,"0");
const pd = s => { const p = s.split("-").map(Number); return new Date(p[0], p[1]-1, p[2]); };
const days = s => Math.round((pd(s) - today) / 86400000);
const byId = id => EVENTS.find(e => e.id === id);
const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

/* ---------- 原生桥（浏览器里打开时优雅降级） ---------- */
const NA = (window.SHExpo && window.SHExpo.isApp) ? window.SHExpo : null;
const IS_APP = !!NA;
function toast(msg){
  const el = document.getElementById("toast");
  el.textContent = msg; el.classList.add("show");
  clearTimeout(toast._t); toast._t = setTimeout(() => el.classList.remove("show"), 1900);
}

/* ---------- 关注 ---------- */
let fav = new Set();
try { fav = new Set(JSON.parse(localStorage.getItem("fav") || "[]")); } catch(e) {}
function saveFav(){
  try { localStorage.setItem("fav", JSON.stringify([...fav])); } catch(e) {}
}

/* ---------- 提醒 ---------- */
let rems = {};   // id -> 触发时间戳
function loadRems(){
  rems = {};
  if (IS_APP && NA.listReminders) {
    try {
      const arr = JSON.parse(NA.listReminders() || "[]");
      arr.forEach(r => { rems[r.id] = r.t; });
    } catch(e) {}
  } else {
    try { rems = JSON.parse(localStorage.getItem("rems") || "{}"); } catch(e) {}
  }
}
loadRems();

/* ---------- 状态 ---------- */
let tab = "timeline", curTopic = "全部", curVenue = "全部场馆", q = "";
let curKind = "expo";
const kindOf = e => (e && e.kind_type === "dev") ? "dev" : "expo";
const KINDS = [{k:"expo", label:"展会"}, {k:"dev", label:"开发者大会"}];
let calY = today.getFullYear(), calM = today.getMonth(), calDay = null;

/* ---------- 顶部统计（在线更新后要重算） ---------- */
function updateMeta(){
  const pool = EVENTS.filter(e => kindOf(e) === curKind);
  const featCount = pool.filter(e => e.featured).length;
  const aiCount = pool.filter(isAI).length;
  const unit = curKind === "dev" ? "场活动待参加" : "场待开展";
  const stamp = esc((DATA.updated || "").slice(0, 10));
  document.getElementById("hmeta").innerHTML =
    pool.length + " " + unit + "<br>" + featCount + " 场重磅 · " + aiCount + " 场 AI"
    + '<span class="sync">' + (stamp ? "数据 " + stamp + " · " : "") + "点击刷新</span>";
}

/* ---------- 类型切换：展会 / 开发者大会 ---------- */
function buildKind(){
  const el = document.getElementById("kindBar");
  if (!el) return;
  el.innerHTML = KINDS.map(function(o){
    const n = EVENTS.filter(e => kindOf(e) === o.k).length;
    const on = o.k === curKind;
    return `<div class="kb${on?" on":""}" data-k="${o.k}"><b>${o.label}</b><span class="n">${n}</span></div>`;
  }).join("");
}
document.getElementById("kindBar").onclick = function(ev){
  const el = ev.target.closest(".kb"); if (!el) return;
  const k = el.dataset.k;
  if (k === curKind) return;
  curKind = k;
  curTopic = "全部"; curVenue = "全部场馆";
  rebuildDerived(); render();
};

/* ---------- chips ---------- */
function buildChips(){
  document.getElementById("chipsTopic").innerHTML = TOPICS.map(t => {
    const on = t === curTopic;
    const warn = on && (t === "重磅" || t === "AI");
    return `<div class="chip${on?" on":""}${warn?" warn":""}" data-t="${t}">${t}</div>`;
  }).join("");
  document.getElementById("chipsVenue").innerHTML = ["全部场馆"].concat(VENUES).map(v => {
    const on = v === curVenue;
    return `<div class="chip${on?" on":""}" data-v="${v}">${v}</div>`;
  }).join("");
}
document.getElementById("chipsTopic").onclick = e => {
  const el = e.target.closest(".chip"); if (!el) return;
  curTopic = el.dataset.t; buildChips(); render();
  el.scrollIntoView({inline:"center", block:"nearest", behavior:"smooth"});
};
document.getElementById("chipsVenue").onclick = e => {
  const el = e.target.closest(".chip"); if (!el) return;
  curVenue = el.dataset.v; buildChips(); render();
  el.scrollIntoView({inline:"center", block:"nearest", behavior:"smooth"});
};

/* ---------- 搜索 ---------- */
const qi = document.getElementById("q");
const sbox = document.getElementById("searchBox");
qi.addEventListener("focus", () => sbox.classList.add("focus"));
qi.addEventListener("blur", () => sbox.classList.remove("focus"));
qi.addEventListener("input", () => {
  q = qi.value.trim();
  sbox.classList.toggle("hasq", q.length > 0);
  render();
});
document.getElementById("clr").onclick = () => {
  qi.value = ""; q = ""; sbox.classList.remove("hasq"); qi.blur(); render();
};

function match(e, s){
  const hay = [e.name, e.venue_short, e.venue, e.organizer, e.halls,
               e.category, (e.topics||[]).join(" ")].join(" ").toLowerCase();
  return s.toLowerCase().split(/\s+/).every(w => hay.includes(w));
}

function filter(list, skipKind){
  let r = list;
  if (!skipKind) r = r.filter(e => kindOf(e) === curKind);
  if (curTopic === "重磅") r = r.filter(e => e.featured);
  else if (curTopic === "进行中") r = r.filter(e => e.status === "ongoing");
  else if (curTopic === "一周内") r = r.filter(e => days(e.start) >= 0 && days(e.start) <= 7);
  else if (curTopic === "AI") r = r.filter(isAI);
  else if (curTopic !== "全部") r = r.filter(e => (e.topics || []).includes(curTopic));
  if (curVenue !== "全部场馆") r = r.filter(e => e.venue_short === curVenue);
  if (q) r = r.filter(e => match(e, q));
  return r.sort((a,b) => a.start.localeCompare(b.start) || a.name.localeCompare(b.name));
}

/* ---------- 卡片 ---------- */
function cardHTML(e){
  const d = pd(e.start);
  const ai = isAI(e);
  const star = fav.has(e.id);
  const hasRem = !!rems[e.id];
  return `<div class="card${e.status==="ongoing"?" live":""}${e.featured?" feat":""}${hasRem?" hasrem":""}" data-id="${esc(e.id)}">
    <div class="datebox"><div class="m">${d.getMonth()+1}月</div><div class="n">${d.getDate()}</div></div>
    <div class="cardbody">
      <div class="name">${e.featured?'<i class="fbar"></i>':""}${esc(e.name)}</div>
      <div class="meta">
        <span><b>${esc(e.venue_short)}</b>${e.district ? " · " + esc(e.district) : ""}</span>
        ${e.end !== e.start ? `<span>至 ${e.end.slice(5).replace("-","/")}</span>` : ""}
        ${e.featured ? `<span class="tag feat">${esc(e.featured_tag || "重磅")}</span>` : ""}
        ${e.admit && e.admit.level === "trade" ? '<span class="tag trade">限专业</span>' : ""}
        ${admitClosed(e) ? '<span class="tag dead" style="margin-left:0">报名已截止</span>' : ""}
        ${ai ? '<span class="tag topic">AI</span>' : ""}
        ${!e.featured ? `<span class="tag">${esc(e.category)}</span>` : ""}
        ${e.status==="ongoing" ? '<span class="tag live">进行中</span>' : ""}
        ${star ? '<span class="tag fav">已关注</span>' : ""}
      </div>
    </div>
    <svg class="bell" viewBox="0 0 16 16" fill="none">
      <path d="M8 2a3.6 3.6 0 0 1 3.6 3.6c0 3 1.1 4 1.4 4.4H3c.3-.4 1.4-1.4 1.4-4.4A3.6 3.6 0 0 1 8 2z"
            stroke="currentColor" stroke-width="1.3"/>
      <path d="M6.6 12.2a1.5 1.5 0 0 0 2.8 0" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
    </svg>
  </div>`;
}

function relTag(e){
  if (e.status === "ongoing") return {txt:"进行中", cls:""};
  const n = days(e.start);
  if (n === 0) return {txt:"今天", cls:"warn"};
  if (n === 1) return {txt:"明天", cls:"warn"};
  if (n > 1) return {txt:n + " 天后", cls:"gray"};
  return null;
}

function listHTML(list, withGroups){
  if (!list.length) {
    return q
      ? `<div class="empty"><b>没找到相关展会</b>换个关键词试试，比如「机器人」「浦东」「食品」</div>`
      : `<div class="empty"><b>暂无符合条件的展会</b>调整一下上面的筛选</div>`;
  }
  let html = "", last = "";
  for (const e of list) {
    if (withGroups && e.start !== last) {
      last = e.start;
      const d = pd(e.start), r = relTag(e);
      html += `<div class="daygroup"><span class="d">${d.getMonth()+1}月${d.getDate()}日</span>`
            + `<span class="w">${WEEK[d.getDay()]}</span>`
            + (r ? `<span class="rel ${r.cls}">${r.txt}</span>` : "") + `</div>`;
    }
    html += cardHTML(e);
  }
  return html;
}

/* ---------- 时间轴 ---------- */
function renderTimeline(){
  const list = filter(EVENTS);
  return `<div style="height:2px"></div>` + listHTML(list, true)
    + `<div class="foot">数据更新于 ${esc((DATA.updated||"").slice(0,10))} · `
    + `共 ${EVENTS.length} 场<br>来源：国家会展中心 · 新国际博览中心 · 市商务委</div>`
    + `<div class="pad"></div>`;
}

/* ---------- 月历 ---------- */
function renderCalendar(){
  const first = new Date(calY, calM, 1);
  const startPad = first.getDay();
  const dim = new Date(calY, calM + 1, 0).getDate();
  const prevDim = new Date(calY, calM, 0).getDate();

  const map = {};
  for (const e of EVENTS) {
    let d = pd(e.start), end = pd(e.end);
    if (end < d) end = d;
    const cur = new Date(d);
    let guard = 0;
    while (cur <= end && guard++ < 60) {
      const k = YMD(cur);
      (map[k] = map[k] || []).push(e);
      cur.setDate(cur.getDate() + 1);
    }
  }

  const todayStr = YMD(today);
  let cells = "";
  for (let i = 0; i < startPad; i++) {
    cells += `<div class="cell out"><div class="dn">${prevDim - startPad + 1 + i}</div></div>`;
  }
  for (let d = 1; d <= dim; d++) {
    const key = calY + "-" + String(calM+1).padStart(2,"0") + "-" + String(d).padStart(2,"0");
    const evs = map[key] || [];
    const uniq = [...new Set(evs.map(x => x.id))].length;
    const hasFeat = evs.some(x => x.featured);
    const dots = evs.length
      ? `<div class="dots">${(hasFeat ? '<i class="a"></i>' : '<i></i>')}${uniq > 1 ? "<i></i>" : ""}${uniq > 2 ? "<i></i>" : ""}</div>`
      : `<div class="dots"></div>`;
    cells += `<div class="cell${key===todayStr?" today":""}${key===calDay?" sel":""}" data-d="${key}">
      <div class="dn">${d}</div>${dots}${uniq > 2 ? `<span class="cnt">${uniq}</span>` : ""}</div>`;
  }
  const tail = (7 - ((startPad + dim) % 7)) % 7;
  for (let i = 1; i <= tail; i++) cells += `<div class="cell out"><div class="dn">${i}</div></div>`;

  let head = `<div class="calbar">
    <div class="nav" data-step="-1">‹</div>
    <div class="ym">${calY} 年 ${calM+1} 月</div>
    <div class="nav" data-step="1">›</div>
    <div class="today-btn" id="calToday">回到本月</div>
  </div>
  <div class="grid">${["日","一","二","三","四","五","六"].map(w => `<div class="wk">${w}</div>`).join("")}</div>
  <div class="grid" id="calGrid">${cells}</div>`;

  let body = "";
  if (calDay) {
    const list = (map[calDay] || []);
    const seen = new Set(), uniq = [];
    for (const e of list) if (!seen.has(e.id)) { seen.add(e.id); uniq.push(e); }
    uniq.sort((a,b) => a.start.localeCompare(b.start));
    const dd = pd(calDay);
    body = `<div class="daygroup" style="position:static">
        <span class="d">${dd.getMonth()+1}月${dd.getDate()}日</span>
        <span class="w">${WEEK[dd.getDay()]}</span>
        <span class="rel gray">${uniq.length} 场</span></div>`
      + (uniq.length ? uniq.map(cardHTML).join("")
         : `<div class="empty" style="padding:34px 0">这天没有展会</div>`);
  } else {
    body = `<div class="empty" style="padding:34px 20px 20px">点日历上的日期，看当天有哪些展</div>`;
  }
  return head + body + `<div class="pad"></div>`;
}

/* ---------- 关注 ---------- */
function renderFav(){
  const star = filter(EVENTS.filter(e => fav.has(e.id)), true);
  const remList = EVENTS.filter(e => rems[e.id])
    .sort((a,b) => (rems[a.id]||0) - (rems[b.id]||0));
  let html = `<div style="height:6px"></div>`;
  if (!star.length && !remList.length) {
    return `<div class="empty"><b>还没有关注的展会</b>在展会详情里点「关注」，<br>开票或临近时就能在这里找到</div>`;
  }
  if (remList.length) {
    html += `<div class="daygroup" style="position:static"><span class="d">已设提醒</span>
      <span class="rel">${remList.length} 场</span></div>`;
    html += remList.map(e => {
      const t = rems[e.id];
      const d = new Date(t);
      const line = `${d.getMonth()+1}月${d.getDate()}日 ${String(d.getHours()).padStart(2,"0")}:${String(d.getMinutes()).padStart(2,"0")} 提醒`;
      const c = cardHTML(e);
      return c.replace('<div class="meta">', `<div class="meta"><span class="tag live">${line}</span>`);
    }).join("");
  }
  if (star.length) {
    html += `<div class="daygroup" style="position:static"><span class="d">我关注的</span>
      <span class="rel gray">${star.length} 场</span></div>`;
    html += star.map(cardHTML).join("");
  }
  return html + `<div class="pad"></div>`;
}

/* ---------- 主渲染 ---------- */
function isSearching(){ return q.length > 0; }

function render(){
  const main = document.getElementById("main");
  const chipsOn = (tab === "timeline" && !isSearching());
  document.getElementById("kindBar").style.display = chipsOn ? "flex" : "none";
  document.getElementById("chipsTopic").style.display = chipsOn ? "flex" : "none";
  document.getElementById("chipsVenue").style.display = chipsOn ? "flex" : "none";
  if (isSearching() && tab !== "timeline") {
    const list = filter(EVENTS);
    main.innerHTML = `<div class="daygroup" style="position:static">
        <span class="d">搜索「${esc(q)}」</span><span class="rel gray">${list.length} 场</span></div>`
      + listHTML(list, false) + `<div class="pad"></div>`;
    return;
  }
  main.innerHTML = tab === "calendar" ? renderCalendar()
                 : tab === "fav" ? renderFav()
                 : renderTimeline();
  main.scrollTop = 0;
}

/* ---------- 交互 ---------- */
document.querySelector(".tabbar").onclick = e => {
  const el = e.target.closest(".tab"); if (!el) return;
  if (tab === el.dataset.tab) { document.getElementById("main").scrollTop = 0; return; }
  tab = el.dataset.tab;
  document.querySelectorAll(".tab").forEach(t => t.classList.toggle("on", t.dataset.tab === tab));
  render();
  updateBadge();
};

document.getElementById("main").onclick = e => {
  const nav = e.target.closest(".nav");
  if (nav) {
    let m = calM + Number(nav.dataset.step), y = calY;
    if (m < 0) { m = 11; y--; } else if (m > 11) { m = 0; y++; }
    calY = y; calM = m; calDay = null; render(); return;
  }
  if (e.target.id === "calToday") {
    calY = today.getFullYear(); calM = today.getMonth();
    calDay = YMD(today); render(); return;
  }
  const cell = e.target.closest(".cell[data-d]");
  if (cell) {
    calDay = (calDay === cell.dataset.d) ? null : cell.dataset.d;
    render(); return;
  }
  const card = e.target.closest(".card");
  if (card) openDetail(card.dataset.id);
};

document.getElementById("main").addEventListener("scroll", e => {
  document.getElementById("hdr").classList.toggle("stuck", e.target.scrollTop > 4);
}, {passive:true});

/* ---------- 参加办法 ---------- */
// 所有报名通道都关闭了吗（卡片上给出"报名已截止"，避免白跑一趟）
function admitClosed(e){
  const a = e && e.admit;
  if (!a) return false;
  const chans = a.channels || [];
  if (!chans.length) return a.state === "closed";
  return chans.every(c => c.state === "closed" || c.state === "full");
}

// 通道状态：优先用数据里的明确标记，其次按截止日期推算，都没有就标"以公告为准"
function chanState(c){
  if (c.state === "closed") return { t: "已结束", c: "dead" };
  if (c.state === "full")   return { t: "已约满", c: "dead" };
  if (c.state === "open")   return { t: "开放中", c: "ok" };
  if (c.state === "soon")   return { t: "未开始", c: "soon" };
  if (c.deadline) {
    const left = Math.round((pd(c.deadline) - today) / 86400000);
    if (left < 0)  return { t: "已结束", c: "dead" };
    if (left === 0) return { t: "今天截止", c: "soon" };
    return { t: "还剩 " + left + " 天", c: "ok" };
  }
  return c.window ? { t: "以公告为准", c: "soon" } : null;
}

function copyName(s){
  const m = (s || "").match(/「(.+?)」/);
  return m ? m[1] : (s || "");
}

function admitRows(e){
  const a = e.admit;
  if (!a) return "";
  const trade = a.level === "trade";
  const chans = a.channels || [];
  let h = `<div class="row"><div class="k">参加</div><div class="v">`
        + `<span class="tag ${trade ? "trade" : "open"}">${esc(a.kind)}</span>`
        + (a.summary ? `<div class="summary">${esc(a.summary)}</div>`
                     : `<span style="display:inline-block;margin-top:6px">${esc(a.how)}</span>`)
        + `</div></div>`;

  if (chans.length) {
    const rows = chans.map(c => {
      const st = chanState(c);
      const cp = copyName(c.where);
      const off = st && st.c === "dead";
      const w = c.wechat || null;
      const wName = (w && w.name) || cp || "";
      const wType = (w && w.type) || (/小程序/.test(c.where || "") ? "小程序" : "公众号");
      const other = c.where && !/「/.test(c.where) ? c.where : "";
      return `<div class="chan${off ? " off" : ""}">`
        + `<div class="ch">${esc(c.name)}${st ? `<span class="tag ${st.c}">${st.t}</span>` : ""}</div>`
        + (c.who ? `<div class="line">适用：<b>${esc(c.who)}</b></div>` : "")
        + (c.window ? `<div class="line">开放时间：${esc(c.window)}</div>` : "")
        + (wName
            ? `<div class="line wxline">${esc(wType)}：<b>${esc(wName)}</b>`
              + `<button class="mini inline" data-copy="${esc(wName)}">复制名称</button>`
              + (w && w.verified === false ? `<span class="hint"> · 未核实</span>` : "")
              + `</div>`
            : "")
        + (other ? `<div class="line">其它渠道：${esc(other)}</div>` : "")
        + (c.steps ? `<div class="line">路径：${esc(c.steps)}</div>` : "")
        + (c.note ? `<div class="line hint">${esc(c.note)}</div>` : "")
        + `</div>`;
    }).join("");
    h += `<div class="row"><div class="k">通道</div><div class="v">${rows}`
       + `<div class="hint" style="margin-top:6px">点「复制名称」，到微信顶部搜索框粘贴即可找到</div>`
       + `</div></div>`;
  } else if (a.deadline) {
    const left = Math.round((pd(a.deadline) - today) / 86400000);
    const txt = left < 0 ? "已截止" : left === 0 ? "今天最后一天" : "还剩 " + left + " 天";
    h += `<div class="row"><div class="k">截止</div><div class="v">${a.deadline}`
       + `<span class="tag ${left < 0 ? "dead" : "ok"}">${txt}</span>`
       + (left < 0 ? `<br><span class="hint">报名已关闭，现场不受理</span>` : "")
       + `</div></div>`;
  }

  if (a.fee) h += `<div class="row"><div class="k">费用</div><div class="v">${esc(a.fee)}</div></div>`;

  h += `<div class="row"><div class="k">依据</div><div class="v hint">`
     + (a.verified ? "主办方官方公告"
        : (kindOf(e) === "dev"
            ? "按主办方公开信息整理，报名前请再核一次官方公告"
            : "按同类展会通行做法推断，出发前请再核一次主办方公告"))
     + `</div></div>`;
  return h;
}

/* 参加入口：能点一下就去的按钮。
   优先用官网首页发现的预登记页（真入口），其次展会官网本身，最后票务搜索。
   商务委备案页没有报名入口，只作为备案信息弱化展示，不给按钮。 */
function linkKind(e){
  if (e.website_kind) return e.website_kind;
  if (!e.website) return "";
  return e.website.indexOf("sww.sh.gov.cn") >= 0 ? "filing" : "official";
}

function entryRows(e){
  const kind = linkKind(e);
  const dev = kindOf(e) === "dev";
  const sg = e.signup || null;
  const tick = e.tickets || [];
  const btns = [];
  if (sg && sg.url) {
    btns.push(`<button class="btn primary" data-url="${esc(sg.url)}">${esc(sg.label || "在线预登记")}</button>`);
  }
  if (kind === "official" && e.website && !(sg && sg.url === e.website)) {
    btns.push(`<button class="btn${(sg && sg.url) ? "" : " primary"}" data-url="${esc(e.website)}">${dev ? "打开活动页" : "打开展会官网"}</button>`);
  }
  tick.forEach(t => {
    btns.push(`<button class="btn" data-url="${esc(t.url)}">${esc(t.name)}搜票</button>`);
  });
  if (!btns.length) {
    /* 只有二维码的活动没有可点网址，也要明确告诉用户入口在哪，不能让页面看起来没入口 */
    if (sg && sg.qr_only) {
      return `<div class="row"><div class="k">报名</div><div class="v">`
        + `<span class="tag open">${esc(sg.label || "扫码报名")}</span>`
        + `<div class="hint" style="margin-top:6px">该活动只有二维码入口，没有可点击的网址。`
        + `到主办方公告里扫码，或按下方「通道」说明操作。</div>`
        + `</div></div>`;
    }
    return "";
  }

  let hint = "";
  if (dev) hint = "点按钮直接去报名页，部分活动有名额与身份审核";
  else if (sg) hint = "已在该展官网找到预登记页，点按钮直接去登记";
  else if (kind === "official") hint = "官网首页一般有「观众预登记 / 参观登记」，进站后找一下";
  else if (tick.length) hint = "在票务平台搜展会名，看到本场即可买票";

  return `<div class="row"><div class="k">参加入口</div><div class="v">`
    + `<div class="entry">${btns.join("")}</div>`
    + (hint ? `<div class="hint" style="margin-top:6px">${hint}</div>` : "")
    + `</div></div>`;
}

function copyToClipboard(t){
  if (IS_APP && NA.copy) {
    try { NA.copy(t); toast("已复制「" + t + "」"); return; } catch(e) {}
  }
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(t).then(
      () => toast("已复制「" + t + "」"),
      () => toast("复制失败，请手动长按选择"));
  } else {
    toast("请手动长按选择文字");
  }
}

/* ---------- 详情 ---------- */
function fmtMs(ms){
  const d = new Date(ms);
  return `${d.getMonth()+1}月${d.getDate()}日 ${String(d.getHours()).padStart(2,"0")}:${String(d.getMinutes()).padStart(2,"0")}`;
}

function openDetail(id){
  const e = byId(id); if (!e) return;
  const d1 = pd(e.start), d2 = pd(e.end);
  const dur = Math.round((d2 - d1) / 86400000) + 1;
  const halls = e.halls ? e.halls.split("、").filter(Boolean) : [];
  const starred = fav.has(e.id);
  const rem = rems[e.id];
  const n = days(e.start);
  const when = e.status === "ongoing" ? "正在进行" : n === 0 ? "今天开始" : n === 1 ? "明天开始" : n + " 天后开始";

  document.getElementById("panel").innerHTML = `
    <div class="grab"></div>
    <h2>${esc(e.name)}</h2>
    <div class="subline">
      ${e.featured ? `<span class="tag feat">${esc(e.featured_tag || "重磅")}</span>` : ""}
      ${isAI(e) ? '<span class="tag topic">AI 相关</span>' : ""}
      <span class="tag">${esc(e.category)}</span>
      ${e.status === "ongoing" ? '<span class="tag live">进行中</span>' : ""}
    </div>
    <div class="row"><div class="k">时间</div><div class="v">
      ${e.start}${e.end !== e.start ? " 至 " + e.end : ""}<br>共 ${dur} 天 · ${when}</div></div>
    <div class="row"><div class="k">场馆</div><div class="v">${esc(e.venue)}${e.district ? "（" + esc(e.district) + "）" : ""}
      ${halls.length ? "<br>" + halls.length + " 个展馆：" + esc(halls.join("、")) : ""}</div></div>
    ${admitRows(e)}
    ${entryRows(e)}
    ${(e.topics||[]).length ? `<div class="row"><div class="k">主题</div><div class="v">
      ${e.topics.map(t => `<span class="tag topic" style="display:inline-block;margin:0 5px 4px 0">${esc(t)}</span>`).join("")}</div></div>` : ""}
    ${e.organizer ? `<div class="row"><div class="k">主办</div><div class="v">${esc(e.organizer)}</div></div>` : ""}
    ${linkKind(e) === "filing" ? `<div class="row"><div class="k">备案</div><div class="v">
      <a href="#" data-url="${esc(e.website)}">市商务委备案信息（无报名入口）›</a></div></div>` : ""}
    <div class="row"><div class="k">来源</div><div class="v">
      ${e.source.split("+").map(s => SRC[s] || s).join(" · ")}</div></div>
    <div class="row"><div class="k">提醒</div><div class="v" id="remLine">
      ${rem ? "已设置：" + fmtMs(rem) : "未设置"}</div></div>
    <div class="actions">
      <button class="btn ${starred?"on":""}" id="btnFav">${starred ? "已关注" : "关注"}</button>
      <button class="btn ${rem?"on":""}" id="btnRem">${rem ? "取消提醒" : "加提醒"}</button>
    </div>
    <div class="actions2">
      <button class="btn primary" id="btnCal">加入系统日历</button>
    </div>`;

  const sheet = document.getElementById("sheet");
  sheet.classList.add("show");

  document.getElementById("btnFav").onclick = () => {
    if (fav.has(e.id)) { fav.delete(e.id); toast("已取消关注"); }
    else { fav.add(e.id); toast("已关注，可在「关注」里找到"); }
    saveFav(); openDetail(id); render(); updateBadge();
  };

  document.getElementById("btnRem").onclick = () => {
    if (rems[e.id]) { cancelReminder(e.id); openDetail(id); render(); return; }
    addReminder(e);
  };

  document.getElementById("btnCal").onclick = () => addCalendar(e);

  document.querySelectorAll("#panel [data-url]").forEach(a => {
    a.onclick = ev => {
      ev.preventDefault();
      const u = a.dataset.url;
      if (IS_APP && NA.openUrl) NA.openUrl(u); else window.open(u, "_blank");
    };
  });

  document.querySelectorAll("#panel [data-copy]").forEach(b => {
    b.onclick = ev => { ev.stopPropagation(); copyToClipboard(b.dataset.copy); };
  });
}

document.getElementById("sheet").onclick = e => {
  if (e.target.id === "sheet") document.getElementById("sheet").classList.remove("show");
};

/* ---------- 提醒逻辑 ---------- */
function addReminder(e){
  const s = pd(e.start), en = pd(e.end);
  const at = (d, h, m) => new Date(d.getFullYear(), d.getMonth(), d.getDate(), h, m, 0, 0).getTime();
  const prevDay = d => new Date(d.getFullYear(), d.getMonth(), d.getDate() - 1);
  // 按优先级挑第一个还没过去的时间点：开展前 → 开展当天 → 闭展前 → 闭展当天
  const cands = [
    [at(prevDay(s), 20, 0), "开展前一天 20:00"],
    [at(s, 8, 30),          "开展当天 08:30"],
    [at(prevDay(en), 20, 0),"闭展前一天 20:00"],
    [at(en, 8, 30),         "闭展当天 08:30"]
  ];
  const now = Date.now();
  const pick = cands.find(c => c[0] > now);
  if (!pick) { toast("这场展已经结束了"); return; }

  const title = "展会提醒 · " + e.name;
  const text = (e.end !== e.start ? e.start + " 至 " + e.end : e.start)
             + " · " + e.venue_short + "，别忘了去看";

  if (IS_APP && NA.setReminder) {
    let ok = false;
    try { ok = NA.setReminder(e.id, title, text, pick[0]) === "ok"; } catch(err) {}
    if (!ok) { toast("提醒设置失败，请检查通知权限"); return; }
    if (NA.requestNotifPermission) { try { NA.requestNotifPermission(); } catch(err) {} }
  } else {
    rems[e.id] = pick[0];
    try { localStorage.setItem("rems", JSON.stringify(rems)); } catch(err) {}
  }
  loadRems();
  toast("已设置 " + pick[1] + " 提醒");
  openDetail(e.id); render(); updateBadge();
}

function cancelReminder(id){
  if (IS_APP && NA.cancelReminder) { try { NA.cancelReminder(id); } catch(e) {} }
  else {
    delete rems[id];
    try { localStorage.setItem("rems", JSON.stringify(rems)); } catch(e) {}
  }
  loadRems();
  toast("已取消提醒");
  updateBadge();
}

/* ---------- 系统日历 ---------- */
function addCalendar(e){
  const s = pd(e.start);
  const sMs = new Date(s.getFullYear(), s.getMonth(), s.getDate(), 9, 0).getTime();
  const en = pd(e.end);
  const eMs = new Date(en.getFullYear(), en.getMonth(), en.getDate(), 18, 0).getTime();
  const loc = e.venue + (e.district ? "（" + e.district + "）" : "");
  const desc = (e.organizer ? "主办：" + e.organizer + "\n" : "")
             + (e.website ? e.website + "\n" : "") + "来自「上海展会」App";
  if (IS_APP && NA.addCalendar) {
    let r = "";
    try { r = NA.addCalendar(e.name, loc, desc, sMs, eMs); } catch(err) { r = "fail"; }
    toast(r === "ok" ? "已打开日历，确认后即写入" : "没找到可用的日历应用");
  } else {
    toast("请在 App 内使用此功能");
  }
}

/* ---------- 返回键 ---------- */
window.onAndroidBack = function(){
  const sheet = document.getElementById("sheet");
  if (sheet.classList.contains("show")) { sheet.classList.remove("show"); return true; }
  if (q) { qi.value = ""; q = ""; sbox.classList.remove("hasq"); render(); return true; }
  if (tab !== "timeline") {
    tab = "timeline";
    document.querySelectorAll(".tab").forEach(t => t.classList.toggle("on", t.dataset.tab === "timeline"));
    render(); return true;
  }
  return false;
};

/* ---------- 角标 ---------- */
function updateBadge(){
  const n = EVENTS.filter(e => rems[e.id]).length + fav.size;
  let b = document.getElementById("favBadge");
  if (!n) { if (b) b.remove(); return; }
  const tabEl = document.querySelector('.tab[data-tab="fav"]');
  if (!b) { b = document.createElement("div"); b.id = "favBadge"; b.className = "badge"; tabEl.appendChild(b); }
  b.textContent = n > 99 ? "99+" : n;
}

/* ---------- 在线更新 ----------
 * 三层数据：APK 内置兜底 → 手机本地缓存 → 线上 latest.json。
 * manifest 的 version 由内容 sha256 决定，内容没变就不下载大文件。
 * 任何一步失败都静默沿用当前数据，不弹错误、不白屏。
 * 网络走原生桥 SHExpo.fetch，避开 WebView 跨域的不确定性。 */
let ENDPOINTS = REMOTE_ENDPOINTS.slice();
let syncing = false, cbSeq = 0;

function httpGet(url, done){
  if (!IS_APP || !NA.fetch) { done(""); return; }
  const cb = "__expoCb" + (++cbSeq);
  let settled = false;
  const timer = setTimeout(function(){
    if (settled) return;
    settled = true;
    try { window[cb] = null; } catch(e) {}
    done("");
  }, 15000);
  try {
    window[cb] = function(txt){
      if (settled) return;
      settled = true; clearTimeout(timer);
      try { window[cb] = null; } catch(e) {}
      done(txt || "");
    };
    NA.fetch(url, cb);
  } catch(e) {
    if (!settled) { settled = true; clearTimeout(timer); done(""); }
  }
}

function tryEndpoints(i, file, done){
  if (i >= ENDPOINTS.length) { done("", ""); return; }
  const url = ENDPOINTS[i] + "/" + file + "?_=" + Date.now();
  httpGet(url, function(txt){
    if (txt && txt.length > 2) done(txt, ENDPOINTS[i]);
    else tryEndpoints(i + 1, file, done);
  });
}

function validData(o){
  return o && typeof o === "object" && Array.isArray(o.events)
      && o.events.length >= MIN_COUNT
      && o.events.every(e => e && e.id && e.name && e.start);
}

function showNewBar(n){
  const el = document.getElementById("newbar");
  if (!el) return;
  el.innerHTML = '<span>' + (n > 0 ? "新增 " + n + " 场活动，已自动加入" : "数据已更新")
               + '</span><span class="x">✕</span>';
  el.classList.remove("hide");
}
document.getElementById("newbar").onclick = function(){
  document.getElementById("newbar").classList.add("hide");
};

function rebuildDerived(){
  TOPICS = TOPIC_ORDER.filter(t => FIXED.includes(t) || hasT(t));
  VENUES = [...new Set(EVENTS.filter(e => kindOf(e) === curKind).map(e => e.venue_short))];
  if (!TOPICS.includes(curTopic)) curTopic = "全部";
  if (!VENUES.includes(curVenue)) curVenue = "全部场馆";
  updateMeta();
  buildKind();
  buildChips();
}

function applyRemote(o, base){
  const oldIds = new Set(EVENTS.map(e => e.id));
  DATA = o;
  EVENTS = o.events;
  const added = EVENTS.filter(e => !oldIds.has(e.id)).length;
  if (base && ENDPOINTS[0] !== base) {
    ENDPOINTS = [base].concat(ENDPOINTS.filter(x => x !== base));
  }
  rebuildDerived();
  render();
  updateBadge();
  showNewBar(added);
}

function finishSync(silent, ok){
  syncing = false;
  if (!silent) toast(ok ? "已是最新数据" : "暂时无法连接，继续使用本地数据");
}

// 远端时间戳不比本地新就不算更新：本地可能是刚装的新版内置数据
function newerThanLocal(mf){
  const local = String(DATA.generated_at || DATA.updated || "");
  const remote = String((mf && (mf.generated_at || mf.updated)) || "");
  return !(remote && local && remote <= local);
}

function sync(silent){
  if (syncing) return;
  if (!IS_APP || !NA.fetch) { if (!silent) toast("请在 App 内检查更新"); return; }
  syncing = true;
  if (!silent) toast("正在检查更新…");
  tryEndpoints(0, "manifest.json", function(txt){
    let mf = null;
    try { mf = JSON.parse(txt); } catch(e) {}
    if (!mf || !mf.version) { finishSync(silent, false); return; }
    if (Array.isArray(mf.endpoints) && mf.endpoints.length) {
      ENDPOINTS = [...new Set(mf.endpoints.concat(ENDPOINTS))];
    }
    if (mf.version === (DATA.version || "")) { finishSync(silent, true); return; }
    // 防降级：远端生成时间不比本地新就当作没有更新，避免线上还没跟上时把新内置数据打回去
    if (!newerThanLocal(mf)) { finishSync(silent, true); return; }
    tryEndpoints(0, "latest.json", function(raw, base){
      let o = null;
      try { o = JSON.parse(raw); } catch(e) {}
      if (!validData(o) || o.version !== mf.version
          || (mf.count && o.count !== mf.count)) {
        finishSync(silent, false); return;
      }
      if (NA.saveCache) { try { NA.saveCache(raw); } catch(e) {} }
      applyRemote(o, base);
      finishSync(silent, true);
    });
  });
}

function bootSync(){
  // 先读上一次成功下载的缓存，比 APK 内置数据新
  if (IS_APP && NA.loadCache) {
    let cached = "";
    try { cached = NA.loadCache(); } catch(e) {}
    if (cached) {
      try {
        const o = JSON.parse(cached);
        if (validData(o)) { DATA = o; EVENTS = o.events; }
      } catch(e) {}
    }
  }
  rebuildDerived();
  render();
  updateBadge();
  sync(true);
}
document.getElementById("hmeta").onclick = function(){ sync(false); };

bootSync();
</script>
</body>
</html>
"""

out = os.path.join(BASE, "app", "src", "main", "assets", "www", "index.html")
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w", encoding="utf-8") as f:
    f.write(HTML.replace("__DATA__", PAYLOAD))
print("index.html %.1f KB, %d events" % (os.path.getsize(out) / 1024.0, data["count"]))
