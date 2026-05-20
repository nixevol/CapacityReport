# 项目上下文记录
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
