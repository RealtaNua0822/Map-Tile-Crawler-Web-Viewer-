# 地理栅格瓦片爬虫与发布系统

# 项目总览（已合并）

此仓库为“地图瓦片爬虫与发布系统”。我已将源代码复制到统一目录 `src_all/`（见下文），并把文档合并为本文件的精简版本。原始文档已备份到 `docs_backup/`。

目的：
- 将所有源码放在一个易查找的位置，便于维护与发布。
- 把散落的说明合并为单一 `README.md`，便于快速上手。

重要：迁移为“复制”，原始文件仍保留在原路径。若需要我可以执行移除或重命名原始文件。

**统一源码位置**
- `src_all/python/` — Python 源文件（`tile_crawler.py`, `stitch_tiles.py`, `stitch_all.py`, `server.py`, `test_tiles.py`）
- `src_all/node_backend/` — Node 后端（`server.js`, `package.json`, `database.js`）
- `src_all/www/` — 静态前端页面（`index.html` 占位）

快速说明：
- Python 服务仍依赖 `requirements.txt`（根目录），可按原方式安装。
- Node 后端在 `src_all/node_backend/`，可用 `npm install` 之后 `npm start` 启动（如需要）。

快速开始（Python）：

```powershell
cd .\ex_1
# 地理栅格瓦片爬虫与发布系统

本仓库为“地图瓦片爬虫与发布系统（ex_1）”。源码统一放在 `src_all/python/`，主要脚本及用途如下。若需回退，原始文档已备份到 `docs_backup/`。

**仓库结构（关键）**
- `src_all/python/` — Python 源文件：`tile_crawler.py`, `stitch_tiles.py`, `stitch_all.py`, `server.py`, `test_tiles.py`
- `out/` — 瓦片存放路径（`out/{z}/{x}/{y}.png`）
- `map/` — 拼接的地图图片输出
- `requirements.txt` — Python 依赖

下面按脚本逐一说明功能与使用示例。

**`tile_crawler.py` — 瓦片爬虫**
- 功能：根据经纬度 bbox 或 GeoJSON 计算瓦片范围，按模板并发下载瓦片到 `out/`。
- 配置：支持从 JSON 文件读取 `headers`、`tokens`、`proxies`。默认搜索位置（优先级从高到低）：
  - CLI 参数 `--config PATH`
  - `src_all/python/config.json`
  - 仓库根 `config.json`
  - 当前工作目录 `config.json`
- 优先级：内置 essential headers < config.json.headers < CLI `--headers` / `--referer` / `--user-agent`。
- 常用参数（摘要）：
  - `--bbox min_lon,min_lat,max_lon,max_lat`（批量）
  - `--geojson path`（可选，替代 `--bbox`）
  - `--zoom Z`（必需，批量抓取）
  - `--template "...{z}/{x}/{y}..."`（URL 模板）
  - `--outdir out`（输出目录，默认 `out`）
  - `--concurrency N`（并发线程）
  - `--config PATH`（指定 JSON 配置文件）
  - `--single-url URL`（下载单个完整 URL）

示例：
```powershell
# 从 config.json 读取 headers 并抓取 bbox
python src_all\python\tile_crawler.py --bbox 115.4,39.4,117.5,41.1 --zoom 8 --template "https://tile.openstreetmap.org/{z}/{x}/{y}.png" --outdir out --config src_all\python\config.json

# 直接在 CLI 指定额外 headers（覆盖 config）
python src_all\python\tile_crawler.py --bbox 115.4,39.4,117.5,41.1 --zoom 8 --headers '{"Authorization":"Bearer TOKEN"}'

# 下载单个 URL
python src_all\python\tile_crawler.py --single-url "https://example.com/tile.png" --outdir out
```

示例 `config.json`（放在 `src_all/python/` 或仓库根）：

```json
{
  "headers": {
    "Authorization": "Bearer <your-token>",
    "Referer": "https://example.com/"
  },
  "tokens": {
    "secretId": "...",
    "clientId": "...",
    "expireTime": "...",
    "sign": "..."
  },
  "proxies": {
    "http": "http://127.0.0.1:1080",
    "https": "http://127.0.0.1:1080"
  }
}
```

**`stitch_tiles.py` — 瓦片拼接工具**
- 功能：将指定 `out/{z}/{x}/{y}.*` 的瓦片拼接为一张完整图片并保存到 `map/`。
- 使用示例：
```powershell
python src_all\python\stitch_tiles.py --z 8 --xmin 210 --xmax 213 --ymin 94 --ymax 99 --out map/stitched_z8.png
```

**`stitch_all.py` — 批量拼接**
- 功能：对指定 zoom 列表或整个数据集，批量调用 `stitch_tiles` 并生成多级拼接图。

示例：
```powershell
python src_all\python\stitch_all.py --zooms 7 8 9 10
```

**`server.py` — 本地瓦片服务（Flask）**
- 功能：提供接口 `GET /tiles/{z}/{x}/{y}.png`（从 `out/` 读取）和 `GET /api/tile-stats`（返回统计信息），用于本地预览或调试。
- 快速启动：
```powershell
pip install -r requirements.txt
python src_all\python\server.py
# 访问 http://127.0.0.1:5000/tiles/8/210/95.png
```

**`test_tiles.py` — 简单文件存在性检查**
- 功能：检查 `out/` 下各级目录的瓦片计数，并能测试若干示例瓦片是否存在。
- 使用：
```powershell
python src_all\python\test_tiles.py
```

=== 额外说明 ===
- 依赖：使用 `pip install -r requirements.txt` 安装（包括 `requests`, `Pillow`, `Flask`, `tqdm`）。
- 配置优先级与安全：不要把生产 token/密钥直接提交到远端仓库（把它们放在本地 `config.json` 并列入 `.gitignore`）。
- 如果需要我可以：
  - 把 `config.json.example` 添加到仓库并在 `.gitignore` 中排除真实配置，
  - 创建 Dockerfile 以便可重复部署，
  - 把更改提交到当前分支 `now` 并打开 PR（需你确认 PR 描述）。

如果你希望我现在：
- 把示例 `config.json` 写入 `src_all/python/`（我可以现在创建）；
- 或者更新 README 中的更多细节或示例脚本，请说明你想要的格式。
