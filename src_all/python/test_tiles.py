#!/usr/bin/env python3
from pathlib import Path

TILES_DIR = Path('out')
PREFERRED_EXTS = ['png', 'webp', 'jpg', 'jpeg']

def find_tile_file(z, x, y):
    tile_dir = TILES_DIR / str(z) / str(x)
    tile_base = tile_dir / str(y)
    
    for ext in PREFERRED_EXTS:
        tile_path = tile_base.with_suffix('.' + ext)
        if tile_path.exists():
            return tile_path
    
    if tile_dir.exists():
        for f in tile_dir.glob(f'{y}.*'):
            if f.is_file():
                return f
    return None

# 测试 zoom=8 的几个瓦片
print("Testing zoom=8 tiles:")
for x in [210, 211]:
    for y in range(95, 98):
        result = find_tile_file(8, x, y)
        status = "✓" if result else "✗"
        print(f"  z=8, x={x}, y={y}: {status}")

# 列出 out/ 目录结构
print("\nDirectory structure in out/:")
for z_dir in sorted(TILES_DIR.glob('*')):
    if z_dir.is_dir():
        file_count = len(list(z_dir.glob('*/*')))
        print(f"  out/{z_dir.name}/: {file_count} tiles")
