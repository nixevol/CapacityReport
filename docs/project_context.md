# 项目上下文记录

## 2026-06-01：修复前端 npm audit moderate 漏洞

- `frontend/package.json` 增加 `overrides.dompurify=3.4.7`，将 `monaco-editor@0.55.1` 间接依赖的 vulnerable `dompurify@3.2.7` 覆盖到安全版本。
- 未执行 `npm audit fix --force`，因为 npm 建议的自动修复会把 Monaco 降级到 `0.53.0`，属于破坏性方向；override 保持 Monaco 版本不变，风险更小。
- 已验证 `npm audit --json` 返回 0 漏洞，`npm ls monaco-editor dompurify` 显示 `monaco-editor@0.55.1 -> dompurify@3.4.7 overridden`，`npm run build` 通过。

## 2026-06-01：Naive UI 自动按需导入

- `frontend/vite.config.ts` 增加 `unplugin-vue-components`、`unplugin-auto-import` 和 `NaiveUiResolver`，模板中的 `n-*` 组件改为构建期自动按需导入；`dts` 关闭以避免生成额外类型文件。
- `frontend/src/main.ts` 移除 `app.use(naive)` 全量注册，保留脚本中对 `useMessage`、`useDialog`、`darkTheme` 等 Naive UI API 的显式导入。
- 已验证 `npm run build` 通过：主入口 JS 从约 1497KB 降到约 572KB，gzip 从约 415KB 降到约 171KB；剩余大 chunk 主要是已懒加载的 Monaco `ScriptPanel` 和 Swagger `ApiDocs`。
- 注意：`npm install` 报告 2 个 moderate audit 项，未执行 `npm audit fix --force`，避免自动升级引入额外风险。

## 2026-06-01：前端非首页路由懒加载

- `frontend/src/router.ts` 保留首屏 `FileWorkflow` 同步加载，将 `HistoryPanel`、`DatabasePanel`、`SettingsPanel` 改为动态导入，和已有的 `ScriptPanel`、`ApiDocs` 保持一致。
- 已验证 `npm run build` 通过：主入口 JS 从约 1556KB 降到约 1497KB，非首页页面拆成独立小 chunk；`ScriptPanel` 和 `ApiDocs` 仍是独立懒加载重 chunk。
- 当前剩余大 chunk 主要来自 Monaco Editor、Swagger UI 和主包中的 Naive UI/Vue 生态；Monaco/Swagger 已经不影响首屏，若继续压主入口体积，下一步应评估 Naive UI 按需引入。

## 2026-06-01：完善 RJ 自动调度日/周粒度识别

- `app/utils/file_dates.py` 新增文件日期范围解析：`XXX_YYYYMMDDHHMM` 视为单日文件，`XXX_YYYYMMDDHHMM_YYYYMMDDHHMM` 按起止时间展开自然日，结束时间为零点时按右开区间处理。
- `app/services/auto_scheduler.py` 的 RJ 检查改为按目录最新 ZIP 自动识别 `daily` 或 `weekly`：日粒度目录要求目标自然周 7 天都存在，周粒度目录要求有一个 ZIP 覆盖目标自然周；空 RJ 目录继续视为停推并跳过。
- 自动调度普通 4G/5G 目录扫描会排除已配置的 RJ 目录，避免 `expected_directories=[]` 时 RJ 周目录被普通 7 天规则误判阻塞。
- `app/services/remote_download.py` 的调度下载筛选改为使用日期覆盖范围：单日文件只要覆盖目标日即下载，多日/周文件必须覆盖完整目标周才下载，避免 ready 后漏下或误下 RJ 周文件。
- `Configure.json` 将 `RJ/700M/700RJGD`、`RJ/700M/700RJYD` 加入 RJ 数据目录，并补充 `700MRJGD`、`700MRJYD` 字段映射；`processor.py` 避免多个源字段别名映射到同一目标字段时生成重复列。
- 配置上传接口现在会导入/保存 `RJData`，前端类型补充 `rj_data` 和调度状态中的 `granularity` 字段。
- 已验证：后端 AST 语法检查、`Configure.json` JSON 解析、`npm run build`、真实 SFTP 清单识别、MySQL 临时导入 700RJYD 样本并清理测试表均通过；前端构建仅保留既有大 chunk 警告。

## 2026-05-29：新增 RJ 周数据处理功能

- 新增 `RJData` 配置块到 `app/config.py`，支持 `enabled`、`weekly_directories` 和 `table_field_mappings` 配置项，用于管理 RJ 周数据目录和字段映射。
- `app/services/auto_scheduler.py` 新增 `RJWeeklyDirectoryStatus` 数据类和 `_check_rj_weekly_ready()` 方法，支持检查 RJ 周数据目录是否包含目标周的文件。
- 自动调度逻辑改为：现有 7 天目录检查 **且** RJ 周数据检查都满足时才触发处理，两个条件是 AND 关系。
- `app/processor.py` 新增 `_get_field_map_for_table()` 方法和 `_find_rj_data_directories()` 方法，支持 RJ 表使用专用字段映射。
- RJ 数据目录结构：`/CapacityReportData/RJ/2.6G/2.6RJGD/` 和 `RJ/2.6G/2.6RJYD/`，每个目录每周一个 ZIP 文件。
- 目标表名映射：`2.6RJGD` -> `2_6GRJGD`，`2.6RJYD` -> `2_6GRJYD`。
- 字段映射配置：`开始时间`、`结束时间`、`gNBId`、`cellId`、`gNBplmn`、`上下行总流量_GB`。
- `Configure.json` 新增 `RJData` 配置块，包含启用状态、周数据目录列表和表字段映射。
- 已验证：`.venv\Scripts\python.exe -m compileall app` 通过；GD 和 YD 数据字段映射测试成功，6 个字段全部匹配。

## 2026-05-25：新增远程自动调度和每目录 7 天处理窗口

- 新增 `app/utils/file_dates.py`，统一解析文件名中的第一个 `YYYYMMDDHHMM` 或 `YYYYMMDDHHMMSS` 时间戳，并提供按目录筛选最近 7 个自然日文件的工具；本地手动上传和远程下载后的 ZIP、Excel、CSV 处理都会按所在目录只保留最近 7 天文件，未携带日期且同目录没有任何可识别日期时保留兼容。
- `app/services/remote_download.py` 增加远程 ZIP 清单扫描和筛选下载：普通远程处理按每个远程目录下载最近 7 天 ZIP；自动调度触发时按 ready flag 中记录的目标日期精确下载，若没有匹配 ZIP 不会回退全量下载，避免误处理新旧混杂数据。
- `app/config.py` 增加 `RemoteData.auto_scheduler` 配置，包含 `enabled`、`check_interval_hours`、`expected_directories` 和 `week_offset`。自动调度开启时后端会强制 `RemoteData.enabled=True` 和 `auto_delete_source=True`，前端也同步灰显并强制打开相关开关。
- 新增 `app/services/auto_scheduler.py` 后台线程：应用启动后按配置间隔检查 FTP/SFTP 目录，使用本机当前日期计算目标自然周（`week_offset=0` 为上周，`-1` 为上上周），但文件覆盖情况完全以 ZIP 文件名日期为准；全部目录覆盖 7 天后写入 `cache/auto_scheduler/ready.flag`，下一轮检测再触发远程下载并处理。
- 调度成功且远程源文件清理成功后会删除 ready flag；处理失败、触发失败或源文件清理失败会保留 ready flag 供下轮重试。扫描失败会记录 `scan_failed`，连续失败次数通过状态接口返回，前端会显示红色失败状态。
- `app/api/routers/remote.py` 新增 `/api/remote/scheduler/status` 和 `/api/remote/scheduler/trigger`，并将远程处理启动逻辑抽成 `start_remote_processing_job()` 供手动按钮和调度器复用。
- `frontend/src/components/SettingsPanel.vue` 在远程数据源配置中加入自动调度区域：启用开关、检查间隔、目标周期、预期目录维护、调度状态、刷新状态和立即检查。配置下载/上传会随 `RemoteData` 一起携带自动调度配置。
- 已验证：文件名日期解析、目标周计算、每目录 7 天筛选、调度开启强制删除源文件配置、调度日期精确筛选逻辑均通过临时 Python 片段；`.venv\Scripts\python.exe -m compileall app` 与 `npm run build` 通过，前端构建仅保留既有 Vite 大 chunk 警告。
- 后续调整：预期目录可访问但完全没有 ZIP 文件时，自动调度会把该目录标记为 `skipped/已停推`，不再阻塞其他目录就绪；但所有目录都为空时不会写入 ready flag，也不会触发处理。

## 2026-05-25：修复 API Token 指定日期输入不可见

- `frontend/src/components/ApiTokenManager.vue` 中创建/编辑 Token 的到期日期控件从 `n-date-picker` 改为原生 `input[type=date]`，避免日期选择组件在弹窗内出现占位但输入框不可见的问题。
- 原生日期输入继续使用 `YYYY-MM-DD` 字符串绑定到 `tokenForm.expires_at`，后端 `/api/tokens/create` 和 `/api/tokens/update` 请求体不变；仅补充本地样式以匹配当前主题和 Naive UI 表单尺寸。
- 已验证：`npm run build` 和 `.venv\Scripts\python.exe -m compileall app` 通过；浏览器实测 `系统设置 > API Token > 生成 Token > 指定日期` 下日期输入框可见，并可输入 `2026-12-31`。

## 2026-05-25：拆分 API Token 管理和 API 文档

- 前端删除旧 `frontend/src/components/ApiCenter.vue`，拆为 `ApiTokenManager.vue` 和 `ApiDocs.vue`：API Token 管理迁入 `系统设置 > API Token` 独立分页，左侧菜单“API 中心”改为“API 文档”，只展示 Swagger 文档。
- API 文档正式路由为 `/api-docs`，旧 `/api-center` 保留为前端兼容别名；后端 `/api/docs-ui` 改为跳转 `/api-docs`。Swagger UI 仍从登录后可见的 `/api/openapi.json` 加载，Token 传递示例指向系统设置中的 API Token 分页。
- `app/main.py` 的 OpenAPI 后处理增加中文 tag、接口 summary/description、常用请求示例和稳定 operationId；业务 API 声明登录 JWT 或 API Token 鉴权，配置/授权/Token 管理/文档接口仍只声明登录 JWT。Swagger 前端隐藏底部 Schemas 区域，减少噪音。
- 修复登录页按钮点击不触发登录的问题：登录按钮改为显式调用 `submit()`，保留密码框回车提交，并在 loading 时防止重复提交。
- 已验证：`.venv\Scripts\python.exe -m compileall app`、`npm run build` 通过；真实 HTTP 检查未登录 `/api/openapi.json` 返回 401、登录后返回 `CapacityReport API`；浏览器实测点击登录按钮可登录，左侧显示 `API 文档`，系统设置显示 `API Token` 分页，API 文档页可见中文 Swagger 分组。

## 2026-05-23：新增 API Token 和离线 API 文档
- API Token 验收补强：非永久 Token 必须明确传入到期日期，非法或缺失到期日期返回 400；到期、停用、重生成旧 Token 均会拒绝业务 API。已实测 API Token 可执行 `/api/database/execute` 和 `/api/database/table/query`，但不能访问 `/api/tokens` 管理接口。
- `frontend/src/components/ApiCenter.vue` 的 Swagger UI 改为通过 `apiUrl('/api/openapi.json')` 加载文档，并在请求拦截器中只在未手动填写 Authorization 时补登录 JWT；桌面端或配置 `VITE_API_BASE` 时，Try it out 请求会自动补全后端基址，避免相对 `/api/*` 请求打到错误 origin。
- 新增 `app/services/api_tokens.py` 和 `app/api/routers/api_tokens.py`：API Token 存储在运行时 `api_tokens.json`，只保存 HMAC-SHA256 哈希、前后缀、启用状态、到期时间和最近使用信息；完整 Token 仅在创建或重生成时返回一次。`api_tokens.json` 已加入 `.gitignore`。
- `app/auth.py` 增加登录态和访问态解析：登录态只接受 JWT/cookie，业务访问态接受登录 JWT、`Authorization: Bearer <api-token>` 和 `X-API-Token`。Token 管理、系统配置、授权和 API 文档仍要求登录后访问。
- `app/main.py` 的全局鉴权中间件改为 JWT + API Token 双鉴权；业务 API 可由 API Token 调用，`/api/openapi.json` 和 `/api/docs-info` 仅登录后可见。OpenAPI schema 同时声明 `BearerAuth` 和 `ApiTokenHeader`，便于外部系统对接。
- 前端新增 `frontend/src/components/ApiCenter.vue`，侧边栏新增 `API 中心`；页面支持 Token 列表、创建、编辑启停/有效期、重生成、删除、复制一次性完整 Token，并内嵌本地 `swagger-ui-dist` 文档。API 中心懒加载，避免 Swagger UI 影响普通页面首屏。
- 新增前端依赖 `swagger-ui-dist`，并在 `frontend/package.json` 中关闭 Scarf 安装期匿名统计配置，确保运行期和离线部署不依赖外网 CDN。
- 已验证：`.venv\Scripts\python.exe -m compileall app`、`npm run build` 通过；本地服务实测未登录访问 `/api/openapi.json` 返回 401，登录创建临时 Token 成功，API Token 可访问 `/api/database/tables` 且不能访问 `/api/tokens`，登录访问 `/api/openapi.json` 成功，非法到期日期返回 400，临时 Token 已删除。
## 2026-05-22：统一日志框与桌面端下载路径反馈

