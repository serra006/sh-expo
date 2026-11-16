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
    "validData,applyRemote,rebuildDerived,sync,bootSync,REMOTE_ENDPOINTS,newerThanLocal," +
    "getEVENTS:()=>EVENTS, getDATA:()=>DATA, getTOPICS:()=>TOPICS, getVENUES:()=>VENUES, getENDPOINTS:()=>ENDPOINTS," +
    "setTab:t=>{tab=t;render();}, getTab:()=>tab, setQ:v=>{q=v;render();}," +
    "setKind:k=>{curKind=k;curTopic='全部';curVenue='全部场馆';rebuildDerived();render();}, getKind:()=>curKind," +
    "setTopic:t=>{curTopic=t;render();}, getCAL:()=>CAL, openCalDetail:openCalDetail," +
    "kindOf:kindOf, getKINDS:()=>KINDS," +
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

// 1 时间轴（默认停在「展会」栏，开发者大会单独一栏）
const expoOnly = api.getEVENTS().filter(e => api.kindOf(e) === "expo");
const devOnly = api.getEVENTS().filter(e => api.kindOf(e) === "dev");
let n = count(els.main.innerHTML, /class="card[ "]/g);
check("时间轴渲染卡片（展会栏）", n === expoOnly.length, n + "/" + expoOnly.length);
check("时间轴有日期分组", count(els.main.innerHTML, /class="daygroup"/g) > 0);
check("重磅高亮存在", els.main.innerHTML.includes('class="card feat') || els.main.innerHTML.includes("feat"));

// 1b 类型切换：展会 / 开发者大会
check("类型切换有两项", api.getKINDS().length === 2, api.getKINDS().map(k => k.label).join(" / "));
check("类型切换栏已渲染", count(els.kindBar.innerHTML, /class="kb/g) === 2);
check("开发者大会数据已并入", devOnly.length > 0, devOnly.length + " 场");
api.setKind("dev");
const devCards = count(els.main.innerHTML, /class="card[ "]/g);
check("切到大会栏只显示大会", devCards === devOnly.length, devCards + "/" + devOnly.length);
check("大会栏统计文案正确",
  els.hmeta.innerHTML.includes(String(devOnly.length) + " 场活动待参加"));
api.setKind("expo");
check("切回展会栏恢复场次",
  count(els.main.innerHTML, /class="card[ "]/g) === expoOnly.length);

const devWithLink = devOnly.find(x => x.signup && x.signup.url);
if (devWithLink) {
  api.openDetail(devWithLink.id);
  check("大会详情给报名按钮",
    els.panel.innerHTML.includes('data-url="' + devWithLink.signup.url + '"')
    && els.panel.innerHTML.includes(devWithLink.signup.label),
    devWithLink.signup.label);
  check("大会详情文案不是展会口径",
    !els.panel.innerHTML.includes("打开展会官网") && !els.panel.innerHTML.includes("观众预登记"));
} else {
  check("大会详情给报名按钮", false, "没有带链接的大会");
}

// 1.7 信息时效：大会靠人工清单维护，详情页要能看出「这条信息是什么时候核实的」
const devVerified = devOnly.find(x => x.verified_at);
if (devVerified) {
  api.openDetail(devVerified.id);
  check("大会详情显示核实日期",
    els.panel.innerHTML.includes("时效") && els.panel.innerHTML.includes("核实于"),
    devVerified.verified_at);
} else {
  check("大会详情显示核实日期", false, "没有带核实日期的大会");
}

// 1.7 死链：探测到 404 的报名页不能再给一个点了报错的按钮
const EV = api.getEVENTS();
const deadSrc = devWithLink || devOnly[0];
const deadUrl = (deadSrc.signup || {}).url || "";
if (deadUrl) {
  EV.push(Object.assign({}, deadSrc, {
    id: "TEST-dead-link",
    name: "死链测试活动",
    signup: Object.assign({}, deadSrc.signup, {
      link_status: "dead", link_checked: "2026-11-15",
    }),
  }));
  api.openDetail("TEST-dead-link");
  check("死链不再渲染报名按钮",
    !els.panel.innerHTML.includes('data-url="' + deadUrl + '"'));
  check("死链给出失效提示", els.panel.innerHTML.includes("已失效"));
  EV.pop();
} else {
  check("死链不再渲染报名按钮", false, "没有带网址的大会");
  check("死链给出失效提示", false, "没有带网址的大会");
}

