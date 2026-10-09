#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_gif_and_spritesheet.py
循环动画视频 → 按帧率抽帧 → 输出 GIF 动图 + 精灵图（sprite sheet）

用法:
    python build_gif_and_spritesheet.py --video run.mp4 --out-dir ./out
    python build_gif_and_spritesheet.py --video run.mp4 --out-dir ./out \
        --fps 8 --start-time 2 --layout strip
    python build_gif_and_spritesheet.py --video run.mp4 --out-dir ./out \
        --fps 12 --start-time 1 --layout grid --cols 8 --dither

参数:
    --video          (必填) 输入视频路径（mp4 等 ffmpeg 支持的格式）
    --out-dir        (必填) 输出目录；帧 PNG 保存在其下 frames/ 子目录
    --fps            抽帧帧率，默认 8
    --start-time     抽帧起始时间（秒），默认 2；即从视频第 2 秒处开始按帧率抽取
    --layout         精灵图排布：strip（横向单行，默认）或 grid（网格）
    --cols           网格列数，仅 grid 排布生效；0 表示自动（按帧数开方）
    --gif-name       GIF 文件名，默认 loop.gif
    --sheet-name     精灵图文件名，默认 spritesheet.png
    --dither         GIF 量化时启用抖动（像素风建议关闭，默认关闭）
    --no-keep-frames 抽帧 PNG 用完即删（默认保留）

依赖: Pillow；ffmpeg（自动发现：环境变量 FFMPEG_PATH → 系统 PATH →
      imageio-ffmpeg 包。都没有时安装 imageio-ffmpeg: pip install imageio-ffmpeg）
"""

import argparse
import math
import os
import shutil
import subprocess
import sys
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


def build_gif(frames, out_path, fps, dither):
    """合成 GIF：全局调色板（取自首帧）避免帧间调色板闪烁。"""
    pal = frames[0].quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    dither_mode = Image.Dither.FLOYDSTEINBERG if dither else Image.Dither.NONE
    pframes = [im.quantize(palette=pal, dither=dither_mode) for im in frames]
    duration = max(20, round(1000.0 / fps))
    pframes[0].save(
        out_path,
        save_all=True,
        append_images=pframes[1:],
        duration=duration,
        loop=0,
        optimize=True,
    )
    return duration


def build_sheet_strip(frames, out_path):
    """横向单行精灵图。"""
    w, h = frames[0].size
    sheet = Image.new("RGBA", (w * len(frames), h), (0, 0, 0, 0))
    for i, im in enumerate(frames):
        sheet.paste(im, (i * w, 0))
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
        sheet.paste(im, (c * w, r * h))
    sheet.save(out_path, optimize=True)
    return sheet.size


def main():
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="循环动画视频抽帧 → GIF + 精灵图")
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
    safe_print(f"[1/3] 抽帧中: fps={args.fps}, 从第 {args.start_time} 秒开始")
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

    # 2. GIF
    gif_path = out_dir / args.gif_name
    duration = build_gif(frames, gif_path, args.fps, args.dither)
    safe_print(f"[2/3] GIF 完成: {gif_path} "
               f"({len(frames)} 帧 x {duration}ms, {os.path.getsize(gif_path) / 1024:.0f} KB)")

    # 3. 精灵图
    sheet_path = out_dir / args.sheet_name
    if args.layout == "grid":
        size = build_sheet_grid(frames, sheet_path, args.cols)
    else:
        size = build_sheet_strip(frames, sheet_path)
    safe_print(f"[3/3] 精灵图完成: {sheet_path} ({args.layout} 排布, {size[0]}x{size[1]})")

    if args.no_keep_frames:
        shutil.rmtree(frames_dir, ignore_errors=True)
        safe_print("已按参数删除抽帧 PNG。")
    else:
        safe_print(f"抽帧 PNG 保留在: {frames_dir}")

    safe_print("\n=== 摘要 ===")
    safe_print(f"使用帧数: {len(frames)}")
    safe_print(f"GIF: {gif_path}")
    safe_print(f"精灵图: {sheet_path} ({args.layout}, {size[0]}x{size[1]})")
    safe_print(f"帧目录: {frames_dir if not args.no_keep_frames else '(已删除)'}")


if __name__ == "__main__":
    main()
