# 远程数据自动调度功能设计方案

## 一、需求概述

### 1.1 背景

当前系统需要每周一手动点击"远程下载并处理"来跑上周数据（周一到周日，7天数据）。由于服务器时间不准确，无法使用定时任务在固定时间运行。需要一个基于**数据就绪状态**的自动调度机制。

### 1.2 核心需求

1. **文件时间过滤**：处理时只处理最近7天的文件
2. **自动就绪检测**：每小时检查远程目录，判断上周7天数据是否齐全
3. **自动触发处理**：数据就绪后自动下载并处理
4. **状态标识管理**：使用标识文件避免重复触发

---

## 二、文件时间解析规则

### 2.1 文件名格式

| 格式 | 示例 | 数据日期 |
|------|------|----------|
| `XXX_YYYYMMDDHHMM_YYYYMMDDHHMM` | `CapacityReportData2.6_202605110000_202605120000.zip` | 第一个时间戳 `202605110000` → 2026-05-11 |
| `XXX_YYYYMMDDHHMM` | `CapacityReportData2.6_202605110000.zip` | 时间戳 `202605110000` → 2026-05-11 |

### 2.2 解析逻辑

复用项目已有的正则 `_ZIP_DATE_RE = re.compile(r"(?<!\d)(20\d{10}(?:\d{2})?)(?!\d)")`，取第一个匹配项作为数据日期。

```python
def extract_file_date(filename: str) -> date | None:
    """从文件名提取数据日期（取第一个匹配的时间戳）"""
    match = _ZIP_DATE_RE.search(filename)
    if not match:
        return None
    timestamp = match.group(1)  # 12位: YYYYMMDDHHMM 或 14位: YYYYMMDDHHMMSS
    fmt = "%Y%m%d%H%M%S" if len(timestamp) == 14 else "%Y%m%d%H%M"
    try:
        return datetime.strptime(timestamp, fmt).date()
    except ValueError:
        return None
```

---

## 三、自动调度机制

### 3.1 工作流程

```
每小时定时器触发
        │
        ▼
┌─────────────────────┐
│  检查就绪标识文件    │
│  (ready.flag)       │
└─────────────────────┘
        │
        ├── 标识存在 ──► 跳过检测，直接触发处理
        │
        ▼
┌─────────────────────┐
│  连接 FTP/SFTP      │
│  遍历远程目录       │
└─────────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│  对每个 expected_directory:         │
│  1. 列出所有 ZIP 文件名             │
│  2. 从文件名提取数据日期            │
│  3. 检查是否覆盖上周7天（周一~周日）│
└─────────────────────────────────────┘
        │
        ├── 未就绪 ──► 记录日志，等待下次检查
        │
        ▼
┌─────────────────────┐
│  写入就绪标识文件    │
│  (ready.flag)       │
└─────────────────────┘
        │
        ▼
┌─────────────────────┐
│  触发远程下载处理    │
│  (复用现有流程)      │
└─────────────────────┘
        │
        ▼
┌─────────────────────┐
│  处理成功后          │
│  1. 删除远程源文件   │
│  2. 删除就绪标识     │
└─────────────────────┘
        │
        ▼
  继续每小时检查
```

### 3.2 目标日期范围（严格按自然周）

**永远是上周一到上周日**（自然周，7天）。无论今天是周几，程序都会自动计算正确的上周一和上周日。

```python
def get_target_week_range(week_offset: int = 0) -> tuple[date, date]:
    """获取目标周的周一到周日。
    week_offset=0 表示上周，-1 表示上上周
    """
    today = date.today()
    this_monday = today - timedelta(days=today.weekday())
    target_monday = this_monday - timedelta(days=7 * (1 - week_offset))
    target_sunday = target_monday + timedelta(days=6)
    return target_monday, target_sunday
```

示例（假设 week_offset=0）：

| 今天 | 本周一 | 上周一 | 上周日 | 检查范围 |
|------|--------|--------|--------|----------|
| 周一 5/19 | 5/19 | 5/12 | 5/18 | 5/12~5/18 |
| 周三 5/21 | 5/19 | 5/12 | 5/18 | 5/12~5/18 |
| 周日 5/25 | 5/19 | 5/12 | 5/18 | 5/12~5/18 |

**不会**把非自然周的7天范围（如上周五到本周四）当作目标。`week_offset` 参数仅用于补跑场景：如果上周处理失败，可设为 `-1` 检查上上周的周一到周日。

### 3.3 就绪判断

一个目录的"就绪"条件：该目录下所有 ZIP 文件提取出的数据日期集合，**完全覆盖**目标周（上周一~上周日）的全部 7 天。

**关键**：
1. 不依赖系统日期，而是从文件名中提取日期
2. 文件名只取**第一个**时间戳作为数据日期
3. 例如文件 `CapacityReportData2.6_202605120000_202605130000.zip` → 数据日期为 2026-05-12
4. 如果某个日期没有对应的 ZIP 文件，该目录判定为未就绪

