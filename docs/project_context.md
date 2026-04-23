# 项目上下文记忆 (Project Context)

## 最近更新记录

### 2026-04-23: 登录页后端级别隔离 + 退出登录
- **问题**: 之前登录页和主页面在同一个 HTML 文件中，即使前端隐藏了主内容，用户仍能通过查看源码看到完整的主页面 HTML。
- **最终方案 — 后端级别隔离**:
  - **独立 `login.html`**: 创建 `static/login.html` 作为独立登录页面，自包含样式和逻辑，不引用主程序任何 JS/CSS。
  - **后端路由鉴权**: `app/main.py` 的 `/` 路由从 cookie 中读取 `token` 并验证，有效则返回 `index.html`，无效则返回 `login.html`。**未登录时服务器根本不会返回 `index.html` 的内容**。
  - **Cookie + localStorage 双存储**: 登录成功后 token 同时存入 cookie（供后端 `/` 路由判断）和 localStorage（供前端 API 请求 Bearer header）。
  - **退出登录**: 每个页面 header 右上角有退出按钮（`⏻`），清除 cookie + localStorage 后跳转到 `/`（后端自动返回登录页）。
  - **API 401 处理**: `showLoginModal()` 函数保留，内部清除 token 后 `window.location.href = '/'` 跳转到登录页。
- **涉及文件**: `static/login.html`（新增）、`app/main.py`、`static/index.html`、`static/js/app.js`、`static/css/style.css`

### 2026-04-22: 增加 JWT 鉴权和接口安全控制
- **问题背景**: 网管部门通报安全问题，扫描到项目存在暴露的 API 文档（/docs, /redoc, /openapi.json），并且 API 接口没有使用授权控制，要求快速增加鉴权。
- **架构变更**:
  - FastAPI 初始化时关闭 `docs_url`、`redoc_url` 和 `openapi_url`。
  - 由于依赖环境限制（`uv` 虚拟环境被破坏），为实现快速且无额外依赖的 JWT 方案，在 `app/main.py` 中自行使用 Python 标准库 `hmac`、`hashlib`、`base64` 实现了原生的 JWT `create_jwt_token` 和 `verify_jwt_token`。
  - 在 `app/main.py` 增加了一个登录接口 `/api/login`，密码验证通过后下发 token。当前密码硬编码为 `admin`。
  - 添加了全局路由中间件 `@app.middleware("http") jwt_middleware`，拦截所有 `/api/` 路由（除登录外），验证请求头 `Authorization: Bearer <token>` 是否合法或过期。
- **前端适配**:
  - `static/index.html` 增加了 `loginModal`（系统登录弹出框）。
  - `static/js/app.js` 的 `api` 统一调用封装修改，支持在请求头附带 token；同时增加对 401 状态码的拦截，一旦失效将移除 token 并在页面弹出 `showLoginModal`。
  - `static/js/app.js` 在处理 XHR 文件上传时，一并增加了 token 的拼装及 401 处理。
- **经验教训**: 在部署内网或暴露环境前，快速关闭 Swagger OpenAPI 的自带页面十分重要。为了绕过环境管理工具或网络导致库安装失败，通过原生标准库提供足够安全的 JWT 校验能极大提升应急处理效率。
