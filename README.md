# warpoc — 免费 Cloudflare WARP → OpenClash 订阅

自动注册免费 Cloudflare WARP 账号（账号返回 `warp_plus: true`），转成
Clash / OpenClash 可直接订阅的 YAML，并通过 GitHub Actions **每 6 小时自动更新一次**。

## 订阅链接

> 注意：以下链接需要**仓库为 public** 才能免登录访问。当前仓库为 private，需要
> 公开后才能使用（或改用你自己的中转）。

- GitHub raw：`https://raw.githubusercontent.com/naughtypi634/warpoc/main/output/warp.yaml`
- ghproxy 加速（国内友好）：`https://ghproxy.net/https://raw.githubusercontent.com/naughtypi634/warpoc/main/output/warp.yaml`
- jsDelivr CDN：`https://cdn.jsdelivr.net/gh/naughtypi634/warpoc@main/output/warp.yaml`

## OpenClash 使用

1. 打开 OpenClash → 订阅管理 → 添加订阅，粘贴上面的订阅链接。
2. 更新订阅后，在代理组里选择 `WARP`（手动选择）或 `WARP-AUTO`（自动测速选优）。

## 工作原理

1. `generate.py` 调用 Cloudflare 移动端注册接口
   （`https://api.cloudflareclient.com/v0i2310010000/reg`）注册 N 个免费 WARP
   账号，每个账号自带 WireGuard 私钥/地址。
2. 每个账号配一组 WARP 优选 IP 端点，生成 `type: wireguard` 代理节点。
3. 输出完整 Clash 配置到 `output/warp.yaml` 并提交，OpenClash 定时拉取即可。

## 手动触发更新

GitHub 仓库 → Actions → `Update WARP Subscription` → Run workflow。

## 关于 WARP+ 的说明

- 2026 年起 Cloudflare 已关闭“邀请返利刷量”接口（错误码 1070），因此无法再
  免费刷取 WARP+ 配额；本项目生成的是**免费 WARP 账号**（`warp_plus: true`，
  配额为 0，流量不限速免费使用）。
- 如果你有自己的 WARP+ / Zero Trust 团队账号，可以把 wgcf 生成的
  `*.conf` 配置放进 `profiles/` 目录，`generate.py` 会自动合并进订阅。
- 账号每天/每次更新都会重新注册，密钥不持久化，旧账号自动作废，无需担心泄漏。

## 自定义

- `ACCOUNT_COUNT` 环境变量控制每轮注册的账号数（workflow 里默认 3）。
- `ENDPOINTS` 列表在 `generate.py` 里，可用 WARP 优选 IP 工具替换成你测速后的
  更优节点。