### 3.4 标识文件

- **位置**：`cache/auto_scheduler/ready.flag`
- **格式**：JSON

```json
{
  "ready_at": "2026-05-19T10:00:00",
  "week_start": "2026-05-12",
  "week_end": "2026-05-18",
  "directories": {
    "4G/FDD": {"found_days": 7, "required_days": 7},
    "4G/900": {"found_days": 7, "required_days": 7},
    "5G/2.6": {"found_days": 7, "required_days": 7},
    "5G/700": {"found_days": 7, "required_days": 7}
  }
}
```

---

## 四、配置项设计

### 4.1 新增配置（`Configure.json` → `RemoteData` 节点下）

```json
{
  "RemoteData": {
    "enabled": true,
    "protocol": "sftp",
    "host": "127.0.0.1",
    "port": 2022,
    "user": "nixevol",
    "remote_dir": "/CapacityReportData",
    "passive": true,
    "timeout": 30,
    "auto_delete_source": true,
    "passwd": "242520",

    "auto_scheduler": {
      "enabled": false,
      "check_interval_hours": 1,
      "expected_directories": [
        "4G/FDD",
        "4G/900",
        "5G/2.6",
        "5G/700"
      ],
      "week_offset": 0
    }
  }
}
```

### 4.2 字段说明

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enabled` | bool | `false` | 是否启用自动调度 |
| `check_interval_hours` | int | `1` | 检查间隔（小时），最小1 |
| `expected_directories` | list[str] | `[]` | 需要检测就绪的子目录路径列表（相对于 `remote_dir`）。为空时按实际 ZIP 所在目录逐个检测 |
| `week_offset` | int | `0` | 周偏移，`0` = 检查上周，`-1` = 检查上上周 |

### 4.3 约束规则

1. **自动调度开启时，`auto_delete_source` 强制为 `true`**（前端灰显、后端校验）
2. `expected_directories` 为空时按远程 ZIP 实际所在目录逐个检测
3. `check_interval_hours` 最小值为 1

---

## 五、代码改动计划

### 5.1 后端

#### `app/config.py`
- `RemoteDataConfig` 新增 4 个字段 + `AutoSchedulerConfig` 子配置类
- 更新 `from_dict()`、`to_dict()`、`to_file_dict()` 序列化逻辑
- 新增约束校验：`auto_scheduler.enabled = true` 时强制 `auto_delete_source = true`

#### `app/services/remote_download.py`
- 新增 `list_remote_zip_files(directory: str | None) -> list[RemoteFileInfo]`：递归列出指定远程目录下所有 ZIP 文件路径、相对路径、所在目录和大小（只扫描，不下载）
- 远程下载会先按每个实际目录筛选最近 7 天 ZIP；自动调度触发时按 ready flag 中的目标日期精确下载，避免数据就绪后远程目录又出现新文件时误下载非目标周数据。

#### `app/services/auto_scheduler.py`（**新建**）
- `AutoScheduler` 类
  - `start()` / `stop()`：启动/停止后台定时线程
  - `check_and_run()`：检查 → 就绪 → 触发处理
  - `_is_ready()`：检查所有目录就绪状态
  - `_mark_ready()` / `_clear_ready()`：标识文件管理
  - `_trigger_processing()`：复用 `remote.py` 中的 `_run_remote_processing` 逻辑
  - `get_status()` → dict：返回调度器当前状态

#### `app/main.py`
- 应用启动时初始化 `AutoScheduler` 并 start
- 应用关闭时 stop

#### `app/api/routers/remote.py`
- 新增 `GET /api/remote/scheduler/status`：查询调度状态
- 新增 `POST /api/remote/scheduler/trigger`：手动触发一次检测
- 修改 `POST /api/remote/start`：自动调度期间禁止手动触发（避免冲突）

### 5.2 前端

#### `frontend/src/components/SettingsPanel.vue`
在"远程数据源"配置区域新增"自动调度"折叠卡片：
- 启用开关
- 检查间隔（小时）输入框
- 预期目录列表（支持增删）
- 周偏移选择（默认上周）
- 状态面板：下次检查时间、上次检查结果、就绪状态、各目录检测结果

---

## 六、日志与监控

### 6.1 日志示例

```
[10:00:00] 自动调度：开始检查远程目录就绪状态
[10:00:01] 自动调度：连接 SFTP 127.0.0.1:2022
[10:00:02] 自动调度：检查 4G/FDD → 找到 5/7 天文件（缺少 2026-05-13, 2026-05-14）
[10:00:03] 自动调度：检查 4G/900 → 找到 7/7 天文件 ✓
[10:00:04] 自动调度：检查 5G/2.6 → 找到 7/7 天文件 ✓
[10:00:05] 自动调度：检查 5G/700 → 找到 6/7 天文件（缺少 2026-05-18）
[10:00:06] 自动调度：数据未就绪（2/4 目录满足），等待下次检查
...
[11:00:00] 自动调度：开始检查远程目录就绪状态
[11:00:05] 自动调度：所有目录数据就绪 (4/4)，写入标识文件
[11:00:06] 自动调度：触发远程下载处理任务
[11:05:00] 自动调度：任务处理成功
[11:05:01] 自动调度：远程源文件已清理
[11:05:02] 自动调度：已清除就绪标识，继续监控
```

### 6.2 状态接口响应

```json
GET /api/remote/scheduler/status

