#!/usr/bin/env python3
"""
stitch_tiles.py

将磁盘上的切片按照 z/x/y 网格拼接成一张大图。
支持输入方式：
 - 指定 zoom 和 x/y 范围（--xrange --yrange）
 - 指定 zoom 和 bbox（--bbox）来计算范围

输出为 PNG（默认）或指定格式。会查找 `input_dir/{z}/{x}/{y}.{ext}`，优先使用 png, webp, jpg。

用法示例：
python -m src.stitch_tiles --zoom 8 --xrange 210,211 --yrange 95,97 --input-dir out --output out/beijing_z8.png

依赖：Pillow, tqdm
"""
from pathlib import Path
import argparse
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
    x_min = min(x1, x2)
    x_max = max(x1, x2)
    y_min = min(y1, y2)
    y_max = max(y1, y2)
    return x_min, x_max, y_min, y_max


def find_tile_file(input_dir: Path, z: int, x: int, y: int):
    base = input_dir / str(z) / str(x) / str(y)
    for ext in PREFERRED_EXTS:
        p = base.with_suffix('.' + ext)
        if p.exists():
            return p
    # fallback: glob any file that startswith the path
    for p in base.parent.glob(base.name + '.*'):
        if p.is_file():
            return p
    return None


def stitch(z, x_min, x_max, y_min, y_max, input_dir: Path, output: Path, tile_size=TILE_SIZE, output_format='PNG'):
    cols = x_max - x_min + 1
    rows = y_max - y_min + 1
    width = cols * tile_size
    height = rows * tile_size

    out_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))

    missing = 0
    total = cols * rows

    for x in tqdm(range(x_min, x_max + 1), desc='cols'):
        for y in range(y_min, y_max + 1):
            tile_path = find_tile_file(input_dir, z, x, y)
            if tile_path is None:
                missing += 1
                continue
            try:
                with Image.open(tile_path) as im:
                    im = im.convert('RGBA')
                    px = (x - x_min) * tile_size
                    py = (y - y_min) * tile_size
                    out_img.paste(im, (px, py), im)
            except Exception as e:
                print(f"警告: 读取或粘贴切片失败 {tile_path}: {e}", file=sys.stderr)
                missing += 1

    output.parent.mkdir(parents=True, exist_ok=True)
    # 若输出格式为 PNG，但路径没有扩展名，确保扩展为 .png
    out_ext = output.suffix.lower()
    if not out_ext:
        output = output.with_suffix('.png')

    out_img.save(output, format=output_format)
    return {
        'z': z,
        'x_min': x_min,
        'x_max': x_max,
        'y_min': y_min,
        'y_max': y_max,
        'cols': cols,
        'rows': rows,
        'total': total,
        'missing': missing,
        'output': str(output)
    }


def parse_range(s: str):
    parts = s.split(',')
    if len(parts) != 2:
        raise argparse.ArgumentTypeError('range must be two integers separated by comma')
    return int(parts[0]), int(parts[1])


def main():
    p = argparse.ArgumentParser(description='拼接瓦片为一张大图')
    p.add_argument('--zoom', '-z', type=int, required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--bbox', help='min_lon,min_lat,max_lon,max_lat')
    g.add_argument('--xrange', help='x_min,x_max')
    p.add_argument('--yrange', help='y_min,y_max (required if --xrange set)')
    p.add_argument('--input-dir', default='out', help='切片根目录 (默认: out)')
    p.add_argument('--output', required=True, help='输出文件路径 (png 推荐)')
    p.add_argument('--tile-size', type=int, default=256)
    p.add_argument('--format', default='PNG', help='输出格式，默认 PNG')

    args = p.parse_args()

    input_dir = Path(args.input_dir)
    z = args.zoom

    if args.bbox:
        parts = args.bbox.split(',')
        if len(parts) != 4:
            p.error('--bbox 需要四个逗号分隔的数字')
        min_lon, min_lat, max_lon, max_lat = map(float, parts)
        x_min, x_max, y_min, y_max = bbox_to_tile_range(min_lon, min_lat, max_lon, max_lat, z)
    else:
        if not args.yrange:
            p.error('--yrange 是必须的当使用 --xrange 时')
        x_min, x_max = parse_range(args.xrange)
        y_min, y_max = parse_range(args.yrange)

    out = stitch(z, x_min, x_max, y_min, y_max, input_dir, Path(args.output), tile_size=args.tile_size, output_format=args.format)

    print('拼接完成:')
    print(f" - zoom: {out['z']}")
    print(f" - x: {out['x_min']}..{out['x_max']} ({out['cols']} cols)")
    print(f" - y: {out['y_min']}..{out['y_max']} ({out['rows']} rows)")
    print(f" - tiles 总计: {out['total']}, 缺失: {out['missing']}")
    print(f" - 输出: {out['output']}")


if __name__ == '__main__':
    main()
