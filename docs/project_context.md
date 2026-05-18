# 项目上下文记录

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
  - `service.py`：服务状态和重启。
  - `script.py`：SQL 脚本读取、保存和执行。
  - `health.py`：健康检查。
- 运行时共享状态放在 `app/state.py`，包括配置实例、历史管理器、处理任务、上传会话和全局任务锁。
- 登录、密码文件和 Token 逻辑放在 `app/auth.py`，继续使用本地 `auth.ini`。
- 服务重启检测和进程退出逻辑放在 `app/services/runtime.py`。
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

- Python 依赖保留当前代码实际使用项：`fastapi`、`uvicorn[standard]`、`python-multipart`、`pymysql`、`sqlalchemy`、`cryptography`、`pandas`、`openpyxl`、`chardet`、`supervisor`。
- 已移除未使用的 `sqlparse`、`aiofiles`、`python-dateutil`。
- 旧静态目录、根目录打包产物、日志和 Python 编译缓存属于可清理产物，不应提交。

### 注意事项

- 当前项目按每周整包替换使用，不维护旧版 API 兼容层；但核心处理流程、配置文件和 `ReportScript.sql` 仍沿用现有语义。
- `ReportScript.sql` 是业务处理链路的一部分，重构接口或前端时不要改写 SQL 语义。
- `auth.ini`、`cache/`、`dist/`、`frontend/dist/`、`frontend/node_modules/` 均为本地运行或构建产物，不进入版本库。
