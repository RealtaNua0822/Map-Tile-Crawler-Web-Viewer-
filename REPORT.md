# 实验报告：时空数据获取与服务（地图瓦片爬虫与发布系统）

## 目录

- 第1章 研究背景与意义
- 第2章 实验方案设计
  - 2.1 关键技术原理分析
  - 2.2 整体方案流程设计
- 第3章 实验步骤与代码实现
  - 3.1 环境准备
  - 3.2 核心模块说明与关键代码片段
  - 3.3 使用示例与运行命令
- 第4章 实验结果验证与分析
  - 4.1 实验环境
  - 4.2 实验结果分析
    - 4.2.1 功能验证
    - 4.2.2 性能测试分析
- 第5章 总结
  - 5.1 遇到的问题及解决方法
  - 5.2 下一步研究方向
  - 5.3 心得体会
- 参考文献
- 建议意见

---

## 第1章 研究背景与意义

随着地理信息系统（GIS）和 Web 地图服务的广泛应用，快速获得并发布栅格地图瓦片（tile）成为很多应用的基础能力。基于多分辨率瓦片金字塔模型，可以高效地在各种缩放级别下浏览地图。通过编写爬虫自动获取开源地图或其他在线地图瓦片并以标准 z/x/y 方式组织、发布，可以用于离线分析、专题可视化或提供自定义地图服务。本实验旨在让学生理解瓦片坐标系统、并发下载、数据组织与瓦片服务发布。

## 第2章 实验方案设计

### 2.1 关键技术原理分析

- 瓦片坐标（Slippy map）：采用 z（zoom）/x（column）/y（row）索引。经纬度到瓦片坐标的转换基于 Web Mercator 投影与标准公式。
- 数据组织：按照 `out/{z}/{x}/{y}.{ext}` 的文件系统结构存储，便于直接用静态文件或简单 HTTP 服务按路径返回瓦片。
- 并发下载：使用线程池（ThreadPoolExecutor）提升下载吞吐，结合速率限制（间隔 sleep）降低被封风险。
- 请求头与反爬：通过 `headers` 与 `Referer`、`User-Agent` 模拟浏览器请求；支持代理（proxies）。
- 服务发布：使用 Flask 提供简单 `GET /tiles/{z}/{x}/{y}.png` 接口，用于本地或内网测试。
- 前端可视化：前端可使用 Leaflet 或类似库，通过配置 tile URL 模板加载服务。

### 2.2 整体方案流程设计

1. 输入区域（矩形 bbox 或 GeoJSON 多边形）和目标 zoom。  
2. 计算对应的 tile x/y 范围（函数 `bbox_to_tile_range` 或 `geojson_bbox`）。  
3. 根据 URL 模板（支持占位符 `{z}`、`{x}`、`{y}` 和可选 tokens）拼接瓦片请求 URL。  
4. 使用并发下载模块按规则保存到 `out/{z}/{x}/{y}.{ext}`（支持自动判断扩展名）。  
5. 提供本地 Flask 服务读取 `out/` 返回图片接口。  
6. 使用 Leaflet 等前端加载该服务进行可视化验证。

## 第3章 实验步骤与代码实现

### 3.1 环境准备

- 操作系统（示例）：Windows 10/11
- Python：3.x（建议 3.8+）
- 依赖安装：

```powershell
cd E:\work\ex_1
python -m pip install -r requirements.txt
```

依赖示例（`requirements.txt`）：`requests`, `Pillow`, `Flask`, `tqdm`, `flask-cors`。

仓库关键文件：
- `src_all/python/tile_crawler.py`：爬虫主程序（支持从 `config.json` 读取 `headers`、`tokens`、`proxies`）
- `src_all/python/stitch_tiles.py`：瓦片拼接工具
- `src_all/python/stitch_all.py`：批量拼接脚本
- `src_all/python/server.py`：Flask 瓦片服务器
- `src_all/python/test_tiles.py`：基础验证脚本
- `out/`：瓦片输出目录
- `map/`：拼接后地图图像目录

### 3.2 核心模块说明与关键代码片段

- 经纬度到瓦片坐标（核心函数）示例：

```python
def latlon_to_tile_xy(lat_deg, lon_deg, z):
    lat_rad = math.radians(lat_deg)
    n = 2 ** z
    x = math.floor((lon_deg + 180.0) / 360.0 * n)
    y = math.floor((1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n)
    x = int(max(0, min(x, n - 1)))
    y = int(max(0, min(y, n - 1)))
    return x, y
```