- 数据处理页菜单从“数据上传”改为“数据处理”，路由标题同步改为“数据处理”。
- 上传/处理日志、历史详情日志和脚本执行日志统一使用分级日志渲染：默认/INFO 跟随主题文字色，SUCCESS 绿色，WARNING 黄色，ERROR 红色；日志框背景和滚动条颜色跟随主题，支持横纵向滚动。
- 数据处理页日志高度改为响应式上限，避免长任务日志把外层页面撑出纵向滚动条。
- 脚本编辑页的手动运行日志移到编辑器下方，编辑器与日志框共享页面高度；脚本运行状态保存在前端全局状态中，切换页面回来可继续轮询或查看上次运行结果，运行结束不自动隐藏日志。
- 桌面端下载完成弹窗会显示保存路径，并提供“打开所在文件夹”；新增 Tauri 命令 `open_path_in_file_manager` 通过系统文件管理器打开下载目录。

## 2026-05-21：桌面端 sidecar 进程改为跨平台管理

- Tauri 桌面端启动/关闭后端 sidecar 不再调用 Windows `netstat`、`tasklist`、`taskkill` 等控制台命令，避免启动和退出时闪过 DOS 窗口。
- 桌面端启动 sidecar 后会在应用数据目录写入 `server.pid`；下次启动前读取该 pid，并通过 `sysinfo` 跨平台确认进程名为 `capareport-server` 后再终止残留进程，pid 被复用为其他程序时不会误杀。
- 关闭桌面端时只使用 Tauri shell 的 `CommandChild.kill()` 停止当前 sidecar，并删除 `server.pid`；若 `9081` 被非本程序占用，则启动前直接报端口占用错误。
- 新增 Rust 依赖 `sysinfo`，仅启用 `system` feature；已验证 `npm run build` 和带临时 sidecar 占位文件的 `cargo check --manifest-path src-tauri\Cargo.toml` 通过，验证产物已清理。

## 2026-05-21：收紧系统设置页头部空间

- 系统设置页移除了内容卡片内重复的“系统设置/更新时间”标题栏，保留外层统一页面标题，减少首屏垂直空间占用。
- 配置更新时间改为页面头部动作区的文本项，显示在“下载配置”按钮左侧；窄屏下沿用全局头部规则隐藏辅助文本。

## 2026-05-21：增加下载完成提示弹窗

- 数据表 CSV/XLSX 导出、历史数据压缩包下载和配置文件下载在下载流程完成后会弹出 Naive UI 成功对话框，使用绿色成功图标提示用户文件已下载完成。
- 提示逻辑统一放在 `frontend/src/composables/downloadFeedback.ts`；桌面端会在 Tauri 原生保存流程确认写入后提示，用户取消保存时不弹完成提示，Web 端会在浏览器下载触发后提示。

## 2026-05-21：排查离线机器桌面端白屏

- 运行时外链扫描确认：`frontend/src`、`app`、`src-tauri/src` 中没有 CDN、在线字体或外网业务接口；桌面端前端只访问本机 `http://127.0.0.1:9081` sidecar，`src-tauri/tauri.conf.json` 的 `https://schema.tauri.app/config/2` 只是编辑器/构建 schema，不参与用户机器运行。
- 离线白屏的主要风险点是 Windows WebView2 Runtime：Tauri 默认 `webviewInstallMode` 为 `downloadBootstrapper`，目标机器没有外网且未预装 WebView2 时，安装或启动阶段可能无法正常创建 WebView。`src-tauri/tauri.conf.json` 已改为 `bundle.windows.webviewInstallMode = { type: "offlineInstaller", silent: true }`，新的 Windows 安装包会内置 WebView2 离线安装器。
- 清理了 `src-tauri/tauri.conf.json` 中误残留的本机构建临时 NSIS `template` 绝对路径；该路径不应进入源码或发布配置。
- 已验证 `npm run build` 和带临时 sidecar 占位文件的 `cargo check --manifest-path src-tauri\Cargo.toml` 通过；构建产物和临时 sidecar 占位文件需在提交前清理。

## 2026-05-21：修复桌面端下载不弹保存路径

- 桌面端不再依赖 WebView 的 `<a download>` 行为保存文件；`frontend/src/api/client.ts` 在 Tauri 环境下会通过 `@tauri-apps/api/core` 调用原生命令，普通浏览器和 Server Portable 仍保留原有 Blob 下载逻辑。
- `src-tauri/src/main.rs` 新增 `download_to_file` 命令：先弹出系统保存对话框，再使用 Rust `reqwest` 按前端传入的 HTTP 方法、URL、Header 和请求体流式请求后端接口，并写入用户选择的路径；用户取消保存时不报错，HTTP 错误会带回前端并继续触发 401 退出登录逻辑。
- 新增依赖 `@tauri-apps/api`、`tauri-plugin-dialog`、`reqwest` 和 `serde`；Tauri schema 文件会因 dialog 插件更新，`src-tauri/gen/schemas/` 仍需保留在版本库中用于 VS Code JSON 校验。
- 已验证 `npm run build`、`.venv\Scripts\python.exe -m compileall app`、`cargo fmt --manifest-path src-tauri\Cargo.toml --check` 和带临时 sidecar 占位文件的 `cargo check --manifest-path src-tauri\Cargo.toml` 均通过；验证后已清理 `frontend/dist`、`src-tauri/target`、`src-tauri/binaries` 和 Python 缓存。

## 2026-05-20：统一端口、升级 3.0.0 并收敛桌面安装行为

- 应用户要求，应用访问端口统一回 `9081`：Server Portable、Docker 宿主机映射、Tauri 桌面 sidecar、桌面前端 `VITE_API_BASE` 和前端 Tauri 兜底 API 地址均使用 `http://127.0.0.1:9081`；桌面版启动前只会清理同名 `capareport-server.exe` 的残留监听进程，避免误杀其它占用 `9081` 的程序。
- 版本统一提升为 `3.0.0`，同步更新后端 `APP_VERSION`、健康检查、侧边栏显示、Tauri 配置和 Cargo 包版本。
- `run.bat` 不再因 `frontend/dist/index.html` 缺失直接退出；缺少前端构建产物时会检查 `npm`、按需执行 `npm ci`，然后自动运行 `npm run build` 再启动后端。
- 桌面版去除 release DevTools：`src-tauri/Cargo.toml` 移除 Tauri `devtools` feature，`tauri.conf.json` 移除窗口 `devtools` 配置，前端在 Tauri 环境下阻止右键浏览器菜单和 `F12`/`Ctrl+Shift+I`。
- Windows NSIS 安装器改为 per-machine，并在未选择自定义安装目录时默认落到 `D:\Program Files\CapacityReport`；如果没有 D 盘，则使用系统 `Program Files\CapacityReport`。`scripts/build.ps1` 构建桌面版时会临时生成 Tauri NSIS 模板并恢复 `tauri.conf.json`，避免旧安装记录把默认路径带回 C 盘。默认授权到期日仍由 `app/services/license.py` 的 `DEFAULT_EXPIRES_ON` 控制。
- 桌面端不再提供服务重启功能：前端移除重启按钮和等待遮罩，后端删除 `/api/service/restart`、`/api/service/status` 以及对应 runtime 重启实现，避免桌面 sidecar 无法可靠自重启时误导用户。
- 登录后连续点击左上角品牌图标 8 次会主动打开授权延期窗口，窗口显示当前激活 key 标签并允许连续提交激活码，每次成功后按新的到期日刷新下一次 key。
- 已验证 `cmd /c scripts\build.bat desktop` 可生成 `dist\desktop\CapacityReport_3.0.0_x64-setup.exe`；静默安装后 `capacity-report-desktop.exe`、`capareport-server.exe`、`Configure.json` 和 `ReportScript.sql` 均位于 `D:\Program Files\CapacityReport`，注册表 `InstallLocation` 指向 D 盘。已启动安装后的桌面程序验证 sidecar `/health` 返回 `3.0.0`，并验证配置、脚本和授权接口可读取；验证后已停止测试进程并清理中间产物。

## 2026-05-20：修复桌面版跨源预检导致配置网络错误

- 桌面版前端访问 `127.0.0.1:19082` 属于 WebView 跨源请求，带 `Authorization` 或上传配置文件时浏览器会先发 `OPTIONS` 预检；`app/main.py` 的 JWT 中间件现在直接放行 `OPTIONS`，让 FastAPI CORS 中间件返回允许头，避免配置读取和配置上传显示“网络错误”。
- 桌面版版本提升为 `2.0.3`，同步更新 `app/main.py`、健康检查、服务状态、Tauri 配置、Cargo 包版本和侧边栏版本号，避免同版本安装包覆盖时难以确认是否装到新包。
- `src-tauri/Cargo.toml` 启用 Tauri `devtools` feature，`tauri.conf.json` 主窗口设置 `devtools: true`；Windows release 桌面包可按 `F12` 或右键打开开发者工具排查真实请求。
- 已用真实 uvicorn 服务验证 `Origin: http://tauri.localhost` 下 `/api/config/full` 和 `/api/config/upload` 的 `OPTIONS` 预检均返回 200，并且登录后 `/api/config/full` 可正常返回；随后执行 `scripts\build.bat desktop` 生成 `dist\desktop\CapacityReport_2.0.3_x64-setup.exe`，静默安装启动后验证 `/health` 返回 `2.0.3`、配置读取正常、脚本读取正常、配置上传返回 200。

## 2026-05-20：修复桌面版残留 sidecar 和卸载用户数据选择

- `src-tauri/src/main.rs` 启动 sidecar 前会先清理占用 `19082` 的旧 `capareport-server` 监听进程，避免卸载/重装或异常退出后连到旧服务；启动后不只检查端口可连接，还会请求 `/health` 返回 HTTP 200 才继续。
- `frontend/src/api/client.ts` 在 Tauri 运行环境下即使构建时未注入 `VITE_API_BASE`，也会兜底使用 `http://127.0.0.1:19082`，并保留短暂 fetch 重试，避免桌面版出现配置页默认空值和脚本页 `Failed to fetch`。
- Windows 桌面包收敛为 NSIS `setup.exe`，不再同时产出 MSI；新增 `src-tauri/windows/nsis-hooks.nsh`，卸载前会尝试关闭桌面进程和 sidecar，卸载后会询问是否删除 `%APPDATA%\com.nixevol.capacityreport` 中的配置、脚本、授权、缓存和日志。
- 已执行 `scripts\build.bat desktop`，产物为 `dist\desktop\CapacityReport_2.0.2_x64-setup.exe`；脚本已自动清理 `dist/.tmp`、`frontend/dist`、`src-tauri/target` 和 `src-tauri/binaries`。
- 已用新 NSIS 包静默覆盖安装并启动桌面版验证：`/health` 正常，`/api/config/full` 读取到 32 个字段映射，`/api/script/content` 成功读取 AppData 下的 `ReportScript.sql`；验证结束后已停止测试启动的桌面和 sidecar 进程。

## 2026-05-20：修复桌面版启动期配置和脚本加载竞态

- 桌面版运行配置和脚本仍从安装包资源 `Configure.json`、`ReportScript.sql` 首次复制到系统 AppData 后读取；安装目录中的 `_up_` 是 Tauri 对 `../` 资源的打包目录，不是后端实际运行目录。
- `src-tauri/src/main.rs` 在启动 Python sidecar 后会等待 `127.0.0.1:19082` 可连接，最多等待 20 秒；如果端口没有起来，会主动杀掉刚启动的 sidecar 并让启动失败，避免前端先加载导致配置页停在默认空表单、脚本页停在“正在加载”。
- `frontend/src/api/client.ts` 对普通 `fetch` 请求增加短暂重试，处理桌面 sidecar 启动或服务重启瞬间的 `Failed to fetch`；上传 XHR 不做自动重试，避免重复上传。
- 已实测当前安装目录 `D:\Program Files\CapacityReport\_up_` 和运行目录 `%APPDATA%\com.nixevol.capacityreport` 均存在配置与脚本，`http://127.0.0.1:19082/health`、`/api/config/full`、`/api/script/content` 均能读取；本次修复的是前端初始请求早于 sidecar 就绪的竞态。
- 已执行 `.venv\Scripts\python.exe -m compileall app`、`npm run build` 和带临时 sidecar 占位文件的 `cargo check --manifest-path src-tauri\Cargo.toml`，均通过；生成产物随后清理。

## 2026-05-20：修复登录失败误提示会话过期

- `frontend/src/api/client.ts` 不再把 `/api/login` 的 401 响应当作全局会话过期处理，登录失败会按后端真实错误显示“账号或密码错误”。
- 已登录业务接口遇到 401 时仍会清理本地 token 并切回登录页，但 `AppShell` 不再额外弹出全局“登录已过期”提示，避免组件自身错误提示和全局提示同时出现。
- 默认登录密码仍由 `app/auth.py` 定义为 `Capacity`，大小写敏感；如本地 `auth.ini` 未修改，输入小写 `capacity` 会按正常登录失败处理。
- 已执行 `npm run build`，构建通过；前端构建仅保留 Vite 大 chunk 提示，生成产物随后清理。

## 2026-05-20：增加按 ZIP 数据日期校验的使用期限限制

