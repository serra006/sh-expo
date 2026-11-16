# 上海展会 · Shanghai Expo

上海在办展会与开发者大会的**离线可读、每日自动更新**清单，附带一个 95 KB 不到的 Android App。

三条链路全自动：抓取 → 发布 → 客户端同步。不需要服务器，也不需要人值守。

```
数据源（3 个展馆/政府站点 + 1 份人工清单）
        ↓  每天 05:23（北京时间）GitHub Actions
质量闸门 → 增量比对 → public/latest.json
        ↓  GitHub Pages / jsDelivr / raw.githubusercontent
Android App（WebView + 内置快照）启动即同步
```

## 在线数据

App 会按顺序尝试这几个端点（表随 `manifest.json` 下发，换源不用改客户端）：

| 端点 | 说明 |
|---|---|
| `https://serra006.github.io/sh-expo/public` | GitHub Pages，国内直连可用 |
| `https://cdn.jsdelivr.net/gh/serra006/sh-expo@main/public` | jsDelivr，国内较快 |
| `https://raw.githubusercontent.com/serra006/sh-expo/main/public` | 备用，国内不稳 |

文件：

- `manifest.json` — 版本号、场次数、更新时间（约 470 B，App 先拉它判断要不要下载）
- `latest.json` — 全量数据（约 170 KB）
- `health.json` — 最近一次采集的健康状态

`manifest.json` 的 `version` 由 `events` 与 `calendar` 内容哈希得出。**内容没变版本号就不变**，App 直接跳过下载。报名链接探测这类每天都会变但对用户无意义的字段，已被排除在哈希之外。

## 数据覆盖

| 来源 | 说明 | 量级 |
|---|---|---|
| `NECC` | 国家会展中心（上海）展览/活动/会议排期，分页 | 5~10 |
| `SNIEC` | 上海新国际博览中心按月展会日历 | 10~14 |
| `GOV` | 上海市会展业公共信息服务平台（市商务委备案） | 60~65 |
| `DEV` | 开发者大会人工清单 `data/dev_events.json` | 6 + 9 日历 |

合计约 100 场未结束的展会/活动。多来源命中的同一场会合并，`source` 记为 `GOV+SNIEC` 这种形式。

### 为什么展会能自动抓，开发者大会不能

展会像火车时刻表——展馆官网排期结构化、提前数月公布、可以穷举。开发者大会（Qoder、Trae、WorkBuddy、云栖、WAIC 这类）像朋友聚餐——谁办谁喊，渠道散在公众号文章、活动行、飞书表单、微信群二维码里，提前两三周才公布。

实测过活动行：`robots.txt` 允许抓 `/events`，但列表页是纯 JS 渲染，HTML 里一条活动都没有，必须逆向接口，而接口随时会变。所以这部分走**人工清单**，一年 20~40 场，人工维护准确率远高于任何抓取。

`data/dev_events.json` 有两个键：

- `events[]` — 已确认确切日期的近期活动，字段与 `data/events.json` 一致
- `calendar[]` — 年度大会日历，只有月份没有确切日期（WAIC 7 月、云栖 9 月、GDPS 10 月…），不进列表，界面上单独一块

某场大会公布确切日期后，从 `calendar` 移到 `events` 即可。

## 快速开始

```bash
pip install -r requirements.txt

python fetch.py                    # 抓三个源 → data/events.json（约 3 分钟）
python publish.py --no-upload      # 质量闸门 + 合并大会 → public/
```

`publish.py` 会检查：任一源归零、总量骤降、字段缺失、公众号名是入口描述——任何一项不过就整体判失败，**不覆盖上一版好数据**，同时把原因写进 `health.json`。排障时可加 `--force` 跳过闸门。

配置了 `R2_ACCOUNT_ID` / `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` / `R2_BUCKET` 时会额外上传到 Cloudflare R2；不配就只写本地 `public/`，由仓库托管。

### 只改数据不重抓

```bash
python refit_admit.py      # 重算「参加通道」（公众号、报名方式、费用）
python refit_links.py      # 重算官网/报名/购票链接
python dev_merge.py        # 把开发者大会合进 events_active.json
```

这三个脚本不访问源站，几秒跑完，改文案或补链接时用。

## 构建 APK

不用 Gradle，`apk/build_apk.sh` 是手写流水线（aapt2 → d8 → zipalign → apksigner），Windows 上约 20 秒。

