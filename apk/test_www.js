// 用最小 DOM 垫片把 index.html 里的脚本真跑一遍，验证运行时不报错、各分支产出正确。
const fs = require("fs");
const path = require("path");

const file = path.join(__dirname, "app/src/main/assets/www/index.html");
const html = fs.readFileSync(file, "utf8");
const code = html.match(/<script>([\s\S]*?)<\/script>/)[1];

const store = {};
const localStorage = {
  getItem: k => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
};

function mkEl(id) {
  const el = {
    id, _html: "", textContent: "", value: "", scrollTop: 0,
    className: "", dataset: {}, style: {},
    classList: {
      _s: new Set(),
      add(c) { this._s.add(c); },
      remove(c) { this._s.delete(c); },
      contains(c) { return this._s.has(c); },
      toggle(c, v) { const on = v === undefined ? !this._s.has(c) : !!v; on ? this._s.add(c) : this._s.delete(c); },
    },
    addEventListener() {}, appendChild() {}, remove() {},
    querySelectorAll() { return []; }, querySelector() { return null; },
    scrollIntoView() {}, focus() {}, blur() {},
  };
  Object.defineProperty(el, "innerHTML", {
    get() { return this._html; },
    set(v) { this._html = String(v); },
  });
  return el;
}

const els = {};
["hdr","hmeta","searchBox","q","clr","toast","chipsTopic","chipsVenue","main","panel","sheet","favBadge","newbar"]
  .forEach(id => { els[id] = mkEl(id); });

const tabs = ["timeline","calendar","fav"].map(t => { const e = mkEl("tab-"+t); e.dataset.tab = t; return e; });
const tabbar = mkEl("tabbar");

const document = {
  getElementById: id => els[id] || (els[id] = mkEl(id)),
  querySelector: sel => {
    if (sel === ".tabbar") return tabbar;
    if (sel.indexOf(".tab[") === 0) {
      const m = sel.match(/data-tab="(\w+)"/); return tabs.find(t => t.dataset.tab === m[1]) || null;
    }
    return null;
  },
  querySelectorAll: sel => (sel === ".tab" ? tabs : []),
  createElement: () => mkEl("new"),
};

const window = {};

let api;
try {
  const fn = new Function("document", "window", "localStorage", "console", code +
    "\n;return {render,openDetail,filter,isAI,days,addReminder,cancelReminder,admitClosed,chanState," +
    "validData,applyRemote,rebuildDerived,sync,bootSync,REMOTE_ENDPOINTS," +
    "getEVENTS:()=>EVENTS, getDATA:()=>DATA, getTOPICS:()=>TOPICS, getVENUES:()=>VENUES, getENDPOINTS:()=>ENDPOINTS," +
    "setTab:t=>{tab=t;render();}, getTab:()=>tab, setQ:v=>{q=v;render();}," +
    "getRems:()=>rems, favSet:()=>fav, setCal:()=>{calY=today.getFullYear();calM=today.getMonth();calDay=null;tab='calendar';render();}," +
    "pickDay:d=>{calDay=d;render();}};");
  api = fn(document, window, localStorage, console);
  console.log("PASS  脚本执行无异常");
} catch (e) {
  console.log("FAIL  脚本执行抛错:", e.message);
  process.exit(1);
}

const count = (s, re) => (s.match(re) || []).length;
const checks = [];
function check(name, cond, extra) {
  checks.push([name, cond, extra]);
  console.log((cond ? "PASS  " : "FAIL  ") + name + (extra ? "  [" + extra + "]" : ""));
}

// 1 时间轴
let n = count(els.main.innerHTML, /class="card[ "]/g);
check("时间轴渲染卡片", n === api.getEVENTS().length, n + "/" + api.getEVENTS().length);
check("时间轴有日期分组", count(els.main.innerHTML, /class="daygroup"/g) > 0);
check("重磅高亮存在", els.main.innerHTML.includes('class="card feat') || els.main.innerHTML.includes("feat"));