- 新增 `app/services/license.py` 和 `/api/license/status`、`/api/license/activate`：本地 `license.dat` 用 XOR+HMAC 方式加密保存到期日期，缺失时自动初始化为 `2026-06-20`，文件已加入 `.gitignore`。
- 授权校验不读取系统日期；本地上传处理和远程下载完成后的处理入口会遍历任务目录下 ZIP 文件名，提取 `YYYYMMDDHHMM` 或 `YYYYMMDDHHMMSS` 时间戳并取最大日期作为数据日期，超过授权到期日则任务失败并返回 `LICENSE_EXPIRED` 详情。
- 激活码为当前到期日期 `YYYY/MM/DD` 字符串的 SHA-256 hex；每次激活只按当前加密文件里的到期日校验，成功后顺延 30 天，因此旧激活码不能重复顺延。
- `frontend/src/components/FileWorkflow.vue` 在任务因授权过期失败时弹出激活框，显示 `key: YYYY/MM/DD`，输入激活码成功后本地上传任务会继续处理，远程任务会重新发起远程下载处理。
- 如果任务中没有 ZIP，或 ZIP 文件名没有可识别时间戳，当前实现会写入警告并跳过授权日期比对，避免误伤直接 CSV/Excel 上传流程；如需强制所有数据都必须带 ZIP 日期，可在 `check_processing_allowed()` 中收紧该策略。
- 已执行授权逻辑临时目录验证、`.venv\Scripts\python.exe -m compileall app`、`uvx --offline ruff check .` 和 `npm run build`，均通过；前端构建仅保留 Vite 大 chunk 提示，生成产物已清理。

## 2026-05-19：配置按请求实时重载
- `app/state.py` 新增 `reload_config()` 和 `current_config()`，后端接口不再长期依赖启动时的 `state.config` 快照；读取配置、下载配置、数据库接口、健康检查、本地处理、远程处理和脚本执行入口都会从 `Configure.json` 重新加载最新配置。
- 配置保存类接口会先重载当前文件再修改对应配置块并保存，避免用户手工更新 `Configure.json` 后，被某个单项保存接口用旧内存配置覆盖。
- 本地/远程处理任务启动时会读取一次最新配置并作为任务快照传入 `DataProcessor`；任务运行过程中不再反复重载，避免处理中途改配置导致同一任务前后规则不一致。
- 已执行 `.venv\Scripts\python.exe -m compileall app`、`uvx --offline ruff check .` 和 `npm run build`，均通过；前端构建仅保留 Vite 大 chunk 提示。

## 2026-05-19：补全字段映射配置
- 当前本地 `Configure.json` 的 `ExtractField` 已按旧版可用映射补全：`基站名称` 增加 `ENBFunction名称`，`ERAB流量` 增加 `ERAB流量(新高负荷)_1538186901014-7-0`，`上行流量_GB/下行流量_GB` 增加 `上行流量(GB)/下行流量(GB)`。
- 4G/5G 数值字段显式补回 `Type: float/int`，避免依赖 SQL 脚本推断类型；`AppConfig.load()` 已验证能读取 32 个字段映射和正确的 `SheetFilter`。
- 修改配置时需要注意 Windows PowerShell 管道的中文编码问题；如果要脚本化写入 `Configure.json`，优先从已有 UTF-8 JSON 读取并用 Unicode escape 合并，避免把中文字段写成 `????`。

## 2026-05-19：清理生成 CSV 并支持历史原始数据下载
- `DataProcessor` 现在会追踪 ZIP 解压出的 CSV 和 Excel 转换生成的 CSV，只有这些处理过程中生成的临时 CSV 会在对应 CSV 成功导入后自动删除；原始 ZIP、Excel 和用户本来上传/远程下载得到的原始 CSV 不会被误删。
- ZIP 解压从 `extractall()` 改为逐条安全解压，会跳过越界路径条目，并在解压 CSV 时登记为后续可清理的临时文件。
- `POST /api/history/download` 会校验历史任务目录必须位于 `cache/` 下，任务完成后才能下载；接口将整个历史工作目录压缩为 ZIP 返回，并通过 `BackgroundTask` 在响应结束后删除临时压缩包。
- `frontend/src/components/HistoryPanel.vue` 在历史列表的“详情”左侧增加“下载”按钮，下载时显示 loading，未完成任务禁用下载，避免重复点击和下载不完整的历史数据。
- 已执行 `.venv\Scripts\python.exe -m compileall app`、`uvx --offline ruff check .` 和 `npm run build`，均通过；本次未启动浏览器或 headless Chrome。

## 2026-05-19：调整数值异常值归零和完成后日志高度

- `DataProcessor` 数值字段清洗策略从异常值写入 `NULL` 改为写入 `0`：空串、`-`、`--`、长短横线、`NA/N/A/NULL/NONE/NAN/\N` 以及其它无法转数值的文本都会归零，正常 `0` 不受影响。
- 数值格式继续清理千分位逗号、全角逗号、半角/全角百分号和空白；例如 `12,345.123` 会导入为 `12345.123`，`95%`/`95％` 会导入为 `0.95`。
- `frontend/src/components/FileWorkflow.vue` 在任务完成或失败后给处理进度区增加 `finished` 状态，`frontend/src/styles.css` 让完成后的日志框使用自适应最大高度，避免上传区恢复显示后日志仍按运行中高度撑开页面。
- 已执行数值转换样例验证、`.venv\Scripts\python.exe -m compileall app`、`uvx --offline ruff check .` 和 `npm run build`，均通过。

## 2026-05-19：修复 CSV 导入阶段数值截断错误

- `DataProcessor` 仍会根据 `ReportScript.sql` 的 `MODIFY COLUMN` 提前把业务数值字段建成 `INT/FLOAT`，但数值清洗改为返回真正的 Python `None/int/float`，避免 pandas `<NA>` 或异常文本被 PyMySQL 当作字符串写入数值列。
- 数值字段导入前会把空串、`-`、`--`、长短横线、`NA/N/A/NULL/NONE/NAN/\N` 等源 CSV 占位符转为数据库 `NULL`，正常 `0` 保留为 `0`；逗号/全角逗号、半角/全角百分号和空白仍按数值格式清理。
- 该问题本质是新版提前按 SQL 类型建表后，MySQL 严格模式会在 CSV 导入阶段拒绝脏数值；旧版多为字符串先落库，所以不会在导入阶段出现 `Data truncated for column`。
- 已执行数值转换样例验证、`.venv\Scripts\python.exe -m compileall app` 和 `uvx --offline ruff check .`，均通过。

## 2026-05-19：优化处理进度阶段显示和日志跟随

- `ProcessLogger` 新增轻量阶段回调，`DataProcessor.process()` 会在远程下载后依次上报 `extracting`、`converting`、`importing`、`scripting`、`completed/failed` 阶段。
- `/api/process/status` 和 `/api/task/status` 返回当前 `stage`，本地上传处理和远程下载处理都通过 `state.processing_tasks` 与全局任务锁同步阶段，前端轮询即可实时显示“远程下载中 / 解压数据中 / 上传数据中 / 运行脚本中”等状态。
- `frontend/src/components/FileWorkflow.vue` 的处理进度卡片新增“保持最新 Log”勾选框，勾选后新日志到达会自动滚动到日志底部；当前任务提示不再显示原始阶段码，改为中文阶段文本。
- 已执行 `.venv\Scripts\python.exe -m compileall app`、`uvx --offline ruff check .` 和 `npm run build`，均通过。

## 2026-05-19：清理后端冗余代码和未用依赖

- `app/database.py` 移除未使用的 SQLAlchemy 连接池、`engine` 属性、`dispose()` 空释放路径和未引用的 `delete_rows()`；数据库访问统一保留现有 PyMySQL 上下文连接。
- `app/api/routers/database.py`、`app/api/routers/health.py` 和 `app/processor.py` 同步去除无效 `dispose()` 调用，避免保留没有实际资源释放意义的样板代码。
- `requirements.txt`、`run.bat` 和 `README.md` 移除 SQLAlchemy 依赖和说明；`build/build.py` 清理无用端口常量、内联导入和宽泛异常捕获。
- 已清理本地 `.ruff_cache/` 与重复的 `ReportScript.sql.bak`；已执行 `.venv\Scripts\python.exe -m compileall app build`、`uvx ruff check .`、`uvx vulture app build --min-confidence 80` 和 `npm run build`，均通过。

## 2026-05-19：移除旧版 HTML 前端和双端口托管

- 删除 `frontend_old/` 旧版 HTML/CSS/JS 前端及其本地 Monaco 资源，项目只保留 Vue 3 新前端。
- `app/main.py` 移除旧版前端托管、`/old` 路由、`9082` 端口和双 socket 分流逻辑，运行时只监听 `9081` 并托管 `frontend/dist`。
- `run.bat`、`build/Dockerfile`、`build/docker-compose.yml`、`build/build.py`、`build/README.md` 和 `README.md` 同步移除旧版端口说明及 `19082 -> 9082` 映射。
- 已执行 `.venv\Scripts\python.exe -m compileall app build`，旧版引用扫描未发现剩余可执行入口。

## 2026-05-19：修复数据管理导出下拉选择不触发弹窗

- `frontend/src/AppShell.vue` 将页头下拉动作从模板事件表达式 `@select` 改为 `:on-select` 回调属性，确保 Naive UI 下拉菜单选择 CSV/XLSX 后会真正执行页面动作。
- 修复数据管理页点击“导出”下拉项后 CSV/XLSX 表选择弹窗不显示的问题。
- 已执行 `npm run build`，构建通过；构建只保留 Vite 原有大 chunk 提示。

## 2026-05-19：优化数据管理导出入口和弹窗宽度

- `frontend/src/composables/pageHeader.ts` 和 `frontend/src/AppShell.vue` 为页面顶部动作支持 Naive UI 下拉菜单，按钮内显示下拉箭头。
- `frontend/src/components/DatabasePanel.vue` 将顶部“导出 CSV / 导出 XLSX”两个按钮合并为一个“导出”下拉按钮，点击后选择 CSV 或 XLSX 再进入对应表选择弹窗。
- CSV 和 XLSX 导出弹窗改为固定 420px 内的响应式宽度，避免在宽屏下铺满整页；表选择列表增加边框和背景，视觉上更集中。
- 已执行 `npm run build`，构建通过；构建只保留 Vite 原有大 chunk 提示。

## 2026-05-19：调整数据管理导出交互并支持多表 XLSX

- `frontend/src/components/DatabasePanel.vue` 将导出入口移到页面顶部，并放在“删除全部表”按钮左侧；内容区工具栏只保留刷新、清空、删除当前表。
- 点击“导出 CSV”会弹出全部表单选弹窗，用户选择一张表后下载 CSV；点击“导出 XLSX”会弹出全部表多选弹窗，用户可选择多张表并下载同一个 XLSX。
- `app/api/routers/database.py` 的 `/api/download` 支持 `table_names`，XLSX 会按表名分 sheet 写入同一工作簿，sheet 名会兼容 Excel 的非法字符和 31 字符限制；CSV 仍限制单表导出。
- `frontend/src/api/client.ts` 的 POST 下载会优先使用后端 `Content-Disposition` 文件名，便于多表导出使用服务端生成的文件名。
- 已执行 `.venv\Scripts\python.exe -m compileall app` 和 `npm run build`，均通过；构建只保留 Vite 原有大 chunk 提示。

## 2026-05-19：优化数据表导出临时文件清理

- `app/api/routers/database.py` 的 `/api/download` 导出接口增加格式校验，只允许 `csv` 和 `xlsx`。
- 导出文件仍临时写入 `cache/`，但 `FileResponse` 发送完成后会通过 `BackgroundTask` 自动删除；写入失败时也会清理半成品文件，避免导出残留占用服务器磁盘。
- 已清理 `cache/` 中旧的导出缓存文件 2 个，仅保留处理历史目录和 `history.json`。
- 已执行 `.venv\Scripts\python.exe -m compileall app`，编译检查通过。

## 2026-05-19：调整上传框操作按钮为换行显示

- `frontend/src/components/FileWorkflow.vue` 移除上传框操作区里无效的 `<br>`，避免在 flex 布局中形成异常间距。
- `frontend/src/styles.css` 将 `.upload-zone-actions` 改为纵向 flex 布局，使“或者点击选择文件”和“远程下载并处理”按钮固定分两行显示。
- 已执行 `npm run build`，构建通过；本次按用户要求未启动浏览器或 headless Chrome。

## 2026-05-19：调整连接配置页卡片布局

- `frontend/src/components/SettingsPanel.vue` 将连接配置页改成左列堆叠“数据库配置”和“处理历史保留”，右列显示“远程数据源”，避免右侧远程数据源卡片高度把处理历史保留卡片挤到很下面。
- `frontend/src/styles.css` 新增 `.settings-connection-stack`，左列卡片之间使用固定 18px 间距。
- 已执行 `npm run build`；已通过本机 Chrome DevTools 验证设置页中数据库配置与处理历史保留同列显示，间距为 18px，远程数据源位于右列。

## 2026-05-19：新增处理历史保留配置并完善配置导入导出

- `app/config.py` 新增 `HistoryRetention` 配置块，包含 `enabled` 和 `keep_count`；`keep_count=0` 表示不保留已结束处理历史，关闭开关时不自动删除历史。
- `app/history.py` 新增按保留数量清理已结束历史的能力，只清理 `completed/failed` 记录及其 `cache/<task_id>` 工作目录，不删除 `pending/processing` 记录。
- `app/api/routers/tasks.py` 和 `app/api/routers/remote.py` 在本地上传处理、远程下载并处理任务结束后自动应用历史保留规则。
- `app/api/routers/config.py` 新增 `/api/config/history-retention` 保存接口；配置下载改为从当前内存配置生成完整 JSON，确保导出的配置始终包含 `RemoteData` 和 `HistoryRetention`；配置上传也会恢复这两个配置块。
- `frontend/src/components/SettingsPanel.vue` 在连接配置页新增“处理历史保留”卡片，可设置自动清理开关和保留最近次数。
- 已执行 `.venv\Scripts\python.exe -m compileall app`、临时目录历史清理验证、配置导入导出验证和 `npm run build`；已用本机 Chrome DevTools 验证设置页新增卡片可见。

