# db_init —— 数据库前置检查 / 结构表初始化

本目录存放各数据库「**必须存在的结构表**」的初始化 SQL。程序启动时、以及每次执行
CellData 脚本前，会由 `app/db_init.py` 的 `ensure_required_tables()` 自动检查：
**某张必需表不存在时，就执行对应的初始化 SQL 把它建好**，从而避免运行过程中因缺表报错。

## 文件命名规则

```
<库标识>.<表名>.sql
```

- `<库标识>` 决定连到哪个库（**实际库名以用户在「系统设置」里配置的为准，不写死**）：
  | 库标识 | 对应配置 | 说明 |
  |---|---|---|
  | `celldata` | `CellData.MySQL_DBInfo` | CellData 库，始终直连 MySQL |
  | `capacityreport` | `MySQL_DBInfo`（主仓库） | 仅当仓库为「直连 MySQL」时检查；Metrix 模式跳过 |
- `<表名>` 为要检查/创建的表名（区分库标识后剩余部分，表名本身不含 `.`）。

例：`celldata.sector.sql` = 在 CellData 库里确保 `sector` 表存在。

## 执行时机与规则

- 触发点：应用启动（`app/main.py` lifespan）、执行 CellData 脚本前（`execute_celldata_script`）。
- 判定：用 `SHOW TABLES` 取现有表，**仅当目标表不存在**时才执行该 `.sql`；已存在则整文件跳过。
- 因此带预设数据的表（如 `sector_band_ref`）**只在首次创建时写入预设**，之后你在库里
  对它的任何增改都会被保留，不会被覆盖或重置。
- 全过程 best-effort：单库连不上 / 单表初始化失败只记日志，不会中断启动或数据处理。
- 前提：**数据库本身需已存在**（本机制只建表，不建库）。

## 当前清单

### celldata（CellData 库）
| 文件 | 表 | 用途 |
|---|---|---|
| `celldata.cellinfo.sql` | `cellinfo` | 小区基础信息。正常由导入自动建，此处兜底。 |
| `celldata.sector.sql` | `sector` | 扇区表，CellData.sql 逆推写入目标。**不会被任何流程自动创建**，必须前置建好。 |
| `celldata.sector_band_ref.sql` | `sector_band_ref` | 频段特征库（频点区间+PLMN→制式/频段），含预设 10 条规则，供逆推用，可自行增改。 |

### capacityreport（主仓库）
当前**无需前置建表**：主仓库的原始表（`4G_UD`/`5G_UD`）、结果表（`4G_结果表`/`5G_结果表`）
以及从 CellData 复制过来的 `sector`/`cellinfo`，都由导入流程 / `ReportScript.sql` /
跨库复制以 `DROP TABLE IF EXISTS` + `CREATE` 动态生成，结构随源数据字段而定，
不宜在此预先固定结构（会与动态建表冲突）。如确有需要，按上面的命名规则新增
`capacityreport.<表名>.sql` 即可被自动纳入检查。

## 新增一张必需表

1. 在本目录新建 `<库标识>.<表名>.sql`，内容用 `CREATE TABLE IF NOT EXISTS ...`；
   如需预设数据，在其后追加 `INSERT ...`（只会在表首次创建时执行）。
2. 无需改 Python，`ensure_required_tables()` 会自动发现并按需执行。