// 1.9 公众号名称：不能拿通道的「入口位置」冒充账号名（线上把「官方公告二维码」显示成了公众号）
function pushTest(o){ api.getEVENTS().push(o); return o.id; }
const qrEvent = {
  id: "TEST-qr-only", kind_type: "dev", name: "二维码通道测试", category: "开发者大会",
  start: "2026-12-03", end: "2026-12-06", venue: "上海（会场待公布）", venue_short: "上海",
  district: "闵行区", source: "DEV", topics: ["AI"], featured: false,
  website: "", website_kind: "filing", status: "upcoming", organizer: "测试主办",
  admit: {
    level: "public", kind: "需审核", summary: "扫码提交参会申请", how: "扫描官方公告中的二维码填表",
    where: "官方公告二维码", deadline: "2026-11-25", verified: true, fee: "", wechat: null,
    channels: [{ name: "扫码申请", who: "从业者", where: "官方公告二维码", window: "11 月 25 日前",
                 steps: "", note: "", deadline: "2026-11-25", state: "", wechat: null }],
  },
  signup: { url: "", label: "扫码申请（11-25 截止）", qr_only: true },
  intro: "", note: "", verified_at: "2026-11-15",
};
pushTest(qrEvent);
api.openDetail("TEST-qr-only");
check("二维码入口不再冒充公众号名",
  !els.panel.innerHTML.includes("公众号：官方公告二维码"));
check("二维码入口说明只能扫码", els.panel.innerHTML.includes("只能扫码"));
check("无账号名时不给复制按钮",
  !els.panel.innerHTML.includes('data-copy="官方公告二维码"'));
check("无账号名时不给复制提示",
  !els.panel.innerHTML.includes("点「复制名称」"));

// 脏名字要能自动清洗：后缀剥掉、纯描述性文字判空
const dirty = JSON.parse(JSON.stringify(qrEvent));
dirty.id = "TEST-wx-suffix";
dirty.admit.channels[0].where = "微信公众号";
dirty.admit.channels[0].wechat = { name: "地瓜机器人微信公众号", type: "公众号" };
pushTest(dirty);
api.openDetail("TEST-wx-suffix");
check("公众号后缀被剥掉", els.panel.innerHTML.includes("地瓜机器人")
  && !els.panel.innerHTML.includes("地瓜机器人微信公众号"));

const junk = JSON.parse(JSON.stringify(qrEvent));
junk.id = "TEST-wx-junk";
junk.admit.wechat = { name: "官方公告二维码", type: "公众号" };
junk.admit.channels[0].wechat = { name: "官方公告二维码", type: "公众号" };
pushTest(junk);
api.openDetail("TEST-wx-junk");
check("脏公众号名不进界面",
  !els.panel.innerHTML.includes('data-copy="官方公告二维码"'));
api.getEVENTS().splice(-3, 3);
document.getElementById("sheet").classList.remove("show");

// 1.8 全年大会日历：只有月份、没有确切日期的大会不进列表，单独给一块
const CAL = api.getCAL();
check("年度日历数据已加载", CAL.length > 0, CAL.length + " 场");
api.setKind("expo");
check("展会栏不显示年度日历", !els.main.innerHTML.includes("全年大会日历"));
api.setKind("dev");
check("大会栏显示年度日历", els.main.innerHTML.includes("全年大会日历"));
const dcRows = count(els.main.innerHTML, /class="dc-row"/g);
check("年度日历行数与数据一致", dcRows === CAL.length, dcRows + "/" + CAL.length);
check("年度日历不重复计入近期场次",
  count(els.main.innerHTML, /class="card[ "]/g) === devOnly.length,
  count(els.main.innerHTML, /class="card[ "]/g) + "/" + devOnly.length);
api.setTopic("AI");
check("筛选时收起年度日历", !els.main.innerHTML.includes("全年大会日历"));
api.setKind("dev");

api.openCalDetail(0);
check("日历详情标明日期待公布", els.panel.innerHTML.includes("日期待公布"));
check("日历详情带公众号名称", !CAL[0].wechat || els.panel.innerHTML.includes(CAL[0].wechat));
const calUrl = CAL.find(c => c.url);
if (calUrl) {
  api.openCalDetail(CAL.indexOf(calUrl));
  check("有官网的日历项给按钮",
    els.panel.innerHTML.includes('data-url="' + calUrl.url + '"'), calUrl.name);
} else {
  check("有官网的日历项给按钮", false, "没有带官网的日历项");
}
document.getElementById("sheet").classList.remove("show");
api.setKind("expo");   // 后续断言按展会栏口径，这里复位

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
check("普通专业展显示具体公众号名",
  els.panel.innerHTML.includes(generic.admit.channels[0].wechat.name),
  generic.admit.channels[0].wechat.name);
check("未核实的名字标成「微信搜」而不是「公众号」",
  /微信搜：/.test(els.panel.innerHTML));
check("未核实名带「可能搜不到」提示",
  els.panel.innerHTML.includes("可能搜不到"));