## 2026-05-19：调整上传页远程下载入口

- `frontend/src/components/FileWorkflow.vue` 将“远程下载并处理”按钮移动到拖拽上传框内部，删除独立的“远程自动化”卡片，上传页首屏只保留一个主要操作区域。
- 远程入口说明“从已配置的 FTP/SFTP 目录递归下载数据，然后自动开始处理。”改为按钮 hover tooltip 展示；按钮点击使用事件阻止冒泡，避免触发拖拽框的本地文件选择逻辑。
- `frontend/src/styles.css` 清理远程自动化卡片样式，新增拖拽框内操作区样式。
- 已执行 `npm run build`；已通过本机 Chrome DevTools 验证 `/upload`：远程按钮位于拖拽框内，外部远程卡片 DOM 数量为 0，tooltip 文案正常显示。

## 2026-05-19：修复规则映射窄宽度滚动

- `frontend/src/styles.css` 将系统设置的规则映射区域改为 tab 内部滚动容器，避免宽度或高度不足时被 `overflow: hidden` 裁切导致 `Sheet 过滤规则` 卡片不可达。
- 浏览器宽度不足触发单列布局时，规则映射区按 `Sheet 过滤规则` 在上、`字段映射配置` 在下排列，字段映射卡片限制高度并继续使用内部字段列表滚动。
- 已执行 `npm run build`；已通过本机 Chrome DevTools 以约 1074px 视口验证 `/settings` 规则映射页：Sheet 卡片可见、容器可纵向滚动、文档没有横向溢出。

## 2026-05-19：移除数据管理表格重复横向滚动条

- `frontend/src/components/DatabasePanel.vue` 移除了上一版额外添加的 `.database-horizontal-scrollbar` 外置滚动条和同步滚动逻辑，避免与 Naive UI DataTable 自带横向滚动条同时显示。
- 数据表仍保留 `scroll-x` 和列最小宽度计算，由 Naive UI 原生表格滚动条负责横向浏览，字段结构折叠头继续保留“字段结构 / 收起字段结构”状态文案。
- 已执行 `npm run build`；已通过本机 Chrome DevTools 验证 `/database` 中外置滚动条 DOM 数量为 0，表格自身仍存在横向溢出滚动。

## 2026-05-19：修复数据管理表格滚动和字段结构收起

- `frontend/src/components/DatabasePanel.vue` 为数据表增加明确的 `scroll-x` 宽度和底部外置横向滚动条，滚动条会与 Naive UI 表格内部横向滚动位置双向同步，避免字段结构区域或分页区域遮挡表格底部横向滚动入口。
- 字段结构区域从默认 `n-collapse` 改为受控折叠头，展开后标题显示“收起字段结构”，再次点击恢复“字段结构”，并使用本地图标箭头表示展开状态。
- 字段结构明细使用内部滚动容器限制高度，数据表主体保持 flex 占位，避免展开字段结构后挤掉分页或整页出现不必要滚动。
- 已执行 `npm run build`；已通过本机 Chrome DevTools 验证 `/database` 中表格横向滚动条可见且与表格滚动同步，字段结构展开/收起文案正常切换。

## 2026-05-19：压缩系统设置页布局高度

- `frontend/src/styles.css` 调整系统设置页为固定高度布局，外层 `settings-workspace` 减小 padding 并隐藏溢出，避免主内容区出现整页滚动条。
- 连接配置页 `.settings-section-grid` 作为 tab 内部滚动容器，浏览器高度变小时只滚动连接配置内容，不裁切远程数据源表单。
- 字段映射配置卡片在规则映射页中占满可用高度，卡片内容区使用 flex 固定 header/footer，字段列表通过内部纵向滚动条浏览，避免主页面滚动或内容溢出。
- Naive UI 当前卡片内容区 DOM class 为 `.n-card-content`，样式同时兼容 `.n-card__content`；字段映射项必须 `flex: 0 0 auto`，否则列表项会被 flex 压缩而无法形成真实滚动高度。

## 2026-05-19：拆分系统设置页并支持远程源文件自动清理

- `frontend/src/components/SettingsPanel.vue` 的系统设置改为 Naive UI Tabs：连接配置页放数据库配置和远程数据源，规则映射页放 Sheet 过滤规则和字段映射配置，修改密码独立一页，避免设置内容堆在一个长页面。
- `RemoteData` 配置新增 `auto_delete_source` 开关；前端在远程数据源配置中显示“处理成功后删除源文件”，默认关闭。
- `app/services/remote_download.py` 新增远程源文件清理能力，下载阶段会记录本次实际下载的远程文件路径；自动清理只删除这些文件，不删除目录，也不会删除处理期间新进入远程目录的文件。
- `app/api/routers/remote.py` 在远程下载并处理成功后才会执行源文件清理；清理失败只写入警告日志，不改变已完成的数据处理结果。
- 已执行 `.venv\Scripts\python.exe -m compileall app` 和 `npm run build`，均通过；未启动浏览器或 headless Chrome。

## 2026-05-18：新增 FTP/SFTP 远程自动化处理

- `Configure.json` 新增 `RemoteData` 配置，包含启用状态、协议、主机、端口、用户名、密码、远程目录、FTP 被动模式、超时时间和源文件自动清理开关；`app/config.py` 会兼容旧配置并在保存时写回该配置块。
- 新增 `app/services/remote_download.py`，FTP 使用标准库 `ftplib`，SFTP 使用 `paramiko`，会递归下载远程目录下的全部文件和文件夹到本地任务缓存目录。
- 新增 `app/api/routers/remote.py`，`POST /api/remote/test` 用于测试远程连接，`POST /api/remote/start` 会创建历史任务、下载远程数据并复用 `DataProcessor` 完成现有处理流程。
- `frontend/src/components/SettingsPanel.vue` 新增“远程数据源”配置卡片，支持 FTP/SFTP 切换、保存和测试连接；`frontend/src/components/FileWorkflow.vue` 新增“远程下载并处理”入口。
- 远程任务启动后会把全局任务阶段设置为 `downloading`，前端处理进度页会显示“远程下载中...”，下载完成后再切换为既有数据处理流程。
- 新增依赖 `paramiko`，当前 `.venv` 已执行 `uv pip install -r requirements.txt`；已执行 `.venv\Scripts\python.exe -m compileall app` 和 `npm run build`，均通过；未启动浏览器或 headless Chrome。

## 2026-05-18：完善服务重启交互和运行时兼容

- `frontend/src/AppShell.vue` 的重启按钮点击后会先弹出确认框，确认后显示全屏“正在重启服务”遮罩和旋转加载动画，避免用户重复操作。
- 重启请求发出后前端会轮询 `/api/service/status`，服务恢复时自动刷新页面；重启过程中请求中断会被视为正常情况继续等待。
- `app/api/routers/service.py` 和 `app/services/runtime.py` 统一重启逻辑：优先使用 supervisor 重启，失败时退回进程退出；Windows 本地依赖 `run.bat` 循环拉起，容器环境会识别 Docker/containerd/k8s 并交给 supervisor 或容器重启策略拉起。
- `/api/service/status` 返回值新增 `container` 字段，用于前端或排障区分容器运行时。
- 已执行 `.venv\Scripts\python.exe -m compileall app` 和 `npm run build`，均通过；未启动浏览器或 headless Chrome。

## 2026-05-18：修正字段映射标题换行

- `frontend/src/styles.css` 调整设置页字段映射卡片头部布局，“字段映射配置”和字段数量标签不再被搜索框挤压换行。
- 字段搜索框改为弹性宽度，优先占用剩余空间，并保留最小宽度和最大宽度约束。
- 已执行 `npm run build`，构建通过；未启动浏览器或 headless Chrome。

## 2026-05-18：优化数据管理表列表和导出入口

- `frontend/src/components/DatabasePanel.vue` 的 MySQL 表列表顶部新增“表”标题和刷新图标按钮，刷新按钮复用 `loadTables()` 并在加载中显示 loading，避免重复刷新。
- 数据表导出从独立 CSV/XLSX 按钮改为 Naive UI 下拉按钮，用户先选择 CSV 或 XLSX 格式再下载。
- 导出请求期间按钮显示 loading 和当前格式文案，并禁用下拉入口，避免大数据表导出等待期间被重复点击。
- 已执行 `npm run build`，构建通过；未启动浏览器或 headless Chrome。

## 2026-05-18：修复数值字段转换失败

- `app/processor.py` 会从 `ReportScript.sql` 的 `ALTER TABLE ... MODIFY COLUMN ... float/int` 自动补全缺失的字段类型提示，配置中未标 `Type` 的数值字段在导入阶段也会按数值清洗和落库。
- 数值清洗只处理格式问题：空值保留为 NULL 后由脚本 `IFNULL` 归零，千分位逗号、中文逗号、百分号、空格和制表符会被移除，正常数值保持不变，正常 0 不再被误判为空值。
- 执行 SQL 脚本时仍保留 MySQL 严格模式；在 `ALTER` 转数值前会对目标表的相关数值列做一次保险清洗，兼容已经导入过的旧字符串表。
- SQL 语句执行失败后不再继续执行后续语句，避免前置 ALTER 失败后继续产生大量 `Unknown column` 和临时表不存在的级联错误，并让任务正确进入失败状态。

## 2026-05-18：修正历史详情日志滚动条颜色

- `frontend/src/styles.css` 为历史详情 `colored-log-panel` 单独设置滚动条颜色，避免继承全局 hover 颜色后在深色日志背景里不可见。
- 日志框滚动条轨道使用深色，滑块和 hover 状态使用更亮的灰蓝色，同时补充横向/纵向滚动条和 corner 样式。
- 已执行 `npm run build`，构建通过；未启动浏览器或 headless Chrome。

## 2026-05-18：优化历史详情日志查看

- `frontend/src/components/HistoryPanel.vue` 的历史详情“处理日志”标题右侧新增复制按钮，点击后复制当前详情日志文本，优先使用 Clipboard API，失败时回退到 textarea 复制。
- 历史详情日志不再使用 `n-log`，改为自定义 `colored-log-panel`，日志框固定高度并同时支持横向和纵向滚动，不自动换行。
- 日志行按内容识别级别并着色：`INFO` 为蓝色，`SUCCESS/COMPLETED` 为绿色，`WARN/WARNING` 为黄色，`ERROR/FAILED` 为红色。
- 已执行 `npm run build`，构建通过；未启动浏览器或 headless Chrome。

## 2026-05-18：切换为圆形侧边栏收缩触发器

- `frontend/src/AppShell.vue` 的 `n-layout-sider` 收缩触发器从 `show-trigger="bar"` 改为 `show-trigger="arrow-circle"`，恢复为 Naive UI 文档中侧栏右侧居中的圆形箭头按钮样式。
- 侧边栏收缩状态仍通过 `handleSidebarCollapsed()` 写入 `localStorage.sidebarCollapsed`。
- 已执行 `npm run build`，构建通过；未启动浏览器或 headless Chrome。

## 2026-05-18：恢复侧边栏原生收缩触发器

- `frontend/src/AppShell.vue` 移除顶部标题栏里的自定义汉堡收缩按钮，改用 Naive UI `n-layout-sider` 的 `show-trigger="bar"` 原生触发器。
- 侧边栏收缩状态仍写入 `localStorage.sidebarCollapsed`，刷新页面后保持用户上次的展开/收缩状态。
- `frontend/src/styles.css` 清理自定义 `.sidebar-toggle` 样式，避免顶部标题栏出现额外按钮。
- 已执行 `npm run build`，构建通过；未启动浏览器或 headless Chrome。

## 2026-05-18：修正折叠侧边栏菜单图标居中

- `frontend/src/styles.css` 的折叠侧边栏菜单项强制改为 flex 居中布局，避免 Naive Menu 折叠时透明文本列继续占据 grid 空间导致图标偏左。
- 折叠态下隐藏菜单文本列和箭头列，并让图标容器自身水平垂直居中，保持选中背景和图标中心对齐。
- 已执行 `npm run build`，构建通过；未启动浏览器或 headless Chrome。

## 2026-05-18：优化历史详情弹窗信息布局

- `frontend/src/components/HistoryPanel.vue` 打开历史详情后会自动调用 `/api/history/size` 计算占用，不再需要用户点击“计算占用”按钮。
- 历史详情基础信息从 Naive UI `n-descriptions` 表格改为自定义键值列表，统一为左侧标题、右侧值，长路径和值会自动换行。
- 占用计算期间显示“计算中...”，失败时显示“计算失败”并保留错误 toast。
- 已执行 `npm run build`，构建通过；未启动浏览器或 headless Chrome。

## 2026-05-18：数据管理页切换时刷新表列表

- `frontend/src/components/DatabasePanel.vue` 在数据管理页激活时会重新执行 `loadTables()`，确保从其他页面切回时左侧表列表拉取最新状态。
- 离开数据管理页时会清空表列表、当前选中表和表数据，避免已删除的表在下次进入前短暂残留。
- 表列表请求增加 `tableLoadToken`，忽略离开页面后返回的旧请求，防止过期响应把已清空的列表重新写回。
- 已执行 `npm run build`，构建通过；未启动浏览器或 headless Chrome。