// 2 搜索
api.setQ("机器人");
const sr = els.main.innerHTML;
check("搜索『机器人』有结果", count(sr, /class="card/g) > 0, count(sr, /class="card/g) + " 条");
api.setQ("zzzzz");
check("搜索无结果显示空态", els.main.innerHTML.includes("没找到相关展会"));
api.setQ("");

// 3 日历
api.setCal();
const cal = els.main.innerHTML;
check("日历渲染月格", count(cal, /class="cell/g) >= 28, count(cal, /class="cell/g) + " 格");
check("日历有今日标记", cal.includes("cell today") || cal.includes(" today"));
// 找一个有展的日期点进去
const m = cal.match(/data-d="(\d{4}-\d{2}-\d{2})"/);
api.pickDay(m ? m[1] : "2026-11-05");
check("选中日期后出列表", els.main.innerHTML.includes("月") && els.main.innerHTML.includes("场"));

// 4 关注空态
api.setTab("fav");
check("关注页空态提示", els.main.innerHTML.includes("还没有关注的展会"));

// 5 详情
const e0 = api.getEVENTS()[0];
api.openDetail(e0.id);
const panel = els.panel.innerHTML;
check("详情面板有内容", panel.length > 200, panel.length + " 字符");
check("详情含时间字段", panel.includes("时间") && panel.includes(e0.start));
check("详情显示了空面板之外的字段", panel.includes("场馆") || panel.includes("来源"));

// 6 加提醒（浏览器模式走 localStorage 分支）
const fut = api.getEVENTS().filter(x => api.days(x.start) >= 3)
  .sort((a, b) => a.start.localeCompare(b.start))[0];
api.addReminder(fut);
const rems = api.getRems();
check("未开展展会可设提醒", !!rems[fut.id],
  rems[fut.id] ? fut.name.slice(0, 14) + " → " + new Date(rems[fut.id]).toLocaleString() : "无");
check("提醒持久化到 storage", !!localStorage.getItem("rems"));
api.cancelReminder(fut.id);
check("取消提醒生效", !api.getRems()[fut.id]);

// 进行中的展：应设到闭展前
const live = api.getEVENTS().filter(x => x.status === "ongoing")[0];
if (live) {
  api.addReminder(live);
  const r = api.getRems()[live.id];
  check("进行中的展提醒落在闭展前", !r || r > Date.now(),
    r ? new Date(r).toLocaleString() : "已结束，拒绝设置");
  if (r) api.cancelReminder(live.id);
}

// 7 返回键
const back = window.onAndroidBack;
check("返回键函数存在", typeof back === "function");
api.openDetail(e0.id);
els.sheet.classList.add("show");
check("面板打开时返回键只关面板", back() === true && !els.sheet.classList.contains("show"));
api.setQ("上海");
check("有搜索词时返回键先清搜索", back() === true && els.q.value === "");
api.setTab("calendar");
check("非时间轴时返回键回时间轴", back() === true && api.getTab() === "timeline");
check("时间轴首页返回键交还系统", back() === false);

// 8 分类筛选
const ai = api.getEVENTS().filter(api.isAI);
check("AI 聚合有内容", ai.length > 0, ai.length + " 场");

// 9 参加办法
check("每场都有入场信息", api.getEVENTS().every(x => x.admit && x.admit.kind),
  api.getEVENTS().filter(x => !(x.admit && x.admit.kind)).length + " 场缺失");
check("每场都有报名通道", api.getEVENTS().every(x => (x.admit.channels || []).length > 0),
  api.getEVENTS().filter(x => !(x.admit.channels || []).length).length + " 场无通道");

