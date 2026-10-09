# 循环动画视频的 Prompt 构建指南

生成"原地循环动画"视频时，提示词的质量直接决定素材能不能用。视频与图片提示词最大的区别是**必须描述运动**；而循环动画素材还多一条铁律：**人物不能位移**。

## 一、四要素（每条 prompt 都要覆盖）

1. **主体在做什么** —— 具体的动作循环，不是"一个人站着"而是"腿部跑动、手臂交替摆动、马尾随动"
2. **镜头怎么动** —— 循环动画素材固定写法：`camera is completely static, no pan, no zoom, no shake`
3. **光线与氛围** —— 一般沿用参考图的既有光线；补充 `lighting unchanged`
4. **结束状态** —— 写 `seamless looping`，让结尾尽量回到接近起始帧的姿态

## 二、原地循环的三条硬约束（缺一条素材就废）

写进每条 prompt，且不可被其他描述稀释：

- `runs/animates in place` —— 动作原地发生
- `body stays at the exact same position and size in the frame, does NOT move forward or translate across the screen` —— 点位与尺寸不变
- `fixed side view, static camera` —— 视角不变

## 三、方向与风格

- **方向**：`facing left` / `facing right`，与参考图朝向一致；用户说"向右跑"就写 facing right
- **像素风专项**：`pixel art style, crisp pixels, consistent character design and colors with the first frame`；背景延续参考图（如 `white background unchanged`）
- **其他画风**：保留参考图的艺术风格描述（如水彩、赛璐璐），加 `consistent style with the first frame`

## 四、常见动作模板（按用户需求替换动作部分）

- 奔跑：`legs cycle through running poses, arms swing alternately, hair and clothes bounce with the motion`
- 待机呼吸：`subtle breathing motion, slight body bob, hair sways gently`
- 攻击挥砍：`wind up, swing weapon across, recover to ready stance`（节奏比循环感更重要）

## 五、反例（不要这样写）

- 只写静态描述（"一个女孩面朝右"）→ 得到几乎不动的视频
- 写了运镜词（`camera follows`、`pan right`）→ 人物或镜头位移，素材无法循环拼接
- 用文字描述参考图而不用参考图本身 → 人物不是同一个，一致性丢失

## 六、参数约定

- **时长**：循环动画取 3～5 秒足够覆盖一个完整动作周期，默认 4 秒
- **画幅**：跟随参考图比例（方形图 → 1:1）
- **首帧锚定**：参考图必须作为视频的 first_frame 传入，这是点位、大小、视角"三不变"的最可靠保障