- 下载与保存（并发）核心说明：使用 `requests.Session()` 复用连接，先写入 `.part` 临时文件，成功后重命名为最终文件名；支持 `headers` 参数、重试、timeout、skip-existing 等。

- 配置读取：脚本支持 `--config` 参数并会按优先级尝试读取 `config.json`（`src_all/python/config.json`、仓库根、当前工作目录），并合并 `headers`、`tokens`、`proxies`。

示例 `config.json`（放在 `src_all/python/` 或仓库根）：

```json
{
  "headers": {
    "Authorization": "Bearer <your-token>",
    "Referer": "https://example.com/"
  },
  "tokens": {
    "secretId": "",
    "clientId": "",
    "expireTime": "",
    "sign": ""
  },
  "proxies": {
    "http": "",
    "https": ""
  }
}
```

### 3.3 使用示例与运行命令

- 单个 URL 下载：

```powershell
python src_all\python\tile_crawler.py --single-url "https://example.com/tile.png" --outdir out
```

- 按 bbox 批量下载（带 config）：

```powershell
python src_all\python\tile_crawler.py --bbox 115.4,39.4,117.5,41.1 --zoom 8 --template "https://tile.openstreetmap.org/{z}/{x}/{y}.png" --outdir out --config src_all\python\config.json --concurrency 8 --rate 0.05
```

- 启动 Flask 服务：

```powershell
pip install -r requirements.txt
python src_all\python\server.py
# 访问 http://127.0.0.1:5000/tiles/8/210/95.png
```

## 第4章 实验结果验证与分析

### 4.1 实验环境

- 主机系统：Windows（实验机器）
- Python 环境：已安装 `requests`, `Pillow`, `Flask`, `tqdm` 等
- 测试数据：仓库自带 `out/` 下示例瓦片用于验证

### 4.2 实验结果分析

#### 4.2.1 功能验证

- `test_tiles.py` 执行能列出 `out/` 下各级瓦片统计并检查示例瓦片存在性。  
- 启动 `server.py` 后，可通过 `GET /tiles/{z}/{x}/{y}.png` 成功获取瓦片（HTTP 200），服务器日志会输出 `Serving tile: ...` 信息。  
- `tile_crawler.py` 在读取到 `config.json` 时会打印 `Loaded config from: <path>`，并使用 config 中 headers/tokens 执行下载请求。

#### 4.2.2 性能测试分析

- 在 `--concurrency 8`、`--rate 0.05` 的默认设置下，小范围抓取稳定且速度合理。  
- 增大并发需配合更严格的限速或代理策略以避免被源站封禁。  
- 大规模抓取需考虑磁盘 I/O、网络带宽及目标站点的访问限制。

## 第5章 总结

### 5.1 遇到的问题及解决方法

- Headers 固定：解决方法为新增 `--config` 和 `config.json`，通过配置文件与 CLI 合并自定义 headers 和 tokens。  
- 扩展名识别：根据 URL 或响应 `Content-Type` 判定并保存正确后缀，支持 webp→png 转换（需 Pillow）。  
- 被封风险：通过 `rate`、`proxies` 和合理并发控制降低风险。

### 5.2 下一步研究方向

- 使用分布式下载或队列系统支持大规模抓取；  
- 使用 MBTiles/SQLite 存储瓦片以便查询与传输；  
- 采用生产级 WSGI + Nginx 静态缓存作为发布方案；  
- 前端集成 Leaflet/Mapbox 并添加任务管理界面。

### 5.3 心得体会

通过本实验掌握了瓦片坐标体系、并发 HTTP 下载、文件组织与简单的瓦片发布流程。外置配置提高了工具的可重用性，也提醒在网络爬取时注意合规与礼貌访问。

## 参考文献

- OpenStreetMap Tile Usage Policy — https://operations.osmfoundation.org/policies/tiles/  
- Slippy Map Tilenames — https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames  
- Leaflet — https://leafletjs.com/  
- requests — https://docs.python-requests.org/  
- Pillow — https://pillow.readthedocs.io/

## 建议意见

- 将 `src_all/python/config.json` 改名为 `config.json.example` 并把真实配置加入 `.gitignore`，避免凭证泄露；我可以帮忙实现。  
- 若需对外提供稳定地图服务，建议使用生产 WSGI + 反向代理并启用静态缓存。  
- 我可以为你：  
  - 把 `config.json.example` 与 `.gitignore` 更新并提交，  
  - 编写 Dockerfile 将服务容器化，  
  - 将本报告提交并创建 PR（如果需要）。

---

*报告已由工具自动生成并保存于项目根 `REPORT.md`。*
