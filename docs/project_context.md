# 项目上下文记忆 (Project Context)

## 最近更新记录

### 2026-04-23: 鉴权改为全屏登录页模式 + 退出登录
- **问题**: 之前的鉴权方案只在 API 层拦截 401 后弹出登录弹窗，但主页面 HTML 内容已经完整渲染并暴露给用户（未登录也能看到界面），不符合安全预期。
- **修复方案**:
  - **登录页独立化**: 将登录从弹窗模式（`loginModal`）改为独立全屏登录页面（`#loginPage`），未登录时主内容区 `#appContainer` 设为 `display:none`，只显示登录页。
  - **Token 启动校验**: `DOMContentLoaded` 时先检查 `localStorage` 中的 token，无 token 直接显示登录页；有 token 则用 `/api/config` 接口验证有效性，401 则跳回登录页。
  - **退出登录功能**: 每个页面 header 右上角新增退出按钮（`⏻` 图标，`.logout-btn` 类），事件委托统一处理，清除 token 后显示登录页。
  - **登录后免刷新**: 登录成功后如果应用模块未初始化则调用 `initApp()` 完成初始化，无需 `window.location.reload()`。
- **涉及文件**: `static/index.html`、`static/js/app.js`、`static/css/style.css`
- **注意事项**: `showLoginModal()` 函数保留作为兼容入口（API 返回 401 时调用），内部已重定向到 `showLoginPage()`。

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
