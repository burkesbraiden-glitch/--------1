# 童旅记项目开发规则

## 1. 项目定位

正式名称是“童旅记”，禁止重新使用“亲子文化游”。

童旅记是亲子文化旅行学习 App，不是酒店、门票、旅游团、交易平台、普通旅游推荐或社交社区。工作应服务于“路线 → 景点 → 探索 → 任务 → 照片和发现 → 记录”的学习闭环。

## 2. 技术栈

- 前端：经典 uni-app、Vue 3、JavaScript、Pinia、SCSS、Vite。
- 后端：Flask、SQLAlchemy、Flask-Migrate/Alembic、MySQL、PyMySQL。

禁止擅自迁移到 uni-app x、`.uvue`、UTS 或普通 Vue Web SPA。

## 3. 当前一级导航

根导航固定为：**首页、探索、记录、我的**，对应：

```text
/pages/home/index
/pages/explore/index
/pages/record/index
/pages/profile/index
```

不要恢复独立 Route、Plan 或 Task Tab。`route`、`plan`、`tasks`、`explore-detail` 等旧页面可保留为兼容或上下文页面，但不能重新成为主导航。

## 4. 页面职责

- Home：品牌、当前旅程摘要和发现；不要重新放孩子切换条、最近记录或任务列表。
- Explore：唯一主要探索工作台，管理 Route → Day → Stop → Plan → Task。
- Record：只读回顾探索成果，展示任务、照片与笔记；不编辑 Route 或生成 Plan。
- Profile：当前孩子、`activeChild`、孩子管理、账号与设置；不放路线或任务列表。

Logo“绿色小星球 + 童旅记”只允许首页使用，不要复制到 Explore、Record、Profile、任务详情、路线详情、记录详情或设置。

## 5. 领域边界

`Route`、`RouteDay`、`RouteStop` 属于 User，是家庭/账号共享行程结构。Route 不按 child 过滤所有权，也不得为 UI 方便新增 `child_id`。

`ExplorationPlan` 属于 Child，并以 `routeStopId` 关联 RouteStop；Task 属于 Plan；TaskSubmission 属于具体 Task；JourneyRecord 是该 Plan/Child 的探索成果。

切换 `activeChild` 后，孩子仍可看到共享 Route，但绝不能看到其他孩子的 Plan、任务进度、TaskSubmission 或 JourneyRecord。除非用户明确重新设计产品模型，不得改变这条边界。

## 6. activeChild 与 Explore Workbench

`activeChild` 是 Home、Explore 和 Record 必须尊重的孩子级业务上下文：

- Home 不得显示上一个孩子的 in-progress Plan。
- Explore 可以显示共享 Route，但 Plan/Task 必须来自当前孩子。
- Record 只查询和显示当前孩子的记录。
- 不要 fallback 到另一位孩子的 Plan。

Workbench 的正式层级不能简化为 `Route → Day → Task`。选择上下文时，URL 明确参数优先，其次是当前孩子的 in-progress Plan，最后才使用当前实现的 fallback。若仅为读取计划列表，使用 `selectionPolicy: 'none'`，避免全局 `currentPlan` 提前污染 Workbench 上下文。

## 7. 数据真实性

禁止：

- 用静态 Demo、假热度、假消息、假孩子、假用户照片或假 Record 冒充真实业务。
- 用随机网络图片冒充用户成果。
- 将 routeId、planId、childId 写死为生产逻辑。

缺少能力时，应显示真实空状态、隐藏入口或明确说明“准备中”。

## 8. 视觉规则

以 P10.2～P10.5 当前实现为准：暖米白背景、深绿色主操作/状态、深棕或深灰正文，少量橙色仅作强调；真实景点/用户照片优先；用留白与细分割线建立层级；一屏通常只有一个主 CTA。

手机内容最大宽度约 430px；桌面 H5 的移动工作区居中；宽屏 Tabbar 内容与主内容对齐。

禁止 Card 套 Card、所有 section 卡片化、日常胶带/印章/大量星星/大量贴纸、厚阴影、`900` 字重、无意义英文 eyebrow 和假图片。Record 可以有回忆感，但照片本身承担视觉重点，不做 scrapbook 装饰堆砌。

若 `docs/design-system-v2.md` 中仍有五 Tab、所有主操作使用橙色或旧装饰语言等冲突描述，以本文件和当前 P10 实现为准；本任务外不要擅自修改该文档。

## 9. 导航与认证

Root Tab 使用项目当前统一 root-tab 逻辑；Task Detail、Route Detail、Record Detail、Child Switch、Settings 等上下文页面使用 `navigateTo` / `navigateBack`。不要为返回主页面滥用 `reLaunch`；仅 root tab 或 auth 流程确有需要时使用。

Home、Explore、Record、Profile 必须有 session/auth 保护。无有效 session 必须进入登录流程；不得写死 token、绕过 auth、前端假登录，或把 500 吞成空状态。401 与 session expired 使用现有统一会话清理逻辑。

## 10. 数据库与 migration

Development 使用 MySQL；测试环境可使用不同数据库。禁止 DROP DB、TRUNCATE、为测试直接插入生产式业务数据，或对空库 `stamp head` 后跳过 migration。

新开发数据库必须正常 migration，再运行 Attraction 基础目录 seed：

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m flask --app app:create_app db upgrade
.\.venv\Scripts\python.exe scripts\seed_attractions.py
```

`seed_attractions.py` 只初始化 Attraction/AttractionGuide 基础目录。User、Child、Route、Plan、Task、Record 的 QA 数据优先通过真实业务流程创建。

## 11. AI 与外部能力

除非用户明确开启新阶段，不要添加 AI 宠物、小旅 floating widget、AI 对话入口、AI Mock UI 或相关 store/state。

Guide Generator 和 Task Generator 当前是服务端固定模板生成；不得声称已接 OpenAI/LLM。真实音频、微信授权和 R2 存储还需要相应环境配置与端到端验证。

## 12. 开发前流程与范围控制

每次开始任务前：

1. 阅读本文件和当前需求。
2. 运行 `git status --short`，查看最近 commits。
3. 阅读相关现有代码、测试、产品说明和当前阶段设计。
4. 明确领域边界和允许修改的文件后再动手。

当前代码、当前测试和最新用户决策优先于旧 README、旧阶段日志和历史交接。禁止一次性重写项目、顺手改无关页面、删除兼容页只为“整洁”、提前开发未要求功能、粗暴全局替换测试，或为了测试通过而回退最新产品决策。

历史测试与新产品契约冲突时逐项判断：失效 UI contract 可以更新，仍有效的业务 contract 必须保留。

## 13. 测试与 Git

修改前端后至少运行：

```powershell
Set-Location frontend
npm run test:session
npm run build:h5
```

按任务需要运行后端 `pytest`。不得声称未实际运行的测试已经通过；真实业务链路变化时优先补真实 E2E/H5 验收。

除非用户明确要求，不要 commit、push、创建 PR、修改远程或 stage 文件。混合工作区使用精确的 `git add -- <paths>`，禁止 `git add .` 与 `git add -A`。

不要修改、删除或 stage `docs/design-mockups/` 和 `docs/交接文档-2026-10-04.md`，除非用户后续明确授权。
