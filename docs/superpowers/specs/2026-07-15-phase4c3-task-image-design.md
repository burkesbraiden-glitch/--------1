# 童旅记第 4C-3 任务图片前端联调设计

## 目标

将任务图片的上传和显示切换到真实受 JWT 保护的后端接口，同时保持 Remote Task 是任务业务事实的唯一来源。

## 边界

- 不修改 Flask、MySQL、迁移、上传格式规则或存储策略。
- 不新增公开图片 URL，不把 JWT 放入 URL。
- 不恢复 Mock Task、localTaskSessions、本地 status、note 或最终 imagePath。
- 页面不直接访问 storage 中的 token，也不各自实现文件传输。

## 设计

`authenticatedFile` 复用既有 `API_BASE_URL`、`tonglvji_auth` token 来源和认证失效处理。上传通过 `uni.uploadFile` 发送 `image` 字段，且不手动设置 multipart `Content-Type`。H5 下载使用带 Authorization 的 fetch、`cache: no-store`、Blob 与 Object URL；非 H5 使用 `uni.downloadFile`，返回临时文件路径。

`taskStore` 删除 `localTaskDrafts`，新增由 `userId:planId:taskId` 隔离的 `taskImageCache`。缓存保存 `displayPath`、`sourceImageUrl`、`loading`、`error`、`generation`、`cleanup` 和共享 Promise。Remote Task 仅保存后端返回的相对 `record.imageUrl`；Blob URL 或临时路径仅写入展示缓存，并通过 Display Task 的 `record.displayImagePath` 暴露。

上传成功后 Store 依次 upsert Remote Task、失效旧缓存并 revoke 旧 Blob URL、递增对应 generation、认证下载新图片。下载结果仅在用户会话与 generation 仍匹配时写入缓存；过期结果立即执行 cleanup。reset/logout 递增 session epoch、清空缓存、revoke 所有 Blob URL，并阻止所有在途结果写回。

任务详情页用 `pendingPreviewPath` 仅在上传期间即时预览；成功后由 `displayImagePath` 展示认证下载结果。Record 页只读取 `displayImagePath`，并在恢复当前 Plan 后受控触发图片显示缓存，不将显示路径写回记录数据。

## 验证

先以静态集成检查锁定 API、认证、缓存、页面展示和无后端改动的约束；再以 Mock 文件传输流程验证上传替换、并发去重、Plan/User 隔离、generation 乱序、completed 事实保持与 logout 清理。最后运行全部前端检查、H5 build、pytest 和 4B smoke。