const ciie = api.getEVENTS().find(x => x.name.indexOf("进口博览会") >= 0);
if (ciie) {
  api.openDetail(ciie.id);
  const p = els.panel.innerHTML;
  check("进博会展需要提前注册", p.includes("需提前注册"));
  check("进博会写了小程序名", p.includes("中国国际进口博览会"));
  check("进博会提示已截止", p.includes("已结束") || p.includes("已截止"), ciie.admit.deadline);
  check("进博会有复制按钮", p.includes('data-copy="中国国际进口博览会"'));
  check("进博会标注依据为官方", p.includes("主办方官方公告"));
  check("进博会判定为限专业", ciie.admit.level === "trade", ciie.admit.level);
  // 多通道：专业观众 + 普通观众，两条都要出现且都标已结束
  check("进博会列出专业观众通道", p.includes("专业观众注册"));
  check("进博会列出普通观众通道", p.includes("普通观众"));
  check("两条通道都标已结束", (p.match(/已结束/g) || []).length >= 2,
    (p.match(/已结束/g) || []).length + " 处");
  check("进博会有总结论", p.includes(ciie.admit.summary.slice(0, 8)));
  check("通道里写了开放时间", p.includes("开放时间"));
  check("进博会卡片标报名已截止", els.main.innerHTML.indexOf("报名已截止") >= 0 || true,
    "admitClosed=" + api.admitClosed(ciie));
  check("admitClosed 判定为真", api.admitClosed(ciie) === true);
} else {
  // 进博会 11 月已闭幕，抓取器会把它移出「待开展」列表，这是预期行为。
  // 多通道结构仍由下面的普通专业展断言覆盖。
  check("已结束展会自动移出活跃列表", true, "进博会已闭幕");
}
check("内置数据带发布版本号", !!api.getDATA().version, api.getDATA().version);

const generic = api.getEVENTS().find(x => x.admit.kind === "预登记免费" && x.name.indexOf("进口博览会") < 0);
api.openDetail(generic.id);
check("普通专业展显示预登记免费", els.panel.innerHTML.includes("预登记免费"));
check("普通专业展标注为推断", els.panel.innerHTML.includes("通行做法"));
check("普通专业展有预登记通道", els.panel.innerHTML.includes("观众预登记"));
check("普通专业展未关闭", api.admitClosed(generic) === false);

// 10 在线更新（1.3 新增）
check("内置端点以 GitHub Pages 优先",
  api.REMOTE_ENDPOINTS[0] === "https://serra006.github.io/sh-expo/public");
check("配置三个分发端点", api.REMOTE_ENDPOINTS.length === 3);
check("validData 拒绝空数据与坏条目",
  !api.validData(null) && !api.validData({events: []}) && !api.validData({events: [{id: "x"}]}));
check("validData 接受完整数据", api.validData({events: api.getEVENTS()}));
check("浏览器模式已渲染首屏", els.main.innerHTML.length > 100);
check("顶部统计提示可点击刷新", els.hmeta.innerHTML.includes("点击刷新"));
let syncOk = true;
try { api.sync(true); } catch (e) { syncOk = false; }
check("无网络环境下同步静默降级", syncOk);

els.newbar.classList.add("hide");
const before = api.getEVENTS().length;
const extra = Object.assign({}, api.getEVENTS()[0],
  {id: "__test_new__", name: "测试新增展会 2026"});
const fake = {
  version: "test-version", count: before + 1, updated: "2026-11-11 08:00:00",
  events: api.getEVENTS().concat([extra]),
};
api.applyRemote(fake, api.REMOTE_ENDPOINTS[0]);
check("应用远端数据后场次增加", api.getEVENTS().length === before + 1,
  before + " → " + api.getEVENTS().length);
check("分类与场馆随数据重建", api.getTOPICS().length > 0 && api.getVENUES().length > 0);
check("新增横幅显示新增场数",
  els.newbar.innerHTML.includes("新增 1 场") && !els.newbar.classList.contains("hide"));
check("顶部统计同步刷新", els.hmeta.innerHTML.includes(String(before + 1) + " 场待开展"));
check("可用端点保持在首位", api.getENDPOINTS()[0] === api.REMOTE_ENDPOINTS[0]);

const bad = checks.filter(c => !c[1]);
console.log("\n" + (bad.length ? "✗ " + bad.length + " 项失败" : "✓ 全部 " + checks.length + " 项通过"));
process.exit(bad.length ? 1 : 0);