## 2026-05-18：合并数据管理页快速导入检测入口

- `frontend/src/components/DatabasePanel.vue` 移除数据库状态卡片里的独立“重新检测”文字按钮，把刷新动作合并到“快速导入”的状态徽标上。
- 点击“可用 / 未启用 / 检测中”徽标会自动重新检测并刷新状态；成功不弹 toast，失败仍显示错误提示。
- 数据库状态卡片去掉为底部按钮预留的额外内边距，布局更紧凑。
- 已执行 `npm run build`，构建通过；未启动浏览器或 headless Chrome。

## 2026-05-18：处理任务运行时隐藏上传区域

- `frontend/src/components/FileWorkflow.vue` 新增 `taskInProgress` 计算状态；当存在活动任务或任务状态未完成/失败时，上传区和已选文件列表不再渲染。
- 上传文件阶段仍保留已选文件和上传进度；后端处理任务开始后页面只显示处理进度卡片和日志，避免已完成上传列表继续占据首屏。
- 已执行 `npm run build`，构建通过；未启动浏览器或 headless Chrome。

## 2026-05-18：修复主题按钮图标和折叠侧栏版本显示

- `frontend/src/AppShell.vue` 的主题切换按钮现在根据 `themeName` 动态显示 `MoonOutline` 或 `SunnyOutline`，切换主题后图标和标题同步变化。
- 侧边栏底部版本信息拆分为版本标签、版本号和 Power by 文案；折叠侧边栏时只保留纯版本号 `v2.0.2`，隐藏“版本：”和 Power by。
- 已执行 `npm run build`，构建通过；未启动浏览器或 headless Chrome。

## 2026-05-18：修复登录页回车提交

- `frontend/src/components/LoginView.vue` 的登录按钮改为原生 submit 类型，继续复用 `n-form` 的 `@submit.prevent` 登录流程。
- 密码输入框增加 `@keydown.enter.prevent="submit"` 兜底，用户输完密码按回车即可触发登录，无需手动点击按钮。
- 已执行 `npm run build`，构建通过；未启动浏览器或 headless Chrome。

## 2026-05-15：取消数据管理页初始化成功提示

- `frontend/src/components/DatabasePanel.vue` 进入页面时仍会自动执行数据库连接检测和数据库信息刷新，但连接成功不再弹出 toast，避免切换到数据管理页时产生无意义提示。
- 用户手动点击“重新检测”时仍保留成功提示；连接失败或接口异常仍会显示错误 toast。
- 已执行 `npm run build`，构建通过；未启动浏览器或 headless Chrome。

## 2026-05-15：优化新版前端图标和侧边栏选中态

- `frontend/src/composables/pageHeader.ts` 的页头动作图标从 emoji 字符串改为 Vue 组件，页面按钮统一传入 `@vicons/ionicons5` 图标组件，构建后随前端资源本地打包，适合内网运行。
- `AppShell.vue` 的折叠侧边栏按钮、主题切换按钮和各页面页头动作已移除 emoji 图标；当前前端源码中仅保留主品牌图标 `📊`。
- `styles.css` 优化侧边栏菜单选中态：展开态使用浅色背景、品牌色描边和左侧短标记，折叠态收敛为居中的 40px 图标块，避免选中背景过宽。
- 本次只执行 `npm run build` 做构建验证，未按用户要求启动浏览器或 headless Chrome。

## 2026-05-15：修复新版前端夜间模式组件颜色

- 新增 `frontend/src/composables/theme.ts` 作为前端共享主题状态，统一读写 `localStorage.theme` 并同步 `document.documentElement[data-theme]`。
- `App.vue` 的 `n-config-provider` 现在会在夜间模式下使用 Naive UI `darkTheme`，修复 `n-card`、`n-input`、`n-form`、`n-menu`、`n-button` 等组件仍按亮色主题渲染的问题。
- `AppShell.vue` 的主题切换改为调用共享主题逻辑，避免 AppShell 和 Naive Provider 各自维护主题状态。
- `styles.css` 补充工作卡片、卡片标题、表单标签、菜单图标和菜单文字颜色兜底，防止局部组件样式覆盖暗色文本。
- 已执行 `npm run build`，构建通过，仅有 Monaco/Vite 大 chunk 体积警告；已用 headless Chrome 打开新版 `/settings` 并预置 `theme=dark` 验证：页面、卡片标题、表单标签、输入框文字、字段映射标题和顶部按钮均为暗色主题可读颜色。

## 2026-05-15：对齐新版前端主体布局并修复全局拖拽默认行为

- 新版 Vue 前端主体内容继续按旧版 `frontend_old/` 的工作区布局对齐：上传页保留旧版上传区尺寸和文件列表结构，数据库页恢复左侧表列表 + 右侧数据区，设置页恢复左右列，脚本页恢复编辑器容器和底部状态栏。
- `frontend/src/composables/pageHeader.ts` 新增页面顶部副标题和动作注册机制；各页面把原本散落在页面内部的主要动作注册到 `AppShell` 顶栏，避免每个页面重复实现标题栏。
- `AppShell.vue` 在捕获阶段统一拦截带 `Files` 的 `dragover/drop` 默认行为，修复文件拖到新版页面空白处时浏览器打开文件或弹出下载的问题；真正的文件处理仍由上传区自己的 `drop` 事件完成。
- 上传区 `FileWorkflow.vue` 明确使用 `.prevent.stop` 处理拖拽事件，并继续支持文件和目录拖拽；目录读取使用 `webkitGetAsEntry()` 递归遍历，文件路径按相对路径去重。
- 已执行 `npm run build`，构建通过，仅有 Monaco/Vite 大 chunk 体积警告；已用 headless Chrome 验证新版 `/upload` 上传区位于 `x=252,y=88,width=1156,height=220`，拖到页面空白处不会跳转，拖到上传区会加入 `drag-test.csv`。

## 2026-05-15：恢复新版数据库页左右工作区布局

- `frontend/src/components/DatabasePanel.vue` 已从纵向卡片堆叠改回旧版主体布局：左侧固定 240px 数据表列表，右侧为表数据面板，左下角显示数据库版本和快速导入状态。
- 数据库连接状态不再占用页面顶部；“重新检测”保留在左下状态块中，表列表刷新和删除全部放在左侧列表顶部。
- 右侧表数据区在未选择表时显示“请选择左侧的数据表”，选择表后显示表名、总行数、刷新、CSV、XLSX、清空、删除、数据表格、字段结构和分页。
- 已执行 `npm run build`；并用 headless Chrome 对照旧版 `http://127.0.0.1:9082/` 与新版 `http://127.0.0.1:9081/database`，确认两边数据库主体均为横向 flex，左栏宽 240px，右侧内容区占用剩余宽度。

## 2026-05-15：修复旧版前端未登录闪烁

- `frontend_old/js/app.js` 现在会在首页初始化前检查登录 token；未登录时直接跳到旧版登录页，避免首页继续初始化并反复请求 API 造成未授权提示闪烁。
- 旧版前端鉴权统一兼容 `capacity_report_token` 和旧 key `token`：请求优先读取新版 key，登录页会同时写入两个 key，并继续写入 `token` cookie。
- 旧版 API 401、XHR 上传 401 和退出登录都会清理两个本地 token key 及 cookie，并跳转到 `/login.html`；通过 `/old/...` 路径访问旧版时会跳转到 `/old/login.html`。
- 已用 headless Chrome 验证：清空本地存储后访问 `http://127.0.0.1:9082/` 会进入 `http://127.0.0.1:9082/login.html`；按本机 `auth.ini` 登录后回到旧版首页，`/api/cache/size` 携带 token 调用返回 200。

## 2026-05-15：新版上传页对齐旧版布局并恢复拖拽上传

- `frontend/src/components/FileWorkflow.vue` 的上传页内容区已按旧版 `frontend_old/index.html` 的上传结构重排，保留新版侧边导航和顶部标题栏，只对齐页面主体中的上传区、文件列表、上传进度和处理日志布局。
- 上传区支持点击选择文件，也支持把文件或文件夹直接拖拽到页面；目录拖拽使用 `DataTransferItem.webkitGetAsEntry()` 递归读取，`readEntries()` 会循环读取完整批次，兼容 Chrome 目录拖拽一次只返回部分条目的情况。
- 上传文件统一过滤 `.zip`、`.xlsx`、`.xls`、`.csv`，路径会归一化为 `/`，并按相对路径去重；文件状态显示为等待上传、上传中、已完成或失败。
- 旧版对照端口仍为 `9082`，新版端口仍为 `9081`；已用 headless Chrome 对比 `9082/` 与 `9081/upload`，新版上传框尺寸、虚线边框、圆角和文案与旧版基本一致，并通过模拟拖拽 `drag-test.csv` 验证文件列表能正常出现。
- 构建验证命令为 `cd frontend && npm run build`；当前只存在 Vite 大 chunk 体积警告，构建本身通过，`frontend/dist/` 仍按 `.gitignore` 作为本地构建产物处理。

## 2026-05-15：拆分新旧前端访问端口

- `python -m app.main` 现在由同一个 FastAPI 进程同时监听 `9081` 和 `9082`，共享后端运行状态、任务锁和 API。
- `9081` 固定服务新版 Vue 3 前端，`9082` 固定服务 `frontend_old/` 旧版 HTML/CSS/JS 前端；旧版页面仍通过 `/old/...` 加载本地 Monaco 等静态资源。
- `app.main:app` 保留为新版单端口 ASGI 实例，`app.main:old_app` 保留为旧版单端口 ASGI 实例，`app.main:split_app` 用于按请求端口切换前端。
- `run.bat`、`supervisord.conf`、Dockerfile、Docker Compose 和离线构建脚本已同步新旧端口：本地为 `9081/9082`，容器宿主机映射为 `19081/19082`。

## 2026-05-15：增加旧版前端对照入口和新版路由

- 从旧提交 `54773f547f6fcb853d73785f05ff5ac39ab2e5f5` 恢复原生 HTML/CSS/JS 前端到 `frontend_old/`，包含旧版 `index.html`、`login.html`、样式、脚本和本地 Monaco 资源。
- 后端在 `app/main.py` 中通过 `/old` 和 `/old/...` 托管 `frontend_old/`，旧版静态资源统一改为 `/old/...` 前缀；旧版页面仍复用当前 `/api/...` 接口，便于和新版直接对比。
- 新版 Vue 前端新增 `vue-router`，页面路径为 `/upload`、`/history`、`/database`、`/script`、`/settings`；菜单切换会更新浏览器地址，刷新时由 FastAPI SPA fallback 返回新版入口，不再固定回到主页。
- `frontend/dist/` 仍是本地构建产物，只用于运行验证，不进入版本库；源码运行时需要先在 `frontend/` 执行 `npm install` 和 `npm run build`。

## 2026-05-15：恢复前端工作台交互质量

- 前端工作台布局重新对齐旧版 `54773f547f6fcb853d73785f05ff5ac39ab2e5f5` 的信息架构：左侧导航、顶部标题栏、紧凑后台式内容区，导航项使用“数据上传 / 处理历史 / 数据管理 / 脚本编辑 / 系统设置”。
- `ScriptPanel.vue` 不再使用普通 textarea，改为 `monaco-editor` SQL 编辑器，保留脚本读取、保存、执行和状态轮询接口；支持 SQL 高亮、行号、缩略图、光标行列状态和未保存状态。
- Monaco 通过 Vue 异步组件按需加载，避免脚本编辑器依赖进入首屏主包；Vite worker 类型由 `frontend/src/vite-env.d.ts` 提供。
- `SettingsPanel.vue` 的字段提取配置恢复为结构化树状配置：字段名、字段类型、提取来源列表、搜索、增删和去重保存，不再要求用户直接编辑 JSON。
- 新增前端运行依赖 `monaco-editor`，构建时仍会生成 `frontend/dist/`，该目录继续作为构建产物忽略，不进入版本库。

## 2026-05-15：修复 Windows 启动脚本编码问题

- `run.bat` 改为纯 ASCII 输出，并规范为 CRLF 行尾，避免 Windows `cmd` 在 PowerShell 中执行 UTF-8 中文批处理时把提示文本解析成碎片命令。
- 启动脚本仍使用 `.venv\Scripts\python.exe`、检查 Python 依赖和 `frontend/dist/index.html`，实际启动方式保持 `python -m app.main` 不变。
- 后续如需中文启动提示，优先放到 PowerShell 脚本或应用日志中，不建议直接写入 `.bat`。

## 2026-05-15：后端拆分与前端迁移

### 当前架构

- 后端入口收敛到 `app/main.py`，只负责创建 FastAPI 应用、注册中间件、注册路由和托管前端构建产物。
- API 按业务拆分到 `app/api/routers/`：
  - `auth.py`：登录和修改密码。
  - `upload.py`：上传会话和文件上传。
  - `tasks.py`：任务锁、处理启动、处理状态。
  - `history.py`：历史记录、日志和记录删除。
  - `database.py`：数据库测试、表查询、表维护和导出。
  - `config.py`：配置读取、保存、上传和下载。
  - `cache.py`：缓存大小统计。
  - `script.py`：SQL 脚本读取、保存和执行。
  - `health.py`：健康检查。