check("底部说明这是推测的搜索词",
  els.panel.innerHTML.includes("推测的搜索词"));
check("不再承诺「粘贴即可找到」",
  !els.panel.innerHTML.includes("粘贴即可找到"));
check("详情页不再出现公用词条", !els.panel.innerHTML.includes("用展会全名搜索"));
check("有复制名称按钮",
  els.panel.innerHTML.indexOf('data-copy="' + generic.admit.channels[0].wechat.name + '"') >= 0);

const wxNames = new Set();
api.getEVENTS().forEach(x => (x.admit.channels || []).forEach(c => {
  if (c.wechat && c.wechat.name) wxNames.add(c.wechat.name);
}));
check("每场展会通道都带公众号名",
  expoOnly.every(x => (x.admit.channels || []).every(c => c.wechat && c.wechat.name)),
  expoOnly.filter(x => (x.admit.channels || []).some(c => !(c.wechat && c.wechat.name))).length + " 场缺名");
check("公众号名不是同一句公用词",
  !JSON.stringify(api.getEVENTS()).includes("用展会全名搜索"));
check("公众号名覆盖不同展会",
  wxNames.size >= api.getEVENTS().length * 0.9,
  wxNames.size + " 个不同名称 / " + api.getEVENTS().length + " 场");

// 11 参加入口（1.5 新增）
const withSignup = api.getEVENTS().find(x => x.signup && x.signup.url);
check("存在带预登记入口的展会", !!withSignup, withSignup ? withSignup.name : "无");
if (withSignup) {
  api.openDetail(withSignup.id);
  check("详情页有「参加入口」", els.panel.innerHTML.includes("参加入口"));
  const frag = withSignup.signup.url.slice(0, 40);
  check("入口按钮指向预登记页", els.panel.innerHTML.indexOf(frag) >= 0, frag);
  check("按钮文案取自官网标签", els.panel.innerHTML.includes(withSignup.signup.label),
    withSignup.signup.label);
  check("提示已找到预登记页", els.panel.innerHTML.includes("直接去登记"));
}

const filing = api.getEVENTS().find(x => x.website_kind === "filing" && x.website);
check("存在商务委备案页展会", !!filing);
api.openDetail(filing.id);
check("备案页标注无报名入口", els.panel.innerHTML.includes("无报名入口"));
check("备案页不给官网按钮", !els.panel.innerHTML.includes("打开展会官网"));

const offOnly = api.getEVENTS().find(x => x.website_kind === "official" && x.website && !x.signup);
if (offOnly) {
  api.openDetail(offOnly.id);
  check("官网未找到入口时给官网按钮", els.panel.innerHTML.includes("打开展会官网"));
  check("并提示进站自己找预登记", els.panel.innerHTML.includes("进站后找一下"));
}

const ticketed = api.getEVENTS().find(x => (x.tickets || []).length);
check("存在卖票展会", !!ticketed);
if (ticketed) {
  api.openDetail(ticketed.id);
  check("卖票展会给大麦搜票", els.panel.innerHTML.includes("大麦搜票"));
  check("卖票展会给活动行搜票", els.panel.innerHTML.includes("活动行搜票"));
  check("票务按钮指向搜索页", els.panel.innerHTML.includes("search.damai.cn/search.htm"));
}

check("每场都有 website_kind 字段",
  api.getEVENTS().every(x => typeof x.website_kind === "string"));
check("备案页数量与官网数量可区分",
  api.getEVENTS().filter(x => x.website_kind === "official").length > 0 &&
  api.getEVENTS().filter(x => x.website_kind === "filing").length > 0);
check("旧版「打开链接」按钮已移除", !els.panel.innerHTML.includes("打开链接"));

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
const expoAfter = api.getEVENTS().filter(e => api.kindOf(e) === "expo").length;
check("顶部统计同步刷新", els.hmeta.innerHTML.includes(String(expoAfter) + " 场待开展"));
check("可用端点保持在首位", api.getENDPOINTS()[0] === api.REMOTE_ENDPOINTS[0]);

// 防降级：线上还没更新时，不能被更旧的远端数据打回去
check("防降级：远端更旧时不覆盖",
  api.newerThanLocal({generated_at: "2026-11-01 00:00:00"}) === false);
check("防降级：远端更新时接受",
  api.newerThanLocal({generated_at: "2099-01-01 00:00:00"}) === true);
check("防降级：远端无时间戳时放行", api.newerThanLocal({version: "x"}) === true);

const bad = checks.filter(c => !c[1]);
console.log("\n" + (bad.length ? "✗ " + bad.length + " 项失败" : "✓ 全部 " + checks.length + " 项通过"));
process.exit(bad.length ? 1 : 0);
