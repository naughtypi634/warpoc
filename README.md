# warpoc — 免费 Cloudflare VLESS 节点 + OpenClash 订阅

基于 [cmliu/edgetunnel](https://github.com/cmliu/edgetunnel)（GPL-2.0）的
Cloudflare Workers/Pages 免费节点方案。部署后获得一个 VLESS 节点，edgetunnel
自带**订阅系统**（按客户端 UA 自动输出 Clash / Sing-box 配置），本仓库同时提供
一个 GitHub 托管的 Clash YAML 镜像作为备用订阅链接。

> 重要：Cloudflare 免费额度为 10 万请求/天，无带宽硬性限制，看 YouTube
> （1080p 通常流畅）没问题；但用 Workers 做代理属 ToS 灰色地带，节点可能被
> Cloudflare 封禁，被封后重新部署即可。`workers.dev` / `pages.dev` 域名在大陆
> 大概率无法直连，**强烈建议绑定自定义域名**。

## 一、部署（二选一，推荐 Pages + GitHub）

### 方式 A：Cloudflare Pages + GitHub（推荐，免复制代码）

1. 登录 [Cloudflare](https://dash.cloudflare.com) → Workers 和 Pages →
   **创建应用程序** → **Pages** → **连接到 Git**。
2. 授权 GitHub，选择本仓库 `naughtypi634/warpoc` → **开始设置**。
3. 构建配置保持默认（仓库根目录的 `_worker.js` 会被自动识别），添加环境变量：
   - `ADMIN`：后台管理密码（必填，自定义，例如 `123456`）
   - `KEY`：订阅路径密钥（自定义，例如 `abc123`，订阅链接就是
     `https://你的域名/abc123`）
   - `UUID`（可选）：强制固定节点 UUID（必须是标准 UUIDv4）
4. 点击**保存并部署**。

### 方式 B：Cloudflare Worker（粘贴代码）

1. Workers 控制台 → 创建 Worker → 把根目录 [`_worker.js`](_worker.js) 的内容
   粘贴进编辑器。
2. 设置 → 变量：添加 `ADMIN`（必填）和 `KEY`、`UUID`（可选）。
3. 部署后打开 Worker 域名。

### 二、绑定 KV（两者都需要）

- 创建一个 KV 命名空间，绑定到项目，**变量名称必须是 `KV`**。
- Pages：设置 → 绑定 → 添加 → KV 命名空间；绑定后重新部署一次。

### 三、绑定自定义域名（大陆使用强烈建议）

- Pages：设置 → 自定义域 → 添加 `子域名.你的域名`（不要把根域名直接绑定）。
- Workers：触发器 → 添加自定义域。
- 需要先把域名接入 Cloudflare DNS，等待证书生效。

## 订阅链接

部署完成后，把下面链接里的 `<域名>` 换成你的实际域名、`<KEY>` 换成你设置的密钥：

- **edgetunnel 原生订阅（推荐）**：`https://<域名>/<KEY>` —— OpenClash 直接添加，
  它会按 UA 返回 Clash 配置
- **GitHub 镜像（备用）**：
  `https://raw.githubusercontent.com/naughtypi634/warpoc/main/output/vless.yaml`
  （需要仓库 Actions Secrets 配置 `VLESS_UUID` / `VLESS_HOST` 后由工作流生成）

### OpenClash 使用

1. 订阅管理 → 添加订阅 → 粘贴原生订阅链接（或镜像链接）→ 更新订阅。
2. 代理组选择 `CF`（手动）或 `CF-AUTO`（自动测速）。

## 后台管理

访问 `https://<域名>/admin`，输入 `ADMIN` 密码登录，可查看节点、修改配置、
流量统计；在后台还能复制 VLESS 分享链接。

## 说明

- 节点是固定 UUID + 固定 Worker，不需要定期轮换，订阅内容天然稳定；GitHub
  Actions 每 6 小时重新生成一次镜像文件（配置了 Secrets 后生效）。
- 本项目 `_worker.js` 与 `LICENSE` 来自 cmliu/edgetunnel（GPL-2.0），部署方式
  与原项目一致；详细图文教程见
  [edgetunnel 部署指南](https://cmliussss.com/p/edt2/)。