```bash
python apk/build_www.py            # 把 public/ 内嵌进 index.html
bash apk/build_apk.sh 1.9          # 产出 apk/ShanghaiExpo-1.9.apk
node apk/test_www.js               # 95 项断言
```

构建前需要：

- JDK 21（`JAVA_HOME` 必须指向 JDK 而非 JRE，`d8`/`apksigner` 依赖它）
- Android SDK build-tools 36.x、platform 36
- Debug keystore

`build_apk.sh` 里几处不能改的坑：

1. **不能用 aapt2 的 `-A` 打 assets** — Windows 上会写出反斜杠路径，Android `AssetManager` 只认正斜杠，运行时报 `ERR_FILE_NOT_FOUND`。assets 由 `apk/add_assets.py` 用 Python `zipfile` 写入。
2. **assets 目录里不能留备份文件** — 会把整个目录打进包，之前 `index.pre16.html` 就是这么混进去的。
3. **Java 源码变更后必须重编 `classes.dex`** — 只改 HTML 时构建脚本会复用旧 dex，`NA.version()` 不会跟着变。

## App 功能

分两栏：**展会**（94 场）与**开发者大会**（6 场近期 + 9 条年度日历）。

- 时间轴 / 月历 / 关注 三个 Tab，收藏存在本地
- 搜索按名称、场馆、主办方、展馆号
- 详情页给「参加通道」：有预登记页的直接给按钮，没有的显示公众号名 + 复制按钮，只有二维码的明确说「只能扫码」
- 有官网的显示「打开展会官网」，只有备案页的显示灰色「备案（无报名入口）」
- 开发者大会额外显示「核实于 X 月 X 日」，超过 30 天变橙色提示可能已变更
- 报名链接每天探测一次，明确返回 404/410 才标「已失效」并撤掉按钮（超时、403 反爬一律不标）

数据同步策略：App 内置一份快照，启动后拉 `manifest.json`，只有版本号更新才下载 `latest.json`。带防降级——远端比本地旧时不覆盖。

## 目录结构

```
fetch.py                抓 NECC / SNIEC / GOV 三源
publish.py              质量闸门 + 合并大会 + 增量发布  ← 核心
dev_merge.py            本地把 dev_events.json 合进 events_active.json
refit_admit.py          只重算通道字段，不重抓
refit_links.py          只重算链接字段，不重抓
requirements.txt        requests / beautifulsoup4 / boto3
.github/workflows/      每天 21:23 UTC（05:23 北京）采集
data/
  events.json           抓取原始产出
  events_active.json    过滤后的活跃场次（App 构建用）
  dev_events.json       开发者大会人工清单  ← 唯一真源
  snapshots/            每日快照，便于回溯
public/
  latest.json           全量数据
  manifest.json         版本与场次数
  health.json           采集健康状态
apk/
  build_www.py          数据 + 模板 → index.html
  build_apk.sh          手工构建流水线
  test_www.js           前端断言（无浏览器，node 里跑）
  app/src/main/         Android 工程（Java + WebView）
```

## 自动更新

`.github/workflows/collect.yml`，每天 **21:23 UTC = 次日 05:23 北京时间**跑一次。特意避开整点：GitHub 的整点任务排队严重，常延迟 15~60 分钟。

即使质量闸门失败也照样提交 `health.json`，一是保住上一版数据，二是让仓库保持活跃——公开仓库连续 60 天无提交会自动停用定时任务，这步同时防静默断更。

## 已知限制

- **开发者大会的新活动发现不了** — 没有机器可读的源，只能人工加。已配每周一次的搜索任务生成候选，但仍需人确认。
- **改期/取消不会自动同步** — 只能人工核实，这也是详情页显示「核实于 X 月 X 日」的原因。
- **NECC 官网列填充率低** — 约 12% 有官网链接，其余只能给备案页。
- **商务委备案页零外链** — 62 场里大部分没有报名入口，只能显示备案信息。
- **小程序直链不可达** — 微信小程序 scheme 必须开发者自签，第三方拿不到，所以标注小程序名称让用户自己搜。
- **GitHub Actions 跑在美国 IP** — 抓国内站点能用但偶发超时，已加 3 次重试与 12 分钟超时。

## 免责

数据来自各展馆与政府公开页面，仅作信息聚合，**不保证准确性**。参展、报名、购票前请以主办方官方公告为准。开发者大会部分为人工整理，核实日期已标注在详情页。