- 运行时共享状态放在 `app/state.py`，包括配置实例、历史管理器、处理任务、上传会话和全局任务锁。
- 登录、密码文件和 Token 逻辑放在 `app/auth.py`，继续使用本地 `auth.ini`。
- 文件大小等工具函数放在 `app/utils/files.py`。

### 前端

- 旧 `static/` 原生 HTML/CSS/JS 已替换为 `frontend/`。
- 前端技术栈为 Vue 3 + TypeScript + Vite + Naive UI。
- 构建产物位于 `frontend/dist`，由 FastAPI 根路由托管；`/assets` 映射到 `frontend/dist/assets`。
- 未构建前端时，后端会返回 503，并提示执行 `cd frontend && npm install && npm run build`。
- Vite 开发服务器将 `/api` 和 `/health` 代理到后端 `http://localhost:9081`。

### 部署与运行

- Windows 本地运行使用 `run.bat`，优先使用 uv 创建的 `.venv\Scripts\python.exe`。
- `run.bat` 会检查 Python 依赖和 `frontend/dist/index.html`，缺少前端产物时要求先构建前端。
- Docker 构建改为多阶段：
  - `node:22-slim` 阶段安装前端依赖并执行 `npm run build`。
  - `python:3.13.11-slim` 阶段安装后端依赖，复制应用代码，再复制前端构建产物。
- `.dockerignore` 只排除 `frontend/node_modules`、`frontend/dist` 等本地产物，不再排除完整前端源码。

### 依赖与清理

- Python 依赖保留当前代码实际使用项：`fastapi`、`uvicorn[standard]`、`python-multipart`、`pymysql`、`cryptography`、`pandas`、`openpyxl`、`chardet`、`supervisor`。
- 已移除未使用的 `sqlparse`、`aiofiles`、`python-dateutil`。
- 旧静态目录、根目录打包产物、日志和 Python 编译缓存属于可清理产物，不应提交。

### 注意事项

- 当前项目按每周整包替换使用，不维护旧版 API 兼容层；但核心处理流程、配置文件和 `ReportScript.sql` 仍沿用现有语义。
- `ReportScript.sql` 是业务处理链路的一部分，重构接口或前端时不要改写 SQL 语义。
- `auth.ini`、`cache/`、`dist/`、`frontend/dist/`、`frontend/node_modules/` 均为本地运行或构建产物，不进入版本库。

## 2026-05-20: Cross-platform packaging

- Added one-command build entry points: `scripts/build.bat`, `scripts/build.ps1`, and `scripts/build.sh`. Targets are `server`, `desktop`, `docker`, and `all`; script output stays ASCII to avoid console encoding issues on Windows.
- Server Portable uses PyInstaller one-dir mode and packages the backend executable with `frontend/dist`, `Configure.json`, `ReportScript.sql`, `cache/`, `logs/`, and launch scripts. The default server port remains `9081`.
- Desktop packaging uses Tauri 2 + Vue + Python sidecar. The build sets `VITE_API_BASE=http://127.0.0.1:19082`, builds a PyInstaller one-file `capareport-server` sidecar, and the desktop app starts it on `127.0.0.1:19082`.
- `app/config.py` supports `CAPAREPORT_BASE_DIR`; frozen PyInstaller server builds default `BASE_DIR` to the executable directory. The Tauri sidecar sets `CAPAREPORT_BASE_DIR` to the app data directory so runtime files are not written into the install directory.
- Tauri startup creates app-data `cache/` and `logs/`, then copies bundled `Configure.json` and `ReportScript.sql` on first run. Resource lookup supports both normal Tauri resources and the `_up_` directory generated for bundled `../` resources.
- Windows desktop shutdown uses `taskkill /F /T /PID` before killing the shell child, which avoids PyInstaller one-file sidecar process leftovers.
- Docker build now copies only required app files and frontend build output. `.dockerignore` excludes local dependencies, caches, and generated output; deployment compose files are emitted under `dist/docker/`.
- `app/main.py` accepts `--host` and `--port` and exposes `run_server()` so portable launchers, Docker, and the Tauri sidecar share the same backend entry point.
- Windows verification completed: `scripts\build.bat server -NoArchive`, `scripts\build.bat server`, `scripts\build.bat docker`, and `scripts\build.bat desktop`. Server portable `/health`, Docker container `/health`, and desktop sidecar `/health` all returned HTTP 200; desktop first run also copied config and SQL into app data.
- Cleanup verification completed: `.venv\Scripts\python.exe -m compileall app`, `npm run build`, PowerShell AST parse for `scripts/build.ps1`, Docker-hosted `sh -n scripts/build.sh`, and `cargo check --manifest-path src-tauri\Cargo.toml` with a temporary sidecar placeholder all passed. Linux/macOS native server and desktop packages still need native OS verification.
- `src-tauri/gen/schemas/` is intentionally tracked because `src-tauri/capabilities/default.json` references `../gen/schemas/desktop-schema.json`; do not ignore or delete these schema files during cleanup, otherwise VS Code JSON validation reports a missing schema.
- `README.md` has been rewritten to document local startup, Server Portable, Tauri desktop, Docker, Linux/macOS build commands, configuration blocks, common APIs, and cleanup rules. Keep future build instructions in sync with `scripts/build.*`.

## 2026-05-20: Tauri desktop console and installer language

- `src-tauri/src/main.rs` uses `#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]` so Windows release builds use the GUI subsystem and do not open an extra console window when launched from Explorer or the installer shortcut.
- `packaging/capareport-server.spec` keeps Server Portable in console mode, but desktop one-file sidecar builds (`CAPAREPORT_ONEFILE=1`) use PyInstaller `console=False`; PyInstaller should select `runw.exe` for the sidecar so it also stays hidden behind the Tauri window.
- `src-tauri/tauri.conf.json` sets Windows installer localization through `bundle.windows.wix.language = "zh-CN"` and `bundle.windows.nsis.languages = ["SimpChinese"]`. NSIS language keys must use NSIS names such as `SimpChinese`, while WiX/MSI uses locale names such as `zh-CN`.
- Verification on Windows: `cargo check --manifest-path src-tauri\Cargo.toml` passed, `scripts\build.bat desktop` generated the MSI and NSIS bundles, PE subsystem checks reported `Windows GUI` for both `capacity-report-desktop.exe` and `capareport-server.exe`, and the generated NSIS script included `MUI_LANGUAGE "SimpChinese"`.

## 2026-05-20: Unified release output under dist

- The former `build/` packaging source directory was renamed to `packaging/` to avoid confusing source-side packaging recipes with generated output. `packaging/` now holds `Dockerfile`, `docker-compose.yml`, the PyInstaller spec, and MySQL container config.
- `scripts/build.ps1` and `scripts/build.sh` now use `dist/.tmp/` for PyInstaller work output and copy final deliverables to `dist/server/`, `dist/desktop/`, and `dist/docker/`. Successful builds remove `dist/.tmp`, `frontend/dist`, `src-tauri/target`, and `src-tauri/binaries`.
- Docker builds now include `Configure.json` in the image and also create a deployable `dist/docker/` bundle containing `capacity-report-app-latest.tar`, `docker-compose.yml`, `Configure.json`, `ReportScript.sql`, `mysql/`, `cache/`, and `logs/`.
- Server Portable still includes `Configure.json` and `ReportScript.sql` inside `dist/server/CapacityReport-Server-<platform>-x64/`. Tauri desktop still bundles both files through `src-tauri/tauri.conf.json` resources and copies them to app data on first run.

## 2026-05-25: API Token management improvements

- API Token records now persist the complete token value in `api_tokens.json` in addition to the HMAC hash, prefix, and suffix. Existing hash-only records remain readable but cannot expose the full token; the UI asks users to regenerate those tokens before copying.
- `app/services/api_tokens.py` now supports exporting/importing token records for configuration migration and batch deletion by token ID. Config download adds an `ApiTokens` block, and config upload restores it when present.
- Token update is a partial update path: callers may change only `name`, `enabled`, or expiration fields without accidentally changing unspecified fields.
- `frontend/src/components/ApiTokenManager.vue` now shows selectable token rows, a batch delete button, a compact per-row action dropdown, copy-token action, and enable/disable action. New token creation defaults to a specified expiration date one month after the current browser date, while permanent tokens remain available via the radio option.
- OpenAPI and README text were updated to describe repeatable token copying, token migration through config upload/download, and batch delete.
- Verification performed: `api_tokens` service create/list/verify/enable/disable/export/import/batch-delete test passed, HTTP endpoints for create/list/update/config download/batch-delete passed on local port `9081`, `.venv\Scripts\python.exe -m compileall app` passed, and `npm run build` passed with only the existing Vite large chunk warning.

## 2026-05-25: API Token row visibility controls

- `frontend/src/components/ApiTokenManager.vue` renders Token values as a compact row with right-side icon buttons: an eye button toggles masked/full Token display, and a copy button copies the complete Token directly from the row.
- The per-row operation dropdown now keeps edit, enable/disable, regenerate, and delete actions; copying is surfaced beside the Token value for faster repeated use.
- Build verification: `npm run build` passed with only the existing Vite large chunk warning.
- Follow-up UI adjustment: the eye/copy buttons now sit immediately after the Token text instead of being pushed to the far right, and Token rows show `created_at` in the metadata area.

## 2026-06-01: API documentation toolbar cleanup

- `frontend/src/components/ApiDocs.vue` no longer registers a page-header `copy sample` action, avoiding duplicate `复制传参示例` buttons on the API documentation page.
- The API documentation card still keeps its local toolbar actions: `复制传参示例` and `OpenAPI JSON`.
- Verification performed: `npm run build` passed, and generated frontend build output was removed after verification.

## 2026-06-01: Frontend entry chunk reduction

- `frontend/src/router.ts` now lazy-loads `FileWorkflow.vue`, matching the other main pages and keeping the data processing page out of the base entry chunk until the route is opened.
- `frontend/src/AppShell.vue` now lazy-loads `LoginView.vue` and the hidden license activation dialog; the dialog UI and activation API flow moved to `frontend/src/components/LicenseActivationModal.vue`.
- Build verification: `npm run build` passed. The base `index` chunk dropped from about `572 kB` to about `461 kB`; the remaining large chunks are still `ApiDocs` (`swagger-ui-dist`) and `ScriptPanel` (`monaco-editor`).

## 2026-06-01: History detail file browser

- `app/api/routers/history.py` adds `/api/history/files` for browsing a history work directory by safe relative path, and `/api/history/file/download` for downloading one file directly or one directory as a temporary ZIP. Both paths are constrained under the record's `cache/` work directory; download still rejects pending/processing records.
- `frontend/src/components/HistoryPanel.vue` keeps the processing log at the bottom of the task detail modal, and adds a `详情 / 文件` tab area above it. The file tab shows breadcrumb navigation, parent/refresh controls, directory/file type, size, modified time, and per-item download actions.
- `frontend/src/types.ts` defines `HistoryFileEntry` and `HistoryFilesResponse`; `app/main.py` adds Chinese OpenAPI descriptions and examples for the new history file APIs.
- Verification performed: `.venv\Scripts\python.exe -m compileall app`, `npm run build`, direct history file listing for `20260519_172434`, path traversal rejection, and single-file download of `log.txt` on a temporary local server all passed. Build output and Python caches were removed after verification.

## 2026-06-01: RJ scheduler display cleanup

- `app/services/auto_scheduler.py` now keeps RJ directory status keys clean instead of prefixing them with `rj:` in the combined scheduler response.
- `frontend/src/components/SettingsPanel.vue` strips any legacy `rj:` prefix before rendering the scheduler directory name, so the UI shows `RJ/2.6G/...` instead of `rj:RJ/2.6G/...`.
- This is display-only cleanup; the underlying RJ directory detection and readiness logic were not changed.

## 2026-06-01: Settings page split

- `frontend/src/components/SettingsPanel.vue` splits the former combined connection page into a dedicated `数据库配置` tab and a separate `远程数据源` tab.
- Database-related settings now stay together with `数据库配置` and `处理历史保留`; remote automation settings now own the FTP/SFTP fields, auto-delete toggle, scheduler configuration, and scheduler status panel.
- `frontend/src/styles.css` now uses dedicated layout classes for the database and remote settings panes, with independent scrolling and responsive single-column stacking on narrower screens.
- Verification performed: `cd frontend && npm run build` passed. Browser inspection on `http://127.0.0.1:9081/settings` confirmed the two new tabs render correctly, the remote panel shows its own configuration and scheduler cards, and horizontal overflow remained at `0`.

## 2026-06-01: Settings remote scheduler refinement

- `frontend/src/components/SettingsPanel.vue` keeps `远程数据源` focused on FTP/SFTP connection fields. Protocol, host, port, timeout, and FTP passive mode render on one row when width allows; remote automation and delete-source toggles now sit below `远程目录`.
- `自动调度` is now a separate settings tab. Scheduler controls are disabled unless `启用远程自动化` is on, and turning off remote automation automatically turns off scheduler enablement in the current form state and saved payload.
- `debug.bat` starts the Python backend on `127.0.0.1:9081` and the Vite frontend on `127.0.0.1:5173` for source-level debugging without requiring `frontend/dist`.
- Verification performed: `cmd /c debug.bat` started the debug backend/frontend, `cd frontend && npm run build` passed, and browser inspection confirmed the remote connection fields align in one row with no horizontal overflow. Debug processes and `frontend/dist/` were removed after verification.

## 2026-06-01: Task runtime cleanup

