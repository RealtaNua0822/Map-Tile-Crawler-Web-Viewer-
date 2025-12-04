#!/usr/bin/env python3
"""
server.py

Flask Web 服务器，发布瓦片服务。
- 从 out/{z}/{x}/{y}.* 或 map/ 读取瓦片
- 提供 /tiles/{z}/{x}/{y}.png 接口（CORS 支持）
- 提供 / 首页（地图浏览）

启动：python server.py
访问：http://localhost:5000
"""

from flask import Flask, send_file, render_template_string, jsonify, make_response
from flask_cors import CORS
from pathlib import Path
import os
import logging

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 配置瓦片目录（指向仓库根的 out/ 和 map/）
# file is at ex_1/src_all/python/server.py -> parents[2] == ex_1
REPO_ROOT = Path(__file__).resolve().parents[2]
TILES_DIR = REPO_ROOT / 'out'
MAPS_DIR = REPO_ROOT / 'map'

# 优先查找顺序：map/{z}/{x}/{y}.png（预生成）> out/{z}/{x}/{y}.png > out/{z}/{x}/{y}.webp
PREFERRED_EXTS = ['png', 'webp', 'jpg', 'jpeg']


def find_tile_file(z: int, x: int, y: int):
    """查找瓦片文件，优先返回 PNG"""
    tile_dir = TILES_DIR / str(z) / str(x)
    tile_base = tile_dir / str(y)
    
    # 优先查找 PNG（首先）
    png_path = tile_base.with_suffix('.png')
    if png_path.exists() and png_path.is_file():
        return png_path
    
    # 再查找其他格式（webp, jpg 等）
    for ext in ['webp', 'jpg', 'jpeg']:
        tile_path = tile_base.with_suffix('.' + ext)
        if tile_path.exists() and tile_path.is_file():
            return tile_path
    
    # fallback: 查找任何扩展名
    if tile_dir.exists():
        for f in tile_dir.glob(f'{y}.*'):
            if f.is_file():
                return f
    
    return None


@app.route('/')
def index():
    """地图浏览首页（HTML + Leaflet）"""
    html = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>瓦片地图服务 - 北京地区</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        * { margin: 0; padding: 0; }
        body, html, #map { width: 100%; height: 100%; font-family: Arial, sans-serif; }
        #info { position: absolute; top: 10px; right: 10px; background: white; padding: 15px;
                border-radius: 5px; box-shadow: 0 0 15px rgba(0,0,0,0.2); z-index: 400;
                font-size: 13px; }
        #info h3 { margin-bottom: 10px; }
        .info-row { margin: 5px 0; }
        .label { font-weight: bold; color: #333; }
    </style>
</head>
<body>
    <div id="map"></div>
    <div id="info">
        <h3>瓦片地图服务</h3>
        <div class="info-row">
            <span class="label">缩放级别 (z):</span> <span id="zoom">7</span>
        </div>
        <div class="info-row">
            <span class="label">瓦片坐标:</span> <span id="tile">-</span>
        </div>
        <div class="info-row">
            <span class="label">中心坐标:</span> <span id="center">-</span>
        </div>
        <div class="info-row">
            <span class="label">覆盖范围:</span> Beijing (z7-12)
        </div>
    </div>

    <script>
        // 初始化地图（中心：北京，初始缩放级别改为 8）
        const map = L.map('map').setView([40.0, 116.4], 8);

        // 添加自定义瓦片图层（从本地服务器加载）
        const tileLayer = L.tileLayer('/tiles/{z}/{x}/{y}.png', {
            attribution: '本地瓦片服务 | 数据源：GeoVisEarth',
            minZoom: 7,
            maxZoom: 12,
            tms: false,
            errorTileUrl: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=='
        }).addTo(map);

        // 实时更新信息面板
        map.on('zoomend', function() {
            document.getElementById('zoom').textContent = map.getZoom();
        });

        map.on('mousemove', function(e) {
            const z = map.getZoom();
            const x = Math.floor((e.latlng.lng + 180) / 360 * Math.pow(2, z));
            const y = Math.floor((1 - Math.log(Math.tan(Math.PI * e.latlng.lat / 180) + 1 / Math.cos(Math.PI * e.latlng.lat / 180)) / Math.PI) / 2 * Math.pow(2, z));
            
            document.getElementById('tile').textContent = `(${x}, ${y}, ${z})`;
            document.getElementById('center').textContent = 
                `${e.latlng.lat.toFixed(4)}°, ${e.latlng.lng.toFixed(4)}°`;
        });

        // 页面加载时的初始提示
        console.log('✓ 地图已加载，当前显示 zoom=8');
        console.log('如果看不到地图，请检查 /tiles/ 接口是否返回有效的瓦片');
    </script>
</body>
</html>
    '''
    return render_template_string(html)


@app.route('/tiles/<int:z>/<int:x>/<int:y>.png')
def get_tile(z, x, y):
    """瓦片接口：返回 z/x/y 对应的瓦片"""
    tile_path = find_tile_file(z, x, y)
    
    if tile_path is None:
        logger.debug(f"Tile not found: {z}/{x}/{y}, returning blank placeholder")
        # 返回透明的 256x256 PNG
        from PIL import Image
        import io
        img = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        resp = make_response(send_file(img_io, mimetype='image/png'))
        resp.headers['Cache-Control'] = 'public, max-age=3600'
        return resp
    
    try:
        logger.info(f"Serving tile: {z}/{x}/{y} from {tile_path}")
        
        # 如果是 PNG，直接返回
        if tile_path.suffix.lower() == '.png':
            resp = make_response(send_file(str(tile_path), mimetype='image/png'))
            resp.headers['Cache-Control'] = 'public, max-age=86400'
            return resp
        
        # 如果是 WebP 或其他格式，转换为 PNG 返回
        from PIL import Image
        import io
        with Image.open(str(tile_path)) as img:
            img = img.convert('RGBA')
            img_io = io.BytesIO()
            img.save(img_io, 'PNG')
            img_io.seek(0)
            resp = make_response(send_file(img_io, mimetype='image/png'))
            resp.headers['Cache-Control'] = 'public, max-age=86400'
            return resp
            
    except Exception as e:
        logger.error(f"Error reading/converting tile {z}/{x}/{y} ({tile_path}): {e}", exc_info=True)
        # 返回错误占位图（半透明红色）
        from PIL import Image
        import io
        img = Image.new('RGBA', (256, 256), (255, 0, 0, 64))
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        resp = make_response(send_file(img_io, mimetype='image/png'))
        resp.headers['Cache-Control'] = 'public, max-age=0'
        return resp


@app.route('/api/tile-stats')
def tile_stats():
    """API：获取瓦片统计信息"""
    stats = {}
    for z_dir in sorted(TILES_DIR.glob('*/')):
        if z_dir.is_dir():
            z = z_dir.name
            count = len(list(z_dir.glob('*/*')))
            stats[z] = count
    return jsonify(stats)


if __name__ == '__main__':
    print("=" * 60)
    print("🌍 瓦片地图服务已启动")
    print("=" * 60)
    print("📍 访问地址：http://localhost:5000")
    print("🗺️  瓦片接口：/tiles/{z}/{x}/{y}.png")
    print("📊 统计接口：/api/tile-stats")
    print("=" * 60)
    print("支持 zoom 范围：7-12（北京地区）")
    print("按 Ctrl+C 停止服务")
    print("=" * 60)
    app.run(debug=False, host='127.0.0.1', port=5000, threaded=True)
