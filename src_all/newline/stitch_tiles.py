#!/usr/bin/env python3
"""
stitch_tiles.py

功能：
- 命令行模式：保持原有用法（--zoom --bbox 等）
- 配置文件模式：通过 --config config.json 读取 jobs 并批量拼接

与 tile_crawler 共用 config.json 的 jobs 字段。
"""

from pathlib import Path
import argparse
import json
import math
from PIL import Image
from tqdm import tqdm
import sys

TILE_SIZE = 256
PREFERRED_EXTS = ["png", "webp", "jpg", "jpeg"]


def latlon_to_tile_xy(lat, lon, z):
    """返回整数 x,y（Slippy map）"""
    lat_rad = math.radians(lat)
    n = 2.0 ** z
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n
    return int(x), int(y)


def bbox_to_tile_range(min_lon, min_lat, max_lon, max_lat, z):
    x1, y2 = latlon_to_tile_xy(min_lat, min_lon, z)
    x2, y1 = latlon_to_tile_xy(max_lat, max_lon, z)
    return min(x1, x2), max(x1, x2), min(y1, y2), max(y1, y2)


def find_tile_file(input_dir: Path, z: int, x: int, y: int):
    base = input_dir / str(z) / str(x) / str(y)
    for ext in PREFERRED_EXTS:
        p = base.with_suffix('.' + ext)
        if p.exists():
            return p
    for p in base.parent.glob(base.name + '.*'):
        if p.is_file():
            return p
    return None


def stitch(z, x_min, x_max, y_min, y_max, input_dir: Path, output: Path, tile_size=TILE_SIZE, output_format='PNG'):
    cols = x_max - x_min + 1
    rows = y_max - y_min + 1
    width, height = cols * tile_size, rows * tile_size
    out_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))

    missing = 0
    total = cols * rows

    for x in tqdm(range(x_min, x_max + 1), desc=f'拼接 {output.stem}'):
        for y in range(y_min, y_max + 1):
            tile_path = find_tile_file(input_dir, z, x, y)
            if not tile_path:
                missing += 1
                continue
            try:
                with Image.open(tile_path) as im:
                    im = im.convert('RGBA')
                    out_img.paste(im, ((x - x_min) * tile_size, (y - y_min) * tile_size), im)
            except Exception as e:
                print(f"警告: 读取失败 {tile_path}: {e}", file=sys.stderr)
                missing += 1

    output.parent.mkdir(parents=True, exist_ok=True)
    if not output.suffix.lower():
        output = output.with_suffix('.png')
    out_img.save(output, format=output_format)
    return {'z': z, 'x_min': x_min, 'x_max': x_max, 'y_min': y_min, 'y_max': y_max,
            'cols': cols, 'rows': rows, 'total': total, 'missing': missing, 'output': str(output)}


def parse_range(s: str):
    parts = s.split(',')
    if len(parts) != 2:
        raise argparse.ArgumentTypeError('需为两个整数，如 100,200')
    return int(parts[0]), int(parts[1])


def run_from_config(config_path: str):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # 获取默认值
    defaults = config.get("defaults", {})
    input_dir_default = defaults.get("outdir", "out")
    tile_size_default = defaults.get("tile_size", TILE_SIZE)
    format_default = defaults.get("format", "PNG")

    jobs = config.get("jobs", [])
    if not jobs:
        print("❌ config.json 中未找到 'jobs' 字段", file=sys.stderr)
        sys.exit(1)

    for job in jobs:
        name = job.get("name", "unnamed")
        zoom = job.get("zoom")
        bbox = job.get("bbox")  # "min_lon,min_lat,max_lon,max_lat"
        outdir = Path(job.get("outdir", input_dir_default))
        output = Path(job.get("output", f"maps/{name}.png"))
        tile_size = job.get("tile_size", tile_size_default)
        fmt = job.get("format", format_default)

        if zoom is None or bbox is None:
            print(f"⚠️ 跳过任务 '{name}'：缺少 zoom 或 bbox", file=sys.stderr)
            continue

        try:
            min_lon, min_lat, max_lon, max_lat = map(float, bbox.split(','))
        except Exception as e:
            print(f"❌ 任务 '{name}' 的 bbox 格式错误: {e}", file=sys.stderr)
            continue

        x_min, x_max, y_min, y_max = bbox_to_tile_range(min_lon, min_lat, max_lon, max_lat, zoom)

        print(f"\n🧩 开始拼接任务: {name}")
        result = stitch(zoom, x_min, x_max, y_min, y_max, outdir, output, tile_size, fmt)
        print(f"✅ 完成: {result['output']} | 缺失: {result['missing']}/{result['total']}")


def main():
    parser = argparse.ArgumentParser(description='拼接瓦片为大图（支持 config.json）')
    parser.add_argument('--config', help='使用 config.json 批量拼接（与爬虫共用）')
    
    # 以下为兼容旧命令行模式
    parser.add_argument('--zoom', '-z', type=int, help='缩放级别')
    parser.add_argument('--bbox', help='min_lon,min_lat,max_lon,max_lat')
    parser.add_argument('--xrange', help='x_min,x_max')
    parser.add_argument('--yrange', help='y_min,y_max')
    parser.add_argument('--input-dir', default='out', help='瓦片根目录')
    parser.add_argument('--output', help='输出文件路径')
    parser.add_argument('--tile-size', type=int, default=TILE_SIZE)
    parser.add_argument('--format', default='PNG')

    args = parser.parse_args()

    if args.config:
        run_from_config(args.config)
    else:
        # 旧命令行模式
        if not args.zoom or not args.output:
            parser.error("在非 --config 模式下，--zoom 和 --output 是必需的")
        if not (args.bbox or (args.xrange and args.yrange)):
            parser.error("需要提供 --bbox 或 (--xrange 和 --yrange)")

        input_dir = Path(args.input_dir)
        z = args.zoom

        if args.bbox:
            parts = args.bbox.split(',')
            if len(parts) != 4:
                parser.error('--bbox 需要四个数字')
            min_lon, min_lat, max_lon, max_lat = map(float, parts)
            x_min, x_max, y_min, y_max = bbox_to_tile_range(min_lon, min_lat, max_lon, max_lat, z)
        else:
            x_min, x_max = parse_range(args.xrange)
            y_min, y_max = parse_range(args.yrange)

        result = stitch(z, x_min, x_max, y_min, y_max, input_dir, Path(args.output),
                        tile_size=args.tile_size, output_format=args.format)
        print('拼接完成:')
        print(f" - zoom: {result['z']}")
        print(f" - x: {result['x_min']}..{result['x_max']} ({result['cols']} cols)")
        print(f" - y: {result['y_min']}..{result['y_max']} ({result['rows']} rows)")
        print(f" - tiles 总计: {result['total']}, 缺失: {result['missing']}")
        print(f" - 输出: {result['output']}")


if __name__ == '__main__':
    main()