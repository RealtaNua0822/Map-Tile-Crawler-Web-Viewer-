# 地理栅格瓦片爬虫与发布系统

完整的地图瓦片爬取、处理、拼接和 Web 发布工具集。支持签名 URL、多源瓦片、格式转换、实时浏览等功能。

## 项目概览

本项目包含以下核心功能：

- **瓦片爬虫** (`tile_crawler.py`)：下载地图瓦片，支持 bbox/GeoJSON/单个 URL，支持签名 URL 和自定义请求头
- **瓦片拼接** (`stitch_tiles.py`, `stitch_all.py`)：将瓦片拼接为大图（PNG），支持多个 zoom 级别
- **Web 服务** (`server.py`)：Flask 服务器，提供 REST API 和交互式地图浏览界面（Leaflet）
- **完整文档** (`USAGE.md`)：详细的 API 文档、参数说明和示例

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 下载瓦片

```bash
# 下载北京地区 zoom=8 的瓦片
python -m src.tile_crawler \
  --bbox 115.4,39.4,117.5,41.1 \
  --zoom 8 \
  --template "https://tiles.../img/{z}/{x}/{y}?..." \
  --outdir out \
  --convert-webp-to-png
```

### 3. 启动 Web 服务

```bash
python server.py

# 在浏览器访问 http://localhost:5000
```

## 功能特性

### tile_crawler.py

- ✅ 支持 bbox（地理边界框）、GeoJSON 多边形、单个 URL
- ✅ 支持签名 URL（secretId、clientId、expireTime、sign）
- ✅ 自定义请求头（Referer、User-Agent、Authorization 等）
- ✅ 速率限制和重试机制
- ✅ WebP→PNG 自动转换
- ✅ 断点续传（--skip-existing）
- ✅ 并发下载
- ✅ Dry-run 模式（估算不下载）

### stitch_tiles.py & stitch_all.py

- ✅ 将瓦片按网格拼接为大图
- ✅ 支持按 bbox 或瓦片坐标范围指定
- ✅ 批量处理多个 zoom 级别
- ✅ 自动文件命名（经纬度 + zoom）
- ✅ 缺失瓦片透明填充

### server.py

- ✅ RESTful API：`GET /tiles/{z}/{x}/{y}.png`
- ✅ 交互式地图浏览（Leaflet.js）
- ✅ 实时显示坐标、瓦片信息
- ✅ 自动格式转换（WebP→PNG）
- ✅ CORS 支持
- ✅ 缓存控制
- ✅ 统计接口：`GET /api/tile-stats`

## 文件结构

```
.
├── README.md                    # 项目说明（简明）
├── USAGE.md                     # 完整使用文档
├── requirements.txt             # Python 依赖
├── server.py                    # Flask Web 服务
├── src/
│   ├── __init__.py
│   ├── tile_crawler.py          # 瓦片下载工具（CLI + API）
│   ├── stitch_tiles.py          # 单个 zoom 拼接工具
│   └── stitch_all.py            # 批量拼接工具
├── out/                         # 下载的瓦片存储（z/x/y 目录结构）
├── map/                         # 拼接后的大图存储
└── test_tiles.py                # 简单测试脚本
```

## 示例工作流

### 完整流程：下载 → 拼接 → 浏览

```bash
# 1. 下载瓦片（zoom=7..9，北京地区）
for z in 7 8 9; do
  python -m src.tile_crawler \
    --bbox 115.4,39.4,117.5,41.1 \
    --zoom $z \
    --template "https://tiles.../img/{z}/{x}/{y}?..." \
    --outdir out \
    --concurrency 8 \
    --rate 0.02 \
    --skip-existing \
    --convert-webp-to-png
done

# 2. 生成拼接图（每个 zoom 一张大图）
python -m src.stitch_all \
  --bbox 115.4,39.4,117.5,41.1 \
  --min-zoom 7 \
  --max-zoom 9 \
  --output-dir map

# 3. 启动 Web 服务
python server.py

# 4. 打开浏览器访问 http://localhost:5000
```

## 核心参数速查

### tile_crawler.py

| 参数 | 说明 | 示例 |
|------|------|------|
| `--bbox` | 地理边界框 | `115.4,39.4,117.5,41.1` |
| `--zoom` | 缩放级别 | `8` |
| `--template` | URL 模板 | `https://tiles.../img/{z}/{x}/{y}` |
| `--outdir` | 输出目录 | `out` |
| `--concurrency` | 并发数 | `8` |
| `--rate` | 请求延时（秒） | `0.02` |
| `--convert-webp-to-png` | 格式转换 | （标志） |
| `--skip-existing` | 断点续传 | （标志） |

### server.py

**API 接口**：

| 接口 | 说明 | 返回 |
|------|------|------|
| `GET /` | 交互式地图 | HTML + Leaflet |
| `GET /tiles/{z}/{x}/{y}.png` | 瓦片 PNG | 256×256 图像 |
| `GET /api/tile-stats` | 统计信息 | JSON |

**启动**：

```bash
python server.py
# 访问 http://localhost:5000
```

## 详细文档

**→ 见 [USAGE.md](./USAGE.md)**

USAGE.md 包含：

- 📖 完整参数说明与类型
- 🔧 Python API 函数参考
- 📋 详细的使用示例
- ❓ 常见问题与故障排查
- 🚀 扩展方案（GeoTIFF、MBTiles 等）

## 注意事项

⚠️ **道德与法律**：

- 仅用于学习和研究
- 遵守瓦片源的服务条款
- 不进行商业性大规模爬取（除非获得授权）
- 注意速率限制，避免对服务器造成负担

## 示例数据

项目已包含北京地区的瓦片样本：

- **范围**：lat 39.4°-41.1°, lon 115.4°-117.5°
- **Zoom**：7-12（共 6 个级别）
- **瓦片数**：~1800 个
- **源**：GeoVisEarth 瓦片服务
- **大小**：~200 MB（PNG + WebP）

可直接启动 Web 服务进行浏览。

## 常见问题

### Q: 网页显示灰色？

A: 检查 `out/` 是否有 PNG 文件。使用 `--convert-webp-to-png` 重新下载。详见 USAGE.md。

### Q: 下载出错（403/401）？

A: 检查签名令牌和请求头是否正确。见 USAGE.md 故障排查。

### Q: 如何只下载特定地区？

A: 用 `--bbox` 指定经纬度范围。示例：`115.4,39.4,117.5,41.1`

## 快速命令

```bash
# 单个瓦片测试
python -m src.tile_crawler --single-url "https://..." --outdir out

# 估算瓦片数量（不下载）
python -m src.tile_crawler --bbox 115.4,39.4,117.5,41.1 --zoom 10 --template "..." --dry-run

# 启动服务
python server.py

# 拼接单个 zoom
python -m src.stitch_tiles --zoom 8 --bbox 115.4,39.4,117.5,41.1 --output map/z8.png

# 批量拼接
python -m src.stitch_all --bbox 115.4,39.4,117.5,41.1 --min-zoom 7 --max-zoom 12 --output-dir map
```

---

**更多详情请查阅 USAGE.md**
