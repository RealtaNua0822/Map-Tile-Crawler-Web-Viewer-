# 地图瓦片爬虫与发布系统 — 完整使用文档

本项目包含一套完整的地图瓦片爬取、处理、拼接和发布的工具链。支持从在线瓦片服务下载瓦片、本地转换、拼接为大图、通过 Web 服务发布。

## 目录

1. [安装与环境](#安装与环境)
2. [核心模块说明](#核心模块说明)
   - [tile_crawler.py — 瓦片下载工具](#tile_crawlerpy)
   - [stitch_tiles.py — 单个 zoom 拼接工具](#stitch_tilespy)
   - [stitch_all.py — 批量 zoom 拼接工具](#stitch_allpy)
   - [server.py — Web 地图服务](#serverpy)
3. [常见工作流](#常见工作流)
4. [API 参考](#api-参考)
5. [故障排查](#故障排查)

---

## 安装与环境

### 依赖包

```bash
pip install -r requirements.txt
```

**requirements.txt 内容**：
```
requests
tqdm
Pillow
Flask
flask-cors
```

### Python 版本

需要 Python 3.7+ 支持（推荐 Python 3.10+）。

---

## 核心模块说明

### tile_crawler.py

**功能**：从在线瓦片服务下载地图瓦片，支持单个瓦片、bbox 范围、GeoJSON 多边形等多种输入方式，支持签名 URL、自定义请求头、速率限制和重试。

#### 使用方式

```bash
python -m src.tile_crawler [OPTIONS]
```

#### 必需参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--zoom` / `-z` | 瓦片缩放级别 | `--zoom 8` |

#### 输入方式（三选一）

| 参数 | 说明 | 格式 |
|------|------|------|
| `--bbox` | 地理边界框 | `--bbox min_lon,min_lat,max_lon,max_lat` |
| `--geojson` | GeoJSON 文件路径（自动提取 bbox） | `--geojson polygon.geojson` |
| `--single-url` | 单个瓦片 URL（直接下载） | `--single-url "https://..."` |

#### 关键选项

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--template` | - | 瓦片 URL 模板，支持 `{z}`, `{x}`, `{y}`, `{secretId}` 等占位符 |
| `--outdir` | `out` | 输出目录（按 `{z}/{x}/{y}.ext` 组织） |
| `--concurrency` | `4` | 并发下载线程数 |
| `--rate` | `0.1` | 请求速率限制（秒/瓦片） |
| `--timeout` | `10` | 单个请求超时（秒） |
| `--retries` | `3` | 失败重试次数 |
| `--skip-existing` | `False` | 跳过已存在的文件 |
| `--convert-webp-to-png` | `False` | 自动转换 WebP 为 PNG |
| `--dry-run` | `False` | 只计算瓦片数量，不下载 |

#### 签名 URL 支持

支持模板令牌，通过 CLI 参数注入：

| 参数 | 说明 |
|------|------|
| `--secretId` | 签名 ID |
| `--clientId` | 客户端 ID |
| `--expireTime` | 过期时间戳 |
| `--sign` | 签名值 |

#### 请求头定制

| 参数 | 说明 | 格式 |
|------|------|------|
| `--referer` | HTTP Referer 头 | `--referer "https://map.example.com"` |
| `--user-agent` | 自定义 User-Agent | `--user-agent "Mozilla/5.0..."` |
| `--headers` | 额外的 HTTP 头（JSON 格式） | `--headers '{"X-Custom":"value"}'` |

#### 示例

##### 下载单个瓦片（带签名）

```bash
python -m src.tile_crawler \
  --single-url "https://tiles1.geovisearth.com/base/v1/img/8/210/95.webp" \
  --referer "https://map.example.com" \
  --user-agent "Mozilla/5.0" \
  --outdir out
```

##### 下载 bbox 范围内的瓦片（zoom=8，使用签名）

```bash
python -m src.tile_crawler \
  --bbox 115.4,39.4,117.5,41.1 \
  --zoom 8 \
  --template "https://tiles1.geovisearth.com/base/v1/img/{z}/{x}/{y}?format=webp&secretId={secretId}&clientId={clientId}&expireTime={expireTime}&sign={sign}" \
  --secretId "your_secret_id" \
  --clientId "your_client_id" \
  --expireTime 1764820008 \
  --sign "your_sign_value" \
  --outdir out \
  --concurrency 8 \
  --rate 0.02 \
  --convert-webp-to-png
```

##### 下载多个 zoom 级别（用循环）

```bash
for z in 7 8 9; do
  python -m src.tile_crawler \
    --bbox 115.4,39.4,117.5,41.1 \
    --zoom $z \
    --template "https://tiles1.geovisearth.com/base/v1/img/{z}/{x}/{y}?format=webp&secretId={secretId}..." \
    --secretId "..." \
    --outdir out \
    --skip-existing \
    --convert-webp-to-png
done
```

##### 估算瓦片数量（不下载）

```bash
python -m src.tile_crawler \
  --bbox 115.4,39.4,117.5,41.1 \
  --zoom 10 \
  --template "..." \
  --dry-run
```

#### 输出结构

```
out/
├── 7/
│   ├── 105/
│   │   ├── 47.png
│   │   ├── 47.webp
│   │   ├── 48.png
│   │   └── 48.webp
│   └── ...
├── 8/
│   ├── 210/
│   │   ├── 95.png
│   │   ├── 95.webp
│   │   └── ...
│   └── ...
└── ...
```

---

### stitch_tiles.py

**功能**：将指定 zoom 级别和范围的瓦片拼接成单张大图（PNG）。

#### 使用方式

```bash
python -m src.stitch_tiles [OPTIONS]
```

#### 参数

| 参数 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `--zoom` / `-z` | ✓ | - | 缩放级别 |
| `--input-dir` | | `out` | 输入瓦片目录 |
| `--output` | ✓ | - | 输出 PNG 文件路径 |
| `--tile-size` | | `256` | 每张瓦片像素大小 |
| `--format` | | `PNG` | 输出格式（PNG/JPEG 等） |

#### 瓦片范围指定（二选一）

| 参数 | 格式 | 说明 |
|------|------|------|
| `--bbox` | `min_lon,min_lat,max_lon,max_lat` | 地理边界框 |
| `--xrange` / `--yrange` | `x_min,x_max` / `y_min,y_max` | 瓦片坐标范围 |

#### 示例

##### 按 bbox 拼接（更常用）

```bash
python -m src.stitch_tiles \
  --zoom 8 \
  --bbox 115.4,39.4,117.5,41.1 \
  --input-dir out \
  --output map/beijing_z8.png
```

##### 按瓦片坐标范围拼接

```bash
python -m src.stitch_tiles \
  --zoom 8 \
  --xrange 210,211 \
  --yrange 95,97 \
  --input-dir out \
  --output map/beijing_z8_custom.png
```

#### 输出

- 成功时生成 PNG 文件，包含瓦片统计信息打印
- 缺失的瓦片用透明像素填充

---

### stitch_all.py

**功能**：一次性为多个 zoom 级别生成拼接大图，输出到统一目录，文件名自动包含经纬度范围和 zoom 级别。

#### 使用方式

```bash
python -m src.stitch_all [OPTIONS]
```

#### 参数

| 参数 | 必需 | 说明 |
|------|------|------|
| `--bbox` | ✓ | 地理边界框 `min_lon,min_lat,max_lon,max_lat` |
| `--min-zoom` | ✓ | 最小 zoom 级别 |
| `--max-zoom` | ✓ | 最大 zoom 级别 |
| `--input-dir` | | 输入瓦片目录（默认 `out`） |
| `--output-dir` | | 输出目录（默认 `map`） |
| `--tile-size` | | 瓦片像素大小（默认 `256`） |

#### 示例

##### 为 zoom 7-12 生成全部 PNG

```bash
python -m src.stitch_all \
  --bbox 115.4,39.4,117.5,41.1 \
  --min-zoom 7 \
  --max-zoom 12 \
  --input-dir out \
  --output-dir map
```

#### 输出文件名格式

```
{min_lon}_{min_lat}_{max_lon}_{max_lat}_z{z}.png
```

**示例**：`115.4000_39.4000_117.5000_41.1000_z8.png`

#### 输出目录结构

```
map/
├── 115.4000_39.4000_117.5000_41.1000_z7.png   (256×512 像素)
├── 115.4000_39.4000_117.5000_41.1000_z8.png   (512×768 像素)
├── 115.4000_39.4000_117.5000_41.1000_z9.png   (1024×1024 像素)
├── 115.4000_39.4000_117.5000_41.1000_z10.png  (1792×1792 像素)
└── ...
```

---

### server.py

**功能**：Flask Web 服务，提供 RESTful API 和交互式地图浏览界面。实时读取 `out/` 目录下的瓦片，支持自动格式转换和缓存。

#### 启动方式

```bash
python server.py
```

**输出**：
```
============================================================
🌍 瓦片地图服务已启动
============================================================
📍 访问地址：http://localhost:5000
🗺️  瓦片接口：/tiles/{z}/{x}/{y}.png
📊 统计接口：/api/tile-stats
============================================================
支持 zoom 范围：7-12（北京地区）
按 Ctrl+C 停止服务
============================================================
```

#### API 接口

##### 1. 主页 / 地图浏览

**端点**: `GET /`

**功能**: 返回交互式 HTML 页面（使用 Leaflet.js）

**特性**:
- 可缩放的地图视图（支持 zoom 7-12）
- 实时显示中心坐标、缩放级别、瓦片坐标
- 鼠标移动时动态更新瓦片坐标

**访问**: 在浏览器打开 `http://localhost:5000`

##### 2. 瓦片接口

**端点**: `GET /tiles/<z>/<x>/<y>.png`

**参数**:
- `z`: 缩放级别（整数，7-12）
- `x`: 瓦片列号（整数）
- `y`: 瓦片行号（整数）

**返回**: PNG 图像（256×256 像素）

**行为**:
- 优先返回 `out/{z}/{x}/{y}.png`（如已存在）
- 若无 PNG 但有 WebP，自动转换为 PNG 返回
- 缺失瓦片返回透明占位图
- 缓存头：`Cache-Control: public, max-age=86400`

**示例**:
```bash
# 直接在浏览器或 curl 中访问
curl http://localhost:5000/tiles/8/210/95.png > tile.png

# 或在 HTML 中作为图像源
<img src="http://localhost:5000/tiles/8/210/95.png" />
```

##### 3. 瓦片统计接口

**端点**: `GET /api/tile-stats`

**返回**: JSON 对象，包含每个 zoom 级别的瓦片总数

**示例响应**:
```json
{
  "7": 4,
  "8": 12,
  "9": 32,
  "10": 98,
  "11": 338,
  "12": 1300
}
```

**示例请求**:
```bash
curl http://localhost:5000/api/tile-stats | jq
```

#### CORS 支持

所有 API 接口均启用 CORS，支持跨域请求：

```javascript
fetch('http://localhost:5000/tiles/8/210/95.png')
  .then(r => r.blob())
  .then(blob => console.log('Tile loaded:', blob.size, 'bytes'));
```

#### 配置参数

在 `server.py` 中可修改以下参数：

```python
TILES_DIR = Path(__file__).parent / 'out'  # 瓦片源目录
MAPS_DIR = Path(__file__).parent / 'map'    # 预生成地图目录
PREFERRED_EXTS = ['png', 'webp', 'jpg']     # 瓦片格式优先级
```

#### 服务器配置

```python
app.run(
    debug=False,                 # 关闭调试模式
    host='127.0.0.1',           # 监听地址（仅本地）
    port=5000,                  # 监听端口
    threaded=True               # 启用线程
)
```

**修改为网络可访问**：

```python
app.run(
    host='0.0.0.0',             # 监听所有网卡
    port=5000
)
```

---

## 常见工作流

### 工作流 1: 快速下载 + 拼接 + 浏览

```bash
# 1. 下载瓦片（zoom=8，北京）
python -m src.tile_crawler \
  --bbox 115.4,39.4,117.5,41.1 \
  --zoom 8 \
  --template "https://tiles.../img/{z}/{x}/{y}?..." \
  --secretId "..." \
  --clientId "..." \
  --expireTime "..." \
  --sign "..." \
  --outdir out \
  --convert-webp-to-png

# 2. 生成拼接图（可选）
python -m src.stitch_all \
  --bbox 115.4,39.4,117.5,41.1 \
  --min-zoom 8 \
  --max-zoom 8 \
  --input-dir out \
  --output-dir map

# 3. 启动 Web 服务
python server.py

# 4. 在浏览器访问 http://localhost:5000
```

### 工作流 2: 批量多 zoom 下载

```bash
# 估算所需瓦片数量
for z in 7 8 9 10 11 12; do
  echo "Zoom $z:"
  python -m src.tile_crawler \
    --bbox 115.4,39.4,117.5,41.1 \
    --zoom $z \
    --template "..." \
    --dry-run
done

# 实际下载所有 zoom
for z in 7 8 9 10 11 12; do
  python -m src.tile_crawler \
    --bbox 115.4,39.4,117.5,41.1 \
    --zoom $z \
    --template "..." \
    --outdir out \
    --skip-existing \
    --convert-webp-to-png
done

# 一次生成所有 zoom 的拼接图
python -m src.stitch_all \
  --bbox 115.4,39.4,117.5,41.1 \
  --min-zoom 7 \
  --max-zoom 12 \
  --output-dir map
```

### 工作流 3: 单个瓦片测试

```bash
# 下载并转换单个瓦片
python -m src.tile_crawler \
  --single-url "https://tiles.../img/8/210/95.webp" \
  --referer "https://map.example.com" \
  --user-agent "Mozilla/5.0" \
  --outdir out

# 查看文件
ls -lh out/8/210/95.*
```

---

## API 参考

### tile_crawler 模块函数

#### `latlon_to_tile_xy(lat, lon, z) -> (int, int)`

将经纬度坐标转换为 Slippy Map 瓦片坐标。

```python
from src.tile_crawler import latlon_to_tile_xy

x, y = latlon_to_tile_xy(lat=40.0, lon=116.4, z=8)
print(f"Tile coordinates: ({x}, {y})")  # 输出: (210, 96)
```

#### `bbox_to_tile_range(min_lon, min_lat, max_lon, max_lat, z) -> (x_min, x_max, y_min, y_max)`

将地理边界框转换为瓦片坐标范围。

```python
from src.tile_crawler import bbox_to_tile_range

x_min, x_max, y_min, y_max = bbox_to_tile_range(
    min_lon=115.4, min_lat=39.4,
    max_lon=117.5, max_lat=41.1,
    z=8
)
print(f"Tile range: X({x_min}..{x_max}), Y({y_min}..{y_max})")
# 输出: Tile range: X(210..211), Y(95..97)
```

#### `download_tile_range(...) -> dict`

并发下载指定范围的瓦片。返回包含统计信息的字典：

```python
result = download_tile_range(
    template="https://tiles.../img/{z}/{x}/{y}?...",
    z=8,
    x_range=(210, 211),
    y_range=(95, 97),
    outdir="out",
    concurrency=8,
    rate=0.02,
    tokens={"secretId": "...", "clientId": "...", ...}
)
print(result)
# 输出: {'total': 6, 'successes': 6, 'failures': 0}
```

### stitch_tiles 模块函数

#### `stitch(z, x_min, x_max, y_min, y_max, input_dir, output, ...) -> dict`

拼接瓦片为大图。

```python
from pathlib import Path
from src.stitch_tiles import stitch

result = stitch(
    z=8,
    x_min=210, x_max=211,
    y_min=95, y_max=97,
    input_dir=Path("out"),
    output=Path("map/beijing_z8.png")
)
print(result)
# 输出: {
#   'z': 8,
#   'x_min': 210, 'x_max': 211,
#   'y_min': 95, 'y_max': 97,
#   'cols': 2, 'rows': 3,
#   'total': 6, 'missing': 0,
#   'output': 'map/beijing_z8.png'
# }
```

---

## 故障排查

### 问题 1: 瓦片下载失败（HTTP 403/401）

**原因**: 签名过期或请求头不正确

**解决**:
1. 检查 `--secretId`, `--clientId`, `--expireTime`, `--sign` 是否有效
2. 确保 `--referer` 和 `--user-agent` 符合服务器要求
3. 尝试增加 `--retries` 和 `--timeout`

```bash
python -m src.tile_crawler \
  --single-url "https://..." \
  --referer "https://map.example.com" \
  --user-agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" \
  --retries 5 \
  --timeout 20
```

### 问题 2: 网页显示灰色（瓦片加载失败）

**原因**: 瓦片文件不存在或格式不支持

**解决**:
1. 检查 `out/` 目录是否有瓦片文件：

```bash
ls -R out/ | head -20
```

2. 确保 PNG 文件存在（不只是 WebP）：

```bash
python -m src.tile_crawler \
  --bbox ... \
  --zoom 8 \
  --template "..." \
  --convert-webp-to-png  # 添加此参数
```

3. 重启服务器：

```bash
# 停止旧实例
Ctrl+C

# 重启
python server.py
```

### 问题 3: 内存不足（大 zoom 下拼接失败）

**原因**: 拼接大图时需要把整个图像加载到内存

**解决**:
1. 分别拼接不同 zoom 级别：

```bash
python -m src.stitch_tiles --zoom 10 --bbox ... --output map/z10.png
python -m src.stitch_tiles --zoom 11 --bbox ... --output map/z11.png
```

2. 减少拼接范围（只拼接关键区域）

3. 升级系统内存或改进拼接算法（流式写入）

### 问题 4: 速率限制导致下载缓慢

**原因**: `--rate` 参数过大

**解决**: 调整 `--rate` 和 `--concurrency`

```bash
# 更快：并发度高，请求间隔小
python -m src.tile_crawler \
  --bbox ... \
  --zoom 8 \
  --concurrency 16 \
  --rate 0.01

# 更稳定：并发度低，请求间隔大（对服务器友好）
python -m src.tile_crawler \
  --bbox ... \
  --zoom 8 \
  --concurrency 4 \
  --rate 0.1
```

### 问题 5: Web 服务端口被占用

**错误**: `Address already in use: ('127.0.0.1', 5000)`

**解决**:

```bash
# 方案 1: 改用其他端口（编辑 server.py）
# 找到 app.run(port=5000) 改为 port=5001

# 方案 2: 杀死占用端口的进程
lsof -i :5000  # macOS/Linux
netstat -ano | findstr :5000  # Windows

# 再用 kill/taskkill 终止该进程
```

---

## 开发与扩展

### 增加新的瓦片源

修改 `tile_crawler.py` 中的 `template` 和 `headers`：

```bash
python -m src.tile_crawler \
  --bbox ... \
  --zoom 8 \
  --template "https://new-source.com/tiles/{z}/{x}/{y}.png" \
  --referer "https://new-source.com" \
  --outdir out_newsource
```

### 自定义 HTTP 请求头

```bash
python -m src.tile_crawler \
  --bbox ... \
  --zoom 8 \
  --template "..." \
  --headers '{"Authorization":"Bearer token123","X-Custom":"value"}'
```

### 导出为 GeoTIFF（地理参考图像）

暂不直接支持，但可使用外部工具（如 GDAL）处理：

```bash
# 先生成 PNG
python -m src.stitch_all --bbox ... --min-zoom 8 --max-zoom 8 --output-dir map

# 使用 GDAL 添加地理参考
gdal_translate -of GeoTIFF \
  -a_srs EPSG:3857 \
  -a_ullr 115.4 41.1 117.5 39.4 \
  map/115.4_39.4_117.5_41.1_z8.png \
  map/beijing_z8_georef.tif
```

---

## 许可与声明

**道德与法律责任**:

- 仅用于学习、研究和个人使用
- 遵守瓦片源的服务条款（Terms of Service）
- 尊重数据提供者的知识产权
- 不用于商业目的或大规模爬取（除非获得授权）
- 使用时注意速率限制和服务器负载

---

## 示例数据集

项目中已包含北京地区（lat 39.4°-41.1°, lon 115.4°-117.5°）zoom 7-12 的示例瓦片：

- **源**: GeoVisEarth 瓦片服务
- **格式**: WebP 和 PNG（已转换）
- **总计**: ~1800 个瓦片文件
- **大小**: ~200 MB（包括 PNG 和 WebP）

用法见 [常见工作流](#常见工作流) 部分。

---

## 更新日志

- **v1.0** (2025-12-04)
  - 初版发布
  - 支持 bbox/geojson/single-url 输入
  - 支持签名 URL 和自定义请求头
  - 支持 WebP→PNG 转换
  - Web 地图服务（Leaflet 前端）
  - 完整的 CLI 和 Python API

---

**获取帮助**: 查看 `README.md` 或在源代码中查找详细注释。
