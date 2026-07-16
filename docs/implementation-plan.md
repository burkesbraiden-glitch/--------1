# 童旅记实施计划

## 第 0 阶段：项目初始化

目标：创建正式经典 uni-app Vue 3 + Vite 前端项目，安装依赖，建立项目根目录文档和后端空目录。

涉及文件：AGENTS.md、README.md、docs/product.md、docs/implementation-plan.md、docs/design-reference/、frontend/、backend/。

完成标准：frontend 可安装依赖并通过 H5 编译；根目录文档齐全；设计参考目录已建立。

禁止修改范围：不制作业务页面，不开发 Flask，不连接 MySQL，不接真实 AI。

## 第 1 阶段：项目结构、公共组件、Mock 数据、Pinia、底部导航、AI 宠物框架

目标：建立前端基础结构，准备公共组件、Mock 数据、状态管理、底部导航和 AI 宠物基础交互。

涉及文件：frontend/src/components/、frontend/src/stores/、frontend/src/mock/、frontend/src/pages.json、frontend/src/App.vue。

完成标准：基础导航、Mock 数据和小旅 peek/open/hidden 状态框架可运行。

禁止修改范围：不实现具体业务页面视觉细节，不接后端，不接真实 AI。

## 第 2 阶段：首页

目标：按 01-home.png 实现首页。

涉及文件：frontend/src/pages/、frontend/src/components/、frontend/src/static/。

完成标准：首页布局、文案、视觉风格、底部导航和小旅状态符合设计参考。

禁止修改范围：不开发计划、任务、记录、我的等其他业务页。

## 第 3 阶段：探索计划、讲解卡

目标：按 02-plan.png 和 03-guide.png 实现探索计划与讲解卡。

涉及文件：frontend/src/pages/、frontend/src/components/、frontend/src/stores/。

完成标准：计划页和讲解卡可从 Mock 数据渲染，基础跳转可用。

禁止修改范围：不开发观察任务、记录页、登录体系。

## 第 4 阶段：观察任务、任务详情

目标：按 04-task-list.png 和 05-task-detail.png 实现观察任务列表和任务详情。

涉及文件：frontend/src/pages/、frontend/src/components/、frontend/src/stores/。

完成标准：任务状态、详情说明和标记完成的 Mock 交互可用。

禁止修改范围：不开发真实上传、后端任务接口、独立 AI 提示卡。

## 第 5 阶段：探索相册记录页面

目标：按 06-record.png 实现最终探索相册手账版记录页面。

涉及文件：frontend/src/pages/、frontend/src/components/、frontend/src/static/。

完成标准：记录页呈现探索相册、儿童手账、拍立得照片、胶带和贴纸风格。

禁止修改范围：不做成普通列表，不接真实图片上传服务。

## 第 6 阶段：登录、我的、孩子档案、收藏、设置

目标：按 07-profile.png 和 08-login.png 实现我的已登录资料页与未登录引导页，并补充孩子档案、收藏、设置入口。

涉及文件：frontend/src/pages/、frontend/src/components/、frontend/src/stores/。

完成标准：登录态 Mock 切换可用，我的页面信息与成长记录结构完整。

禁止修改范围：不接真实 JWT，不开发后端认证接口。

## 第 7 阶段：Flask、MySQL、前后端联调

目标：建立 Flask 后端、MySQL 数据库和前后端联调能力。

涉及文件：backend/、frontend/src/api/、frontend/src/stores/。

完成标准：核心 Mock 数据逐步替换为后端接口，认证使用 JWT。

禁止修改范围：不重写已完成前端页面，不改变产品定位。
