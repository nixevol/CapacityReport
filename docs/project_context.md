# 项目上下文记忆 (Project Context)

## 最近更新记录

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