- `app/api/routers/task_runtime.py` centralizes shared task-stage updates, processing license log output, and safe history-retention cleanup for manual processing and remote processing routes.
- `app/api/routers/tasks.py` and `app/api/routers/remote.py` now reuse the shared helpers instead of carrying duplicate `_set_task_stage` and `_log_license_check` implementations.
- Verification performed: `.venv\Scripts\python.exe -m compileall app`, `npm run build`, and `cargo check --manifest-path src-tauri\Cargo.toml` with a temporary sidecar placeholder all passed. Generated build output, Python caches, and temporary Tauri sidecar files were removed after verification.

## 2026-06-01: Download cleanup helper

- `app/utils/files.py` now provides `remove_file_safely()` for best-effort temporary file cleanup.
- Database table export and history archive download routes now reuse this helper instead of carrying duplicate private `_remove_file()` functions.
- Verification performed: `.venv\Scripts\python.exe -m compileall app`, `npm run build`, and `cargo check --manifest-path src-tauri\Cargo.toml` with a temporary sidecar placeholder all passed. Generated build output, Python caches, and temporary Tauri sidecar files were removed after verification.

## 2026-06-01: Clipboard helper cleanup

- `frontend/src/composables/clipboard.ts` centralizes browser clipboard writes with the existing hidden-textarea fallback.
- API documentation, API Token management, and history detail log copying now reuse `writeClipboardText()` instead of each component carrying its own clipboard fallback.
- Verification performed: `npm run build`, `.venv\Scripts\python.exe -m compileall app`, and `cargo check --manifest-path src-tauri\Cargo.toml` with a temporary sidecar placeholder all passed. Generated build output, Python caches, and temporary Tauri sidecar files were removed after verification.

## 2026-06-01: Final cleanup pass

- A follow-up static import scan removed the leftover unused `Path` import from `app/api/routers/database.py`.
- Final verification included `.venv\Scripts\python.exe -m compileall app`, `npm run build`, a lightweight Python AST unused-import scan, `.venv\Scripts\python.exe -m pip check`, and `npm audit --omit dev`.
- Remaining scan hits are intentional runtime/cleanup console messages or behaviorally different format helpers; no further low-risk cleanup item was found in the final pass.

## 2026-06-01: Script task status cleanup

- `app/api/routers/script.py` now reuses the shared `set_task_stage()` helper for manual SQL script task status updates.
- Script execution status entries now include the same `stage` field shape used by processing and remote tasks while preserving the existing status values.
- Verification performed: `.venv\Scripts\python.exe -m compileall app`, `npm run build`, and `cargo check --manifest-path src-tauri\Cargo.toml` with a temporary sidecar placeholder all passed. Generated build output, Python caches, and temporary Tauri sidecar files were removed after verification.

## 2026-06-02: Platform architecture planning

- `docs/platform_architecture_plan.md` records the planned standalone Web data-processing platform architecture, module boundaries, submodule strategy, data flow, storage/history model, and staged roadmap.
- The future platform workspace is reserved as `platform/` under the current repository root and is ignored by CapaReport through `.gitignore` so exploratory platform development does not affect this project.
- The design intentionally treats CapaReport as a reference implementation only; reusable ideas should be extracted by responsibility rather than copied into one large module.
- `platform/` is explicitly isolated from CapaReport: it must not use this repository's virtual environment, dependency files such as `requirements.txt`, frontend packages such as `frontend/node_modules`, build scripts, configs, runtime data, or source modules.

## 2026-06-23：双模式后端（自带 FTP/MySQL + Metrix 平台可选，两侧独立）

把应用做成「自包含 + Metrix 可选」：源与仓库各自可在直连与 Metrix 间独立选择，互不依赖。基于原版（pre-M2 全功能：FTP/MySQL/查看导出/license）叠加 Metrix 后端。

- 配置 `app/config.py`：新增 `source_type`(ftp/sftp/metrix)、`warehouse_type`(mysql/metrix)、`MetrixConfig`(base_url/token/storage_id/database_conn_id/target_database/recent_days/data_dir_to_table)，保留 `MySQLConfig`/`RemoteDataConfig`；Configure.json 新增 `SourceType`/`WarehouseType`/`Metrix`（token 隐藏于 to_dict，含于 to_file_dict）；缺省向后兼容（source_type 缺省取 RemoteData.protocol，warehouse 缺省 mysql）。
- 源工厂 `app/services/platform.py::make_source_downloader`：按 source_type 返回 `RemoteDataDownloader`(FTP/SFTP) 或 `PlatformStorageDownloader`(Metrix 储存)，接口一致。`platform.py` 改用 MetrixConfig（token 从配置读），并扩展 `PlatformClient` 增 list_tables/table_columns/table_data/submit_export/download_job_file 供仓库代理。
- 仓库分派：`remote.py`/`tasks.py`/`script.py` 按 warehouse_type 分流——mysql 走原版 `DataProcessor`（直连、LOAD DATA、单会话报表 SQL）；metrix 走 `app/services/pipeline.py`（CsvProcessor → 平台 import → run-script single_session）。`auto_scheduler.py` 扫描也改用 make_source_downloader。
- 仓库视图代理 `app/warehouse.py`：`make_warehouse(config)` → 直连返回原版 `DatabaseManager`，Metrix 返回 `MetrixWarehouse`（用平台 API 实现 get_tables/get_table_info/query_table/truncate/drop/drop_all/execute_sql 同接口）；`routers/database.py` 的 `_db()` 透明切换，`/api/download` 在 metrix 模式代理到平台导出任务（避免分页上限丢行）。
- 路由 `routers/config.py`：新增 `POST /api/config/backend`(类型)、`/api/config/metrix`(连接)，配置上传也识别 SourceType/WarehouseType/Metrix。
- 前端 `SettingsPanel.vue`：新增「数据源/仓库」标签——源/仓库单选 + Metrix 连接卡片（地址/Token/storage_id/database_conn_id/目标库/recent_days）+ 保存/测试储存；保留原 MySQL/远程数据源标签与 DatabasePanel 查看导出。`types.ts` 加 `source_type/warehouse_type/metrix`+`MetrixConfig`。
- 重要修复：`routers/database.py` 全部处理函数由 `async def` 改为 `def`——这些是阻塞式（直连 pymysql / Metrix HTTP / 大表导出轮询），放在事件循环里会冻结单 worker（实测大表导出把 /health 也卡死）；改 def 后 FastAPI 用线程池执行。
- 容器：`main.py` 重新支持 `CAPAREPORT_FRONTEND_DIR`（代码/前端在 /app、运行态 /data 分离，robocopy 覆盖后补回）；`.dockerignore` 放开 `frontend/dist`；`requirements.txt` 含 requests + pymysql/cryptography/paramiko（双模式都要）。Token 改存配置，entrypoint 不再需要环境变量。
- 验证：前端 `npm run build`（vue-tsc）通过；镜像构建成功；容器冒烟（Metrix 模式）端到端通过——登录/`config/full`(新字段)/tables/table info/table-data/execute/导出代理全部 200，行数与列数正确。直连 MySQL 路径为原版未改代码。

## 2026-06-24：精简（去 API 文档 / API Token）+ 设置页卡片自适应 + 授权默认期改 2026-12-30

随双模式集成一起进入 `metrix-integration` 分支。去掉与数据处理无关的对外 API 能力，业务接口仅保留登录态访问：

- 删除 API Token 与离线 API 文档：删 `app/api/routers/api_tokens.py`、`app/services/api_tokens.py`、`frontend/src/components/ApiDocs.vue`、`ApiTokenManager.vue`；前端去掉 `router.ts`/`AppShell.vue` 的 `api-center` 路由与菜单、`package.json` 的 `swagger-ui-dist` 依赖、`types.ts` 的 `ApiToken*` 类型、`vite-env.d.ts` 的 swagger 声明、`SettingsPanel.vue` 的「API Token」分页。
- 后端解耦：`auth.py::resolve_access_context` 只保留 JWT（去掉 api_token 分支）；`main.py` 去掉 api_tokens 路由注册、`touch_token_usage`、`/api/openapi.json` `/api/docs-ui` 文档端点，并删除随之不可达的整套 OpenAPI 定制（`custom_openapi`/`TAG_LABELS`/`OPENAPI_TAGS`/`OPENAPI_OPERATION_DOCS` 及 `_make_operation_id` 等辅助、`get_openapi` 导入、`LOGIN_ONLY_API_PATHS`），`LOGIN_ONLY_API_PREFIXES` 去掉 `/api/tokens`；`config.py` 去掉配置下载/上传里的 `ApiTokens` 字段。
- 授权默认到期日：`app/services/license.py::DEFAULT_EXPIRES_ON` 由 `2026-06-20` 改为 `2026-12-30`，前端兜底文案（`FileWorkflow.vue`、`LicenseActivationModal.vue`）同步；授权功能本身保留（连点品牌图标 8 次打开延期窗口）。
- 设置页排版：`styles.css` 的 `.settings-database-stack` 由纵向 `column` 改为 `row wrap`，子卡 `flex:1 1 360px;min-width:320px`，宽屏并排、窄屏自动换行；「处理历史保留」卡加 `work-card-narrow`（`flex-grow:0` + `max-width`）显著收窄；规则同时作用于「数据源/仓库」与「数据库」两个标签页；清理已失效的 `.settings-token-panel` 规则。
- 验证：`python -m compileall app` 通过；前端 `npm run build`（vue-tsc）通过，产物中不再出现 swagger/ApiDocs chunk。

## 2026-06-24：Metrix 模式报表 SQL 固定按本地 ReportScript.sql 执行（移除库内脚本 script_id 死路径）

- 背景：Metrix 平台 `POST /run-script` 同时支持 `content`（直接执行 SQL 文本）与 `script_id`（执行平台数据库里保存的脚本，且 `script_id` 会覆盖 `content`）。CapacityReport 期望「无论哪种触发，Metrix 模式都执行本应用本地的 `ReportScript.sql`」，不使用平台库内保存的脚本。
- 现状确认：`pipeline.py`/`warehouse.py` 所有 `run_script` 调用本就只传 `content`（报表 SQL 来自 `read_report_sql()` 读取本地 `ReportScript.sql`），从不传 `script_id`，行为已正确。
- 改动：`app/services/platform.py::run_script` 删除一直未被调用的 `script_id` 参数与对应 body 分支，方法只构造 `content`，从代码层面杜绝走平台库内脚本那条路；签名由 `(conn_id, script_id=None, content="", ...)` 改为 `(conn_id, content="", ...)`，现有调用全用 `content=` 关键字、`conn_id` 位置参，未受影响。
- 验证：`python -m compileall app` 通过；全仓 `app` 内除该行注释外无 `script_id` 引用。

## 2026-06-24：数据目录映射统一为 DataMappings

- 背景：UD 与 RJ 在处理阶段本质都是「源目录 -> 暂存表」。此前 UD 使用 `UDData.directories`，RJ 使用 `RJData.weekly_directories` + 代码内置目录名到表名映射，概念重复且前端容易继续堆卡片。
- 配置：删除 `UDData` / `RJData` 两套配置，改为顶层 `DataMappings`。`DataMappings.directories` 每行结构为 `{path, table, ready_rule}`，`ready_rule=daily` 表示目标周每日 7 天检查，`ready_rule=auto` 表示按目录最新 ZIP 自动识别日粒度或周粒度；RJ 原字段映射并入 `DataMappings.table_field_mappings`，按目标表名覆盖全局字段映射。`MetrixConfig` 仍只保留平台连接信息。
- 处理链路：直连 MySQL 的 `DataProcessor` 与 Metrix 仓库模式的 `CsvProcessor` 都只读取 `DataMappings.directories`。一个表可对应多个目录：每个目录先按最近日期筛选 CSV，再合并导入同一张暂存表（Metrix 模式写 `.out/{table}.csv`，MySQL 模式逐文件导入同表）。表级字段映射存在时优先使用 `DataMappings.table_field_mappings[table]`，否则使用全局 `ExtractField`。
- 自动调度：原 RJ 专用检查改为通用自动粒度检查。`ready_rule=auto` 的目录会从普通每日扫描中排除，并单独按最新 ZIP 判断日/周粒度；如果配置里只有自动粒度目录，只要这些目录就绪也可触发调度。
- 前端：设置页「规则映射」左侧独立滚动配置栏中只保留一个「数据目录映射」卡片，每行可编辑目录、暂存表与就绪规则，并保存到 `/api/config/data-mappings`。后续新增目录类映射继续加同一张表，不再新增配置卡片。
- 验证：`python -m compileall -q app` 通过；`frontend` `npm run build` 通过（仅既有大 chunk 提示）；构建产物与 Python 缓存已清理。

## 2026-06-24：新增 CellData 远程源与数据库配置入口

- 背景：后续需要引入 CellData 自动化处理，处理完成报表 SQL 后还会从 CellData 数据库表匹配数据并写入结果表。本轮先只落配置与界面，不接入实际提取/处理/入库流水线。
- 配置：新增顶层 `CellData` 配置块，包含 `RemoteData`（FTP/SFTP 连接，默认远程目录 `/CellData`，不参与现有自动调度）与 `MySQL_DBInfo`（默认库名 `celldata`）。CellData 数据库可与主仓库 MySQL 相同，也可指向独立数据库。
- 后端接口：新增 `/api/config/cell-data/remote`、`/api/config/cell-data/mysql` 保存接口，以及 `/api/config/cell-data/remote/test`、`/api/config/cell-data/mysql/test` 测试接口；测试逻辑分别复用 `RemoteDataDownloader` 和独立 PyMySQL `SELECT 1`。
- 前端：系统设置「数据库」页新增「CellData 数据库配置」卡片；「远程数据源」页新增「CellData 数据源」卡片；「数据源 / 仓库」页说明 CellData 为独立辅助数据源，不影响主数据源/仓库选择。
- 验证：`python -m compileall -q app` 通过；`frontend` `npm run build` 通过（仅既有大 chunk 提示）；构建产物与 Python 缓存已清理。

