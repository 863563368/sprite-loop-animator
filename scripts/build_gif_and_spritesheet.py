#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_gif_and_spritesheet.py
循环动画视频 → 按帧率抽帧 → 背景透明化 → 输出透明背景 GIF 动图 + 精灵图（sprite sheet）

用法:
    python build_gif_and_spritesheet.py --video run.mp4 --out-dir ./out
    python build_gif_and_spritesheet.py --video run.mp4 --out-dir ./out \
        --fps 8 --start-time 2 --layout strip
    python build_gif_and_spritesheet.py --video run.mp4 --out-dir ./out \
        --fps 12 --start-time 1 --layout grid --cols 8 --dither
    python build_gif_and_spritesheet.py --video run.mp4 --out-dir ./out \
        --bg-removal color --bg-color "#00FF00"   # 纯色背景快速抠除

参数:
    --video          (必填) 输入视频路径（mp4 等 ffmpeg 支持的格式）
    --out-dir        (必填) 输出目录；抽帧 PNG（已透明化）保存在其下 frames/ 子目录
    --fps            抽帧帧率，默认 8
    --start-time     抽帧起始时间（秒），默认 2；即从视频第 2 秒处开始按帧率抽取
    --layout         精灵图排布：strip（横向单行，默认）或 grid（网格）
    --cols           网格列数，仅 grid 排布生效；0 表示自动（按帧数开方）
    --gif-name       GIF 文件名，默认 loop.gif
    --sheet-name     精灵图文件名，默认 spritesheet.png
    --bg-removal     背景透明化方式：
                       rembg  AI 抠图，适用于任意背景（默认；首次运行会下载模型）
                       color  纯色背景抠除（配合 --bg-color / --bg-tol，无重依赖）
                       none   不做透明化，保持原样
    --bg-color       color 模式的背景色（#RRGGBB）；缺省时自动取四角像素中位数
    --bg-tol         color 模式颜色容差 0~255，默认 30
    --rembg-model    rembg 模式使用的模型，默认 u2net（可选 isnet-general-use 等）
    --alpha-thresh   GIF 透明阈值 0~255，alpha 低于该值视为全透明，默认 128
    --dither         GIF 量化时启用抖动（像素风建议关闭，默认关闭）
    --no-keep-frames 抽帧 PNG 用完即删（默认保留，保留的是已透明化的 RGBA 帧）

依赖: Pillow；ffmpeg（自动发现：环境变量 FFMPEG_PATH → 系统 PATH →
      imageio-ffmpeg 包。都没有时安装 imageio-ffmpeg: pip install imageio-ffmpeg）
      rembg 模式额外依赖: pip install rembg（首次运行自动下载模型）
      color 模式额外依赖: numpy