{
  "enabled": true,
  "running": true,
  "next_check_at": "2026-05-19T12:00:00",
  "last_check_at": "2026-05-19T11:00:00",
  "last_result": "triggered",
  "failure_count": 0,
  "task_running": false,
  "ready_flag": {
    "exists": false
  },
  "target_week": {
    "start": "2026-05-12",
    "end": "2026-05-18"
  },
  "directory_status": {
    "4G/FDD": {"found_days": ["2026-05-12"], "found_count": 7, "required_count": 7, "ready": true},
    "4G/900": {"found_days": ["2026-05-12"], "found_count": 7, "required_count": 7, "ready": true},
    "5G/2.6": {"found_days": ["2026-05-12"], "found_count": 7, "required_count": 7, "ready": true},
    "5G/700": {"found_days": ["2026-05-12"], "found_count": 7, "required_count": 7, "ready": true}
  }
}
```

---

## 七、异常处理

| 场景 | 处理方式 |
|------|----------|
| SFTP/FTP 连接失败 | 记录错误日志，等下次周期重试 |
| 连续失败 ≥3 次 | 在前端调度状态面板显示红色失败状态 |
| 处理失败 | **保留就绪标识**，下次检查时直接触发处理（不重新检测） |
| 远程目录不存在 | 跳过该目录，记录警告，其他目录正常检测 |
| 目录内无 ZIP 文件 | 该目录判定为未就绪 |
| 手动触发远程处理 | 自动调度运行中禁止手动触发，反之亦然（互斥锁复用 `global_task_lock`） |

---

## 八、测试要点

1. **文件名解析**
   - `XXX_202605110000_202605120000.zip` → 2026-05-11 ✓
   - `XXX_202605110000.zip` → 2026-05-11 ✓
   - `no_date_here.zip` → None（跳过）
   - `XXX_20260511000012345.zip` → 14位匹配 → 2026-05-11 ✓

2. **就绪检测**
   - 所有目录都覆盖7天 → 就绪
   - 某目录缺少1天 → 未就绪
   - `expected_directories` 为空 → 只检测根目录
   - 子目录不存在 → 跳过并记录警告

3. **调度流程**
   - 检测 → 写标识 → 触发处理 → 成功 → 删标识 → 循环
   - 处理失败 → 保留标识 → 下次直接触发

4. **配置联动**
   - 开启自动调度 → `auto_delete_source` 自动变为 true
   - 修改配置 → 调度器热重载

5. **互斥**
   - 自动调度运行中 → 手动触发被拒绝
   - 手动任务运行中 → 自动调度跳过本轮

---

## 九、实施步骤与工时估算

| 步骤 | 内容 | 预估工时 |
|------|------|----------|
| 1 | `app/config.py`：扩展 `RemoteDataConfig`，新增 `AutoSchedulerConfig` | 20min |
| 2 | `app/services/remote_download.py`：新增 `list_remote_zip_names()` | 30min |
| 3 | `app/services/auto_scheduler.py`：新建调度器核心逻辑 | 2h |
| 4 | `app/api/routers/remote.py`：新增状态查询和手动触发接口 | 30min |
| 5 | `app/main.py`：集成调度器启动/停止 | 10min |
| 6 | `frontend/src/components/SettingsPanel.vue`：自动调度配置 UI | 1.5h |
| 7 | `frontend/src/api/client.ts`：新增 API 调用方法 | 10min |
| 8 | 联调测试 | 1h |
| **合计** | | **约6h** |

---

## 十、注意事项

1. **不改动现有处理流程**：自动调度只是在现有"远程下载并处理"之上加了一层检测和触发机制
2. **标识文件是运行时数据**：`cache/auto_scheduler/ready.flag` 不应提交到版本库
3. **`week_offset` 用途**：如果某周处理失败需要下周补跑，可将 `week_offset` 设为 `-1` 来检查上上周的数据
4. **配置热重载**：修改自动调度配置后，调度器应在下一次检查周期使用新配置（不需要重启服务）
5. **前端 `auto_delete_source` 联动**：当自动调度开启时，前端应将"处理成功后删除源文件"开关灰显为强制开启状态
