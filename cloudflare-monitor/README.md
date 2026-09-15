# Cloudflare Monitor Local Dashboard

这个目录用于在本地查看当前 Orange Community 项目的 Cloudflare 资源状态。

## 运行方式

1. 先生成数据：
   ```powershell
   cd "D:\csl\个人项目\橙子社区\cloudflare-monitor"
   node .\scripts\gather-cf-status.mjs
   ```

2. 启动本地静态站点：
   ```powershell
   cd "D:\csl\个人项目\橙子社区\cloudflare-monitor"
   python -m http.server 8080
   ```

3. 打开浏览器：
   ```text
   http://localhost:8080
   ```

## 说明

- 该看板展示的内容来自当前项目真实的 Cloudflare 资源信息。
- 包括：Pages、Worker、D1、HTTPS、部署状态等。
- 数据生成脚本会读取 Wrangler 和 HTTP 健康检查结果，并写入 `data/cf-status.json`。