"""

import argparse
import math
import os
import shutil
import subprocess
import sys
from collections import deque
from pathlib import Path

from PIL import Image


def safe_print(message):
    """Windows 控制台安全打印。"""
    try:
        print(message)
    except UnicodeEncodeError:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(message)


def find_ffmpeg():
    """按优先级发现可用的 ffmpeg 可执行文件。"""
    env_path = os.environ.get("FFMPEG_PATH")
    if env_path and Path(env_path).is_file():
        return str(env_path)
    which = shutil.which("ffmpeg")
    if which:
        return which
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return None


def extract_frames(ffmpeg, video, frames_dir, fps, start_time):
    """用 ffmpeg 从起始时间处开始、按指定帧率抽出帧 PNG。"""
    pattern = str(frames_dir / "f_%04d.png")
    cmd = [
        ffmpeg, "-y", "-loglevel", "error",
        "-ss", str(start_time),
        "-i", str(video),
        "-vf", f"fps={fps}",
        pattern,
    ]
    subprocess.run(cmd, check=True)


# ---------------------------------------------------------------------------
# 背景透明化
# ---------------------------------------------------------------------------

def remove_bg_rembg(frames, model_name):
    """用 rembg AI 抠图，适用于任意背景。"""
    try:
        from rembg import new_session, remove
    except ImportError:
        safe_print("错误: 未安装 rembg。请执行: pip install rembg")
        sys.exit(1)
    session = new_session(model_name)
    return [remove(im.convert("RGB"), session=session) for im in frames]


def remove_bg_color(frames, bg_color, tol):
    """纯色背景抠除：从图像边缘 flood-fill 与背景色相近的连通区域。"""
    try:
        import numpy as np
    except ImportError:
        safe_print("错误: color 模式需要 numpy。请执行: pip install numpy")
        sys.exit(1)

    results = []
    for idx, im in enumerate(frames):
        rgba = im.convert("RGBA")
        arr = np.array(rgba)
        h, w = arr.shape[:2]

        if bg_color is None:
            # 自动取四角像素中位数作为背景色
            corners = [
                arr[0, 0, :3], arr[0, -1, :3],
                arr[-1, 0, :3], arr[-1, -1, :3],
            ]
            bg = tuple(int(v) for v in np.median(np.array(corners), axis=0))
        else:
            bg = bg_color
        bg_arr = np.array(bg, dtype=np.int16)

        # 与背景色的距离（RGB 欧氏距离近似：逐通道差绝对值之和）
        dist = np.abs(arr[:, :, :3].astype(np.int16) - bg_arr).sum(axis=2)
        near = dist <= tol * 3  # 容差按通道放宽到三倍，允许整体更宽松

        # BFS：从所有边缘上的"近背景色"像素向内扩散
        visited = np.zeros((h, w), dtype=bool)
        dq = deque()
        for x in range(w):
            for y in (0, h - 1):
                if near[y, x] and not visited[y, x]:
                    visited[y, x] = True
                    dq.append((y, x))
        for y in range(h):
            for x in (0, w - 1):
                if near[y, x] and not visited[y, x]:
                    visited[y, x] = True
                    dq.append((y, x))
        while dq:
            y, x = dq.popleft()
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= ny < h and 0 <= nx < w and near[ny, nx] and not visited[ny, nx]:
                    visited[ny, nx] = True
                    dq.append((ny, nx))

        arr[visited, 3] = 0  # 背景连通区域置为全透明
        results.append(Image.fromarray(arr, "RGBA"))
        if idx == 0:
            ratio = visited.sum() / (h * w) * 100
            safe_print(f"      背景色 {bg}, 第 1 帧抠除面积占比 {ratio:.0f}%")
    return results


# ---------------------------------------------------------------------------
# 合成
# ---------------------------------------------------------------------------

def build_gif(frames, out_path, fps, dither, alpha_thresh):
    """合成透明背景 GIF：全局调色板（取自首帧）+ 索引 255 保留为透明色。

    GIF 仅支持 1 位透明，因此 alpha 低于 alpha_thresh 的像素视为全透明；
    半透明像素按不透明处理（保留原色）。
    """
    first_rgb = frames[0].convert("RGB")
    pal = first_rgb.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    dither_mode = Image.Dither.FLOYDSTEINBERG if dither else Image.Dither.NONE
    pframes = []
    for im in frames:
        p = im.convert("RGB").quantize(palette=pal, dither=dither_mode)
        alpha = im.getchannel("A")
        # mask=255 处将被写成透明索引 255
        mask = alpha.point(lambda a: 255 if a < alpha_thresh else 0)
        p.paste(255, mask)
        p.info["transparency"] = 255
        pframes.append(p)
    duration = max(20, round(1000.0 / fps))
    pframes[0].save(
        out_path,
        save_all=True,
        append_images=pframes[1:],
        duration=duration,
        loop=0,
        transparency=255,
        disposal=2,  # 每帧播完恢复透明背景，避免上一帧残影
        optimize=True,
    )
    return duration


def build_sheet_strip(frames, out_path):
    """横向单行精灵图。"""
    w, h = frames[0].size
    sheet = Image.new("RGBA", (w * len(frames), h), (0, 0, 0, 0))
    for i, im in enumerate(frames):
        sheet.paste(im, (i * w, 0), im)
    sheet.save(out_path, optimize=True)
    return sheet.size


def build_sheet_grid(frames, out_path, cols):
    """网格精灵图；末尾不足一格的位置保持透明。"""
    n = len(frames)
    cols = cols if cols and cols > 0 else max(1, math.ceil(math.sqrt(n)))
    rows = math.ceil(n / cols)
    w, h = frames[0].size
    sheet = Image.new("RGBA", (w * cols, h * rows), (0, 0, 0, 0))
    for i, im in enumerate(frames):
        r, c = divmod(i, cols)
        sheet.paste(im, (c * w, r * h), im)
    sheet.save(out_path, optimize=True)
    return sheet.size


def parse_color(text):
    """解析 #RRGGBB 颜色，返回 (r, g, b)。"""
    t = text.strip().lstrip("#")
    if len(t) != 6:
        raise argparse.ArgumentTypeError(f"颜色格式应为 #RRGGBB: {text}")
    try:
        return tuple(int(t[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        raise argparse.ArgumentTypeError(f"颜色格式应为 #RRGGBB: {text}")


def main():
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="循环动画视频抽帧 → 背景透明化 → GIF + 精灵图")
    parser.add_argument("--video", required=True, help="输入视频路径")
    parser.add_argument("--out-dir", required=True, help="输出目录")
    parser.add_argument("--fps", type=float, default=8, help="抽帧帧率（默认 8）")
    parser.add_argument("--start-time", type=float, default=2.0,
                        help="抽帧起始时间（秒，默认 2，即从视频第 2 秒开始抽）")
    parser.add_argument("--layout", choices=["strip", "grid"], default="strip",
                        help="精灵图排布（默认 strip 横向单行）")
    parser.add_argument("--cols", type=int, default=0, help="网格列数，0 为自动")
    parser.add_argument("--gif-name", default="loop.gif", help="GIF 文件名（默认 loop.gif）")
    parser.add_argument("--sheet-name", default="spritesheet.png", help="精灵图文件名（默认 spritesheet.png）")
    parser.add_argument("--bg-removal", choices=["rembg", "color", "none"], default="rembg",
                        help="背景透明化方式（默认 rembg AI 抠图；纯色背景可用 color；none 关闭）")
    parser.add_argument("--bg-color", type=parse_color, default=None,
                        help="color 模式背景色 #RRGGBB；缺省自动取四角中位数")
    parser.add_argument("--bg-tol", type=int, default=30, help="color 模式容差 0~255（默认 30）")
    parser.add_argument("--rembg-model", default="u2net",
                        help="rembg 模型（默认 u2net，可选 isnet-general-use 等）")
    parser.add_argument("--alpha-thresh", type=int, default=128,
                        help="GIF 透明阈值 0~255，低于该值视为全透明（默认 128）")
    parser.add_argument("--dither", action="store_true", help="GIF 启用抖动（像素风不建议）")
    parser.add_argument("--no-keep-frames", action="store_true", help="不保留抽帧 PNG")
    args = parser.parse_args()

    video = Path(args.video).resolve()
    if not video.is_file():
        safe_print(f"错误: 视频不存在: {video}")
        sys.exit(1)

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        safe_print("错误: 未找到 ffmpeg。请安装后重试: pip install imageio-ffmpeg")
        sys.exit(1)

    out_dir = Path(args.out_dir).resolve()
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    # 清理上次运行遗留的帧，避免陈旧帧混入本次结果
    for old in frames_dir.glob("f_*.png"):
        old.unlink()

    # 1. 抽帧
    safe_print(f"[1/4] 抽帧中: fps={args.fps}, 从第 {args.start_time} 秒开始")
    try:
        extract_frames(ffmpeg, video, frames_dir, args.fps, args.start_time)
    except subprocess.CalledProcessError:
        safe_print("错误: ffmpeg 抽帧失败，请检查视频文件是否可读、格式是否受支持。")
        sys.exit(1)

    files = sorted(p.name for p in frames_dir.glob("f_*.png"))
    if not files:
        safe_print(f"错误: 从第 {args.start_time} 秒起未抽出任何帧，视频可能比起始时间短。")
        sys.exit(1)

    frames = [Image.open(frames_dir / f).convert("RGB") for f in files]
    w, h = frames[0].size
    safe_print(f"      从第 {args.start_time} 秒开始抽出 {len(frames)} 帧，单帧 {w}x{h}")

    # 2. 背景透明化（抽帧之后、合成之前）
    if args.bg_removal == "rembg":
        safe_print(f"[2/4] 背景透明化中: rembg AI 抠图（模型 {args.rembg_model}，首次运行需下载模型）")
        frames = remove_bg_rembg(frames, args.rembg_model)
        safe_print("      rembg 抠图完成")
    elif args.bg_removal == "color":
        safe_print(f"[2/4] 背景透明化中: 纯色抠除（容差 {args.bg_tol}）")
        frames = remove_bg_color(frames, args.bg_color, args.bg_tol)
        safe_print("      纯色抠除完成")
    else:
        safe_print("[2/4] 跳过背景透明化（--bg-removal none）")

    # 把已透明化的帧写回 frames/，保证保留的帧序列就是最终成品
    for f_path, im in zip(frames_dir.glob("f_*.png"), frames):
        im.save(f_path)

    # 3. GIF（带透明背景）
    gif_path = out_dir / args.gif_name
    duration = build_gif(frames, gif_path, args.fps, args.dither, args.alpha_thresh)
    safe_print(f"[3/4] GIF 完成: {gif_path} "
               f"({len(frames)} 帧 x {duration}ms, 透明背景, {os.path.getsize(gif_path) / 1024:.0f} KB)")

    # 4. 精灵图（RGBA 透明背景）
    sheet_path = out_dir / args.sheet_name
    if args.layout == "grid":
        size = build_sheet_grid(frames, sheet_path, args.cols)
    else:
        size = build_sheet_strip(frames, sheet_path)
    safe_print(f"[4/4] 精灵图完成: {sheet_path} ({args.layout} 排布, RGBA 透明, {size[0]}x{size[1]})")

    if args.no_keep_frames:
        shutil.rmtree(frames_dir, ignore_errors=True)
        safe_print("已按参数删除抽帧 PNG。")
    else:
        safe_print(f"抽帧 PNG（已透明化）保留在: {frames_dir}")

    safe_print("\n=== 摘要 ===")
    safe_print(f"使用帧数: {len(frames)}")
    safe_print(f"背景透明化: {args.bg_removal}"
               + (f" (容差 {args.bg_tol})" if args.bg_removal == "color" else "")
               + (f" (模型 {args.rembg_model})" if args.bg_removal == "rembg" else ""))
    safe_print(f"GIF: {gif_path} (透明背景, 帧间隔 {duration}ms)")
    safe_print(f"精灵图: {sheet_path} ({args.layout}, RGBA 透明, {size[0]}x{size[1]})")
    safe_print(f"帧目录: {frames_dir if not args.no_keep_frames else '(已删除)'}")


if __name__ == "__main__":
    main()