## 2026-06-24：精简系统设置与历史页文案

- 设置页说明文案去掉开发实现细节，只保留用户填写配置所需的短提示：主数据源/仓库、Metrix 连接、CellData 数据库/远程源、远程数据源、自动调度、目录映射、Sheet 过滤和字段映射等位置均已压缩。
- 历史删除确认中的“缓存文件”改为“相关文件”，避免把内部存储实现暴露给用户。
- 验证：`frontend` `npm run build` 通过；构建产物已清理。

## 2026-06-25：数据管理支持切换主数据库与 CellData 数据库

- 数据管理页左侧表列表新增数据库选择，可在主数据库与 CellData 数据库之间切换；选项名称跟随系统设置里的主仓库库名和 `CellData.MySQL_DBInfo.dbname`。
- 后端数据库接口新增 `database_source` 参数，`main` 保持原有直连 MySQL / Metrix 仓库逻辑，`cell_data` 使用 `CellData.MySQL_DBInfo` 创建独立 MySQL 仓库。表列表、表结构、分页数据、清空、删除、删除全部、执行 SQL 和导出均按该参数选择数据库。
- CellData 数据库当前只支持直连 MySQL 配置；Metrix 仓库模式只影响主数据库。
- 验证：`python -m compileall -q app` 通过；`frontend` `npm run build` 通过（仅既有大 chunk 提示）；构建产物与 Python 缓存已清理。

## 2026-06-25：数据管理数据库选择改为弹窗列表

- 数据管理页不再用下拉框切换数据库，改为表标题旁的图标按钮打开「选择数据库」弹窗；弹窗内为固定高度列表，超出高度滚动。
- 左侧标题只显示分类名（主数据库 / CellData），不显示具体库名，也不再显示“表”字；弹窗列表显示真实库名（如 `主数据库：CapacityReport`）。选择项后续新增更多数据库时继续扩展同一列表，不占用侧栏宽度。
- 验证：`frontend` `npm run build` 通过（仅既有大 chunk 提示）；构建产物已清理。

## 2026-06-25：CellData cellinfo 来源与映射规则（待实现）

- 数据来源：SFTP `127.0.0.1:2022` 开发环境中，CellData 原始文件位于 `/网优日常优化数据文档/日常性能报表/2026年/300表/{700M,2.6G}/`。目录下文件为 `Result_300_*.zip`；文件时间取 ZIP 文件名末尾时间戳（如 `20260620132109`），**不要用 SFTP 修改时间**。
- ZIP 结构：压缩包内部包含若干 CSV，例如 `LTE_ITBBU_CellInfo_*.csv`、`LTE_SDR_CellInfo_*.csv`、`NR_CellInfo_*.csv`、`NetworkInfoStat_*.csv`、`SpecificColumn/...`、`others/...`。核心入库来源先按文件名前缀识别 `LTE_ITBBU_CellInfo`、`LTE_SDR_CellInfo`、`NR_CellInfo`。
- 编码注意：样本中 `NR_CellInfo` 用 GBK/GB18030 解码中文正常，按 UTF-8 会乱码；后续读取 CSV 时需要做编码探测或优先兼容 GBK。
- 目标表：`celldata.cellinfo`，字段为 `CGI/eNodeBID/CellID/PLMN/基站名称/小区名称/频点/带宽/制式/功率/网络`。其中 `CGI` 由 `PLMN-eNodeBID-CellID` 拼接生成。
- 2.6G 映射：
  - `LTE_ITBBU_CellInfo`：`eNodeBID<-eNBId`，`CellID<-cellLocalId`，`PLMN<-plmn`，`基站名称<-eNBName`，`小区名称<-CellName`，`频点<-frequency`，`带宽<-bandWidth`，`制式<-radioMode`，`功率<-cpSpeRefSigPwr`，`网络="4G"`。
  - `LTE_SDR_CellInfo`：同 `LTE_ITBBU_CellInfo`。
  - `NR_CellInfo`：`eNodeBID<-gNBId`，`CellID<-cellLocalId`，`PLMN<-plmn`，`基站名称<-gNBName`，`小区名称<-CellName`，`频点<-ssbFrequency`，`带宽<-carrierBandwidth`，`制式="2.6G"`，`功率<-powerPerRERef`，`网络="5G"`。
- 700M 映射：
  - `LTE_ITBBU_CellInfo`：`eNodeBID<-eNBId`，`CellID<-cellLocalId`，`PLMN<-plmn`，`基站名称<-eNBName`，`小区名称<-CellName`，`频点<-frequency`，`带宽<-bandWidth`，`制式<-radioMode`，`功率<-cpSpeRefSigPwr`，`网络="4G"`。
  - `NR_CellInfo`：`eNodeBID<-gNBId`，`CellID<-cellLocalId`，`PLMN<-plmn`，`基站名称<-gNBName`，`小区名称<-CellName`，`频点<-ssbFrequency`，`带宽<-carrierBandwidth`，`制式="700M"`，`功率<-powerPerRERef`，`网络="5G"`。

## 2026-06-25：实现 CellData 预处理与单独刷新入口

- 配置：`CellData` 新增 `scan_paths`、`year_dir_regex`、`file_name_regex`、`file_time_regex` 与 `mapping`。默认扫描路径为 `/网优日常优化数据文档/日常性能报表/{maxyear}年/300表`；默认 ZIP 过滤为 `Result_300_*.zip`；默认映射写入 `cellinfo` 并生成 `CGI={PLMN}-{eNodeBID}-{CellID}`。
- 设置页：CellData 数据源卡片新增扫描路径列表、路径说明弹窗、三个高级正则输入、映射 JSON 编辑框，以及“校验 JSON / 恢复默认映射 / 保存规则”操作。说明弹窗包含路径模板、占位符、正则和多目录示例，避免在表单页堆长文案。
- 后端：新增 `app/services/cell_data.py`，负责路径模板解析（含 `{maxyear}`/`{yyyy}`/`{yyyymm}`/`{yyyymmdd}`）、按扫描目录下一级子目录选择最新 ZIP、解析目标 CSV、执行 JSON 映射、清空并批量写入 `celldata.cellinfo`。CSV 解码优先 UTF-8/UTF-8-SIG，回退 GB18030/GBK。
- 接口：新增 `app/api/routers/cell_data.py`，提供 `POST /api/cell-data/process/start` 与 `/status`，数据处理页新增独立 CellData 卡片，可只刷新 CellData，不跑容量处理。
- 接入：本地上传、远程手动和自动调度入口都会在容量处理前调用 CellData 预处理；CellData 单独处理和容量处理共用现有全局任务锁，避免并发写库。
- 验证：`python -m compileall -q app` 通过；`frontend` `npm run build` 通过；远程定位可从最新年份 `2026年/300表` 选出 `2.6G` 与 `700M` 各自最新 `Result_300` ZIP；用 SFTP MCP 读取的小样本 ZIP 验证解析和入库，`celldata.cellinfo` 写入 1 行且中文字段正常（样本 `CGI=460-00-12683845-1`）。

## 2026-06-25：CellData 卡片支持本地上传处理

- 数据处理页 CellData 卡片改为与主上传区一致的拖拽/点击上传样式，支持拖入或选择多个 `Result_300_*.zip`，也支持选择文件夹上传。
- 新增 `/api/cell-data/process/upload`，上传后复用 CellData 解析入库逻辑；若 ZIP 不在 `700M/2.6G` 等目录下且无法识别频段，会跳过无法唯一匹配的 CSV。
- CellData 卡片仍保留「远程刷新」操作，用于按系统设置中的 CellData SFTP/FTP 配置拉取处理。
- 验证：`frontend` `npm run build` 通过；构建产物已清理。

## 2026-06-25：数据处理卡片补说明按钮并规范 CellData 上传

- 数据处理页的容量数据卡片与 CellData 卡片左上角均显示数据类型，右上角均提供说明图标按钮，点击后以小弹窗展示所需文件格式和目录结构。
- CellData 卡片改为点击/拖拽文件夹上传，不再提供单文件选择；直接拖入单个 ZIP 会提示选择包含 `Result_300` ZIP 的文件夹。
- 验证：`frontend` `npm run build` 通过；构建产物已清理。

## 2026-06-25：数据处理卡片并排展示

- 数据处理页容量数据与 CellData 两个卡片在宽屏下左右并排展示，窄屏下自动回落单列，减少对日志区域的挤压。
- 容量数据说明补充：启用 CellData 数据源时，处理容量数据前会先刷新 CellData；CellData 卡片按钮文案统一为「远程下载并处理」。
- 验证：`frontend` `npm run build` 通过；构建产物已清理。

## 2026-06-25：数据处理卡片说明与上传方式调整

- 容量数据和 CellData 卡片左上角均标注数据类型，右上角均有说明按钮；容量数据说明弹窗明确启用 CellData 时会在处理容量数据前先更新 CellData。
- CellData 卡片点击后选择文件夹，拖拽也只接受文件夹；不支持单个 ZIP 文件直接拖入，避免缺少频段目录导致无法映射。
- 验证：`frontend` `npm run build` 通过；构建产物已清理。

## 2026-06-25：远程数据源页收纳 CellData 规则设置

- 远程数据源页只保留容量数据源与 CellData 数据源两张连接配置卡片，宽屏下并排展示；CellData 的扫描路径、正则和映射 JSON 收纳到「规则设置」弹窗。
- CellData 规则弹窗包含扫描路径列表、路径说明入口、高级正则和 Monaco JSON 编辑器，支持格式化、校验、恢复默认映射和保存规则。
- 验证：`frontend` `npm run build` 通过；构建产物已清理。

## 2026-06-25：精简 CellData 数据源路径配置

- CellData 数据源卡片去掉“远程目录”输入，连接根目录固定走 `/`；实际数据位置统一由「规则设置」中的扫描路径模板决定，避免两个路径概念混淆。
- 扫描路径占位符扩展支持 `{maxmonth}`、`{maxday}`，并新增 `month_dir_regex`、`day_dir_regex` 高级正则配置；说明弹窗同步补充相关说明。
- 验证：`python -m compileall -q app` 通过；`frontend` `npm run build` 通过；构建产物与 Python 缓存已清理。

## 2026-06-25：CellData 扫描路径回到数据源卡片

- 扫描路径属于文件来源配置，已移回 CellData 数据源卡片中展示和维护；「规则设置」弹窗只保留高级正则与映射 JSON，避免弹窗承担过多基础配置。
- CellData 数据源不再展示“远程目录”，连接根目录固定为 `/`；实际文件位置完全由扫描路径控制。
- 扫描路径占位符支持 `{maxyear}`、`{maxmonth}`、`{maxday}`、`{yyyy}`、`{yyyymm}`、`{yyyymmdd}`，并提供对应年份/月/日目录正则配置。
- 验证：`python -m compileall -q app` 通过；`frontend` `npm run build` 通过；构建产物与 Python 缓存已清理。

## 2026-06-25：优化 CellData 扫描路径排版

- CellData 数据源卡片中的扫描路径区域改为全宽列表布局，说明文字、说明按钮、路径输入、删除按钮和添加输入保持对齐，减少左侧拥挤。
- 验证：`frontend` `npm run build` 通过；构建产物已清理。

## 2026-06-25：CellData 映射支持图形化编辑

- CellData「规则设置」弹窗中的映射规则增加“图形化 / JSON”切换。图形化模式可维护目标表、主键字段、主键表达式、来源目录、CSV 前缀和字段映射；字段映射支持“CSV 字段”和“固定值”两种模式。
- JSON 模式仍使用 Monaco 编辑器，支持格式化、校验、恢复默认；两种模式共用同一份 `CellData.mapping` JSON，切换时自动互转。
- 验证：`frontend` `npm run build` 通过；构建产物已清理。

## 2026-06-25：修正 LTE_SDR 小区名称映射

- `LTE_SDR_CellInfo` 的小区名称字段实际为 `cellName`（小写 c），不是 `CellName`；默认 CellData 映射和 `Configure.json` 已同步修正。
- 使用 2.6G 样本重新导入后，`celldata.cellinfo` 中 4G/5G 的 `小区名称` 空值数均为 0。
- 验证：`python -m compileall -q app` 通过。

## 2026-06-25：固定图形化映射基础区与添加来源按钮

- CellData「规则设置」弹窗不再整体滚动；高级匹配、目标表、主键字段和主键表达式固定显示，图形化模式下仅来源列表滚动。
- “添加来源”按钮固定在来源列表下方，始终可见；弹窗底部保存按钮也保持可见。
- 验证：`frontend` `npm run build` 通过；构建产物已清理。

## 2026-06-25：图形化来源支持折叠

- CellData 图形化映射中每个来源卡片支持展开/收起，来源头展示目录与 CSV 前缀摘要；“添加来源”按钮移动到映射规则标题区右侧。
- 验证：`frontend` `npm run build` 通过；构建产物已清理。

## 2026-06-25：调整图形化映射添加来源位置

- “添加来源”按钮移动到主键表达式输入区下方右侧；点击后来源列表自动滚动到新增来源。
- 验证：`frontend` `npm run build` 通过；构建产物已清理。
