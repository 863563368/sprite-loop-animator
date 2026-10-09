# sprite-loop-animator

**精灵循环动画生成流水线** —— 一张角色参考图，直接变成可投入使用的循环动画素材。

```
角色参考图 ──► 原地循环动画视频 ──► 抽帧 ──► GIF 动图 + 精灵图（sprite sheet）+ 帧序列 PNG
```

适用于像素风 / 手绘角色制作奔跑、待机、攻击等**原地循环**动画素材：人物点位、大小、相机视角全程固定，抽出的帧可直接拼进游戏引擎或表情包。

## 效果

以一张 768×768 像素风角色图（面朝右）为例，默认参数（4 秒、8fps、从第 2 秒开始抽帧）产出：

| 产物 | 说明 |
|---|---|
| 循环动画视频 | 1:1 画幅，人物原地向右奔跑，相机静止 |
| `loop.gif` | 20 帧循环，全局调色板、无抖动，保持像素风干净 |
| `spritesheet.png` | 20 帧横向单行，15360×768 |
| `frames/*.png` | 从第 2 秒起的全部抽帧 PNG，按序号命名 |

## 安装

### 前置要求

- [WorkBuddy](https://www.workbuddy.cn/)（视频生成能力依赖其内置的图生视频服务）
- Python 3.10+
- ffmpeg：三选一，脚本自动发现
  1. 系统已安装 ffmpeg（在 PATH 中）
  2. 设置环境变量 `FFMPEG_PATH` 指向 ffmpeg 可执行文件
  3. 什么都不做，脚本会自动使用 `imageio-ffmpeg` 包附带的 ffmpeg
- Python 依赖：`pip install pillow imageio-ffmpeg`

### 安装到 WorkBuddy

把本仓库克隆（或下载解压）到用户技能目录：

```bash
git clone https://github.com/863563368/sprite-loop-animator.git
# Windows
move sprite-loop-animator %USERPROFILE%\.workbuddy\skills\
# macOS / Linux
mv sprite-loop-animator ~/.workbuddy/skills/
```

重启 WorkBuddy 会话后即可触发。

## 使用

在 WorkBuddy 对话中给出角色参考图 + 一句话描述，例如：

> 参考这张图，帮我生成一段人物向右奔跑的视频，4 秒，人物点位不变、大小不变、相机不变，然后从第 2 秒开始、每秒 8 帧抽帧，输出 GIF 和精灵图。

技能会先确认参数，然后自动走完：视频生成 → 抽帧 → GIF + 精灵图。

### 参数与默认值

| 参数 | 默认值 | 说明 |
|---|---|---|
| 动作与方向 | — | 奔跑 / 待机 / 攻击等，向左或向右 |
| 时长 | 4 秒 | 循环动画建议 3～5 秒 |
| fps | 8 | 抽帧帧率 |
| 起始时间 | 第 2 秒 | 从视频第 2 秒开始抽帧，跳过开头常见的姿态过渡 |
| 精灵图排布 | strip | 横向单行；可选 grid 网格（列数自动或指定） |

### 单独运行处理脚本

`scripts/build_gif_and_spritesheet.py` 是独立的抽帧合成工具，不依赖 WorkBuddy，可对**任何已有的循环动画视频**单独使用：

```bash
python scripts/build_gif_and_spritesheet.py \
  --video run.mp4 --out-dir ./out \
  --fps 8 --start-time 2 --layout strip
```

完整参数见脚本头部注释（`--layout grid --cols 8` 网格排布、`--dither` 抖动、`--no-keep-frames` 用后即删等）。

## 目录结构

```
sprite-loop-animator/
├── SKILL.md                              # 技能主文档（工作流与硬约束）
├── README.md
├── references/
│   └── video-prompting.md                # 循环动画视频提示词构建指南
└── scripts/
    └── build_gif_and_spritesheet.py      # 抽帧 → GIF + 精灵图 一体脚本
```

## 注意事项

- 视频生成环节依赖 WorkBuddy 内置的图生视频服务，需在其环境中使用；处理脚本可独立运行
- 像素风格默认关闭 GIF 抖动并使用全局调色板，避免帧间色彩闪烁
- AI 生成视频的开头常有姿态过渡，默认从第 2 秒开始抽帧；素材不理想时可调整起始时间或重生成
- 人物点位 / 大小 / 相机固定已在生成提示词中硬约束，但动作本身的自然起伏（跑动起伏、头发摆动）不可避免

## License

待添加 —— 开源前请选择并添加 LICENSE 文件（如 MIT）。
