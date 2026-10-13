# 童旅记

童旅记是一款亲子文化旅行学习 App。它不做酒店预订、门票交易、旅游团、旅游线路交易、普通旅游推荐或社交社区。

产品把一次普通出行组织为一条可回顾的学习路径：

```text
路线 → 景点 → 儿童友好探索任务 → 照片和发现 → 探索记录
```

## 当前产品结构

底部一级导航固定为四项：

| 页面 | 职责 |
| --- | --- |
| 首页 | 品牌入口、当前旅程摘要、目的地与景点发现。品牌 Logo 仅在此处出现。 |
| 探索 | 路线、天、景点、探索计划和任务的执行工作台。 |
| 记录 | 浏览 JourneyRecord 成果档案，包括任务成果、照片与笔记。 |
| 我的 | 当前孩子、孩子切换与管理、账号和设置。 |

路线规划、任务详情、记录详情、孩子切换和设置是上下文页面，不是独立一级 Tab。

## 核心领域模型

```text
User
└── Route
    └── RouteDay
        └── RouteStop
            └── ExplorationPlan
                ├── GuideCard
                └── Task
                    └── TaskSubmission

completed ExplorationPlan
└── JourneyRecord
```

`Route`、`RouteDay` 与 `RouteStop` 是账号/家庭共享的行程结构：`Route` 只绑定 `user_id`，不绑定 `child_id`。`ExplorationPlan` 通过 `routeStopId` 关联一个景点站点，并绑定 `child_id`；`Task`、完成进度、`TaskSubmission` 和 `JourneyRecord` 随该计划隔离。

因此，同一账号下的不同孩子可以看到同一条共享路线，但不能互相看到对方的探索计划、任务进度、任务成果或探索记录。

## 当前已实现功能

- 认证：JWT 会话恢复、退出登录、私有页面登录保护；开发环境支持手机号验证码和 Mock 微信登录，生产认证使用真实微信授权。
- 孩子：孩子列表、创建、编辑、默认孩子与 `activeChild` 切换。
- 路线：路线、天、景点站点与景点目录查询；支持创建、编辑、排序和删除保护。
- 探索：从 `RouteStop` 为当前孩子生成 `ExplorationPlan`，查看计划状态与进度，开始和完成探索。
- 讲解：计划级 `GuideCard` 读取与缺失时生成；讲解音频具备异步任务、播放界面和服务端领域代码。
- 任务：服务端任务集、开始任务、文字笔记、完成任务、受认证保护的图片上传与读取。
- 记录：`JourneyRecord` 创建、编辑、封存、完成任务成果、照片和笔记的详情查看；已封存记录使用稳定快照和受认证保护的记录图片。

GuideCard 与 Task 的内容生成目前是服务端固定模板/规则生成，不是 OpenAI 或其他 LLM 功能。

## 技术栈

前端：经典 uni-app、Vue 3、JavaScript、Pinia、SCSS、Vite、Vitest。

后端：Flask、SQLAlchemy、Flask-Migrate（Alembic）、MySQL、PyMySQL、Pytest。

## 项目目录

```text
frontend/                 classic uni-app 前端、Pinia Store、API 和会话测试
backend/
  app/                    Flask API、模型、服务与 worker
  migrations/             Flask-Migrate / Alembic 迁移
  scripts/seed_attractions.py
docs/                     产品说明、设计规范与参考资料
```

## 本地开发

前端：

```powershell
Set-Location frontend
npm install
npm run dev:h5
```

常用前端命令：

```powershell
npm run build:h5
npm run test:session
```

后端（Windows PowerShell 示例）：

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

后端从 `backend/.env` 读取环境变量；请配置自己的 development MySQL 连接与必要密钥，绝不把密码或真实第三方凭据写入仓库。

## 数据库初始化

Development 使用 MySQL。新开发数据库必须先配置好连接，再正常执行全部 migration，并运行项目标准的 Attraction 基础目录 seed：

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m flask --app app:create_app db upgrade
.\.venv\Scripts\python.exe scripts\seed_attractions.py
```

`Attraction` 是系统基础目录数据；没有运行 seed 时，路线编辑中的景点列表会为空。它不负责创建 User、Child、Route、Plan、Task 或 Record。开发/QA 业务数据应通过正常产品流程建立。

不要在空数据库上只手工把 `alembic_version` 标记为 `head`（例如 `stamp head`）就开始运行。那会造成 revision 表存在、而 `users`、`children`、`routes` 等真实业务表缺失的错误状态。

## 测试与构建

前端：

```powershell
Set-Location frontend
npm run test:session
npm run build:h5
```

后端：

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m pytest
```

当前自动化验证基线（2026-10-12）：前端 56 个测试文件、460 项测试通过；后端 725 项测试通过；H5 构建成功。测试和构建不替代 Flask、MySQL、登录或真实浏览器/真机验收。

## 当前状态

- P10.2：探索工作台完成，路线、天、站点、计划和任务收敛到探索执行流。
- P10.3：首页完成，面向当前孩子展示继续探索、路线入口和景点发现。
- P10.4：记录页完成，围绕真实 JourneyRecord、任务成果、照片和笔记呈现。
- P10.5：我的页完成，支持当前孩子、快速切换、孩子管理、账号与设置入口。
- P10.6：全局 E2E/QA 已完成。已覆盖 development DB/Flask/auth、Attraction seed、Route 账号级共享与 Plan/Task/Record 孩子级隔离、activeChild A→B→A、登录/退出、手机/桌面基础布局，以及普通浏览器的真实照片上传与预览。

## 当前限制

- GuideCard 和 Task Generator 仍是服务端固定模板生成，不是已上线的 LLM/AI 服务。
- 真实讲解音频需要可用的微信、Edge TTS、私有 R2 存储、worker 和相应环境配置；代码存在不等于生产外部链路已验收。
- 当前 Attraction seed 以北京景点目录为主，部分 `coverImage` 为空。
- 设置页中的账号信息编辑尚未提供，当前只展示轻提示。

## 产品原则

- 真实数据优先；不使用静态 Demo 冒充动态业务。
- 不伪造热度、消息、孩子、用户照片或探索记录。
- 缺少能力时展示真实空状态、隐藏入口或明确说明“准备中”。
- AI 功能不得伪装成已经上线的产品能力。
