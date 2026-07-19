"""
matting.py — AI 坐标转掩膜抠图 Pipeline

流程：
  AI 返回归一化 [0,1] 轮廓点 → 点预处理（去重尾/去离群，保持原顺序）
  → Centripetal Catmull-Rom 样条插值（α=0.5，弦长参数化）
  → 4× 超分 + 抗锯齿 + 羽化 → RGBA 输出

注意：API 模型已按提示词要求返回顺时针点序，预处理不能重排角度！
      质心角度排序会破坏凹形（如鸟翅）的正确相邻关系。

依赖：Pillow（无 numpy / cv2 / scipy）
"""

import math
from typing import Optional
from PIL import Image, ImageDraw, ImageFilter, ImageChops


# ═══════════════════════════════════════════════════════════════
#  第 1 步：点预处理
# ═══════════════════════════════════════════════════════════════

def _validate_and_sort(points: list) -> list:
    """
    输入归一化 [0,1] 坐标，保持原顺序，做去重尾和去离群。

    ⚠️ 不按角度排序！API 返回的就是正确顺时针顺序。
       角度排序会破坏凹形轮廓（如鸟翅）的相邻关系。

    步骤：
      1. 去尾重复（首尾距离 < 1e-6 则移除尾部）
      2. 离群点剔除（距相邻两点平均距离 > 3×中位距则丢弃）
      3. 保留首尾两点不动
      4. 若剩余 < 10 点则报错
    """
    pts = [(float(x), float(y)) for x, y in points]
    if len(pts) < 10:
        raise ValueError(f"轮廓点太少（{len(pts)} 个），至少需要 10 个")

    # ── 1a. 去尾重复 ──────────────────────────────────────────
    def _dist2(a, b):
        return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2

    while len(pts) >= 2 and _dist2(pts[0], pts[-1]) < 1e-12:
        pts.pop()

    if len(pts) < 10:
        raise ValueError("去除重复点后轮廓点数不足 10 个")

    # ── 1b. 离群点剔除（保持原序） ─────────────────────────────
    n = len(pts)
    adj_dists = []
    for i in range(n):
        d = (math.sqrt(_dist2(pts[i], pts[(i - 1) % n])) +
             math.sqrt(_dist2(pts[i], pts[(i + 1) % n]))) / 2.0
        adj_dists.append(d)

    adj_dists_sorted = sorted(adj_dists)
    median_dist = adj_dists_sorted[len(adj_dists_sorted) // 2]
    threshold = 3.0 * median_dist if median_dist > 0 else float("inf")

    keep = [True] * n
    keep[0] = keep[-1] = True  # 保留端点
    for i in range(1, n - 1):
        if adj_dists[i] > threshold:
            keep[i] = False

    cleaned = [p for i, p in enumerate(pts) if keep[i]]
    if len(cleaned) < 10:
        raise ValueError("剔除离群点后轮廓点数不足 10 个")

    return cleaned


# ═══════════════════════════════════════════════════════════════
#  第 2 步：自适应点数
# ═══════════════════════════════════════════════════════════════

def _adaptive_point_count(points: list, override: Optional[int] = None) -> int:
    """
    根据归一化坐标下的轮廓周长自动推算插值点数。

    Rules（归一化尺度 [0,1]）：
      - 周长 < 0.5 → 200 点
      - 周长 < 2.0 → 400 点
      - 周长 ≥ 2.0 → 600 点

    override 不为 None 时直接返回该值。
    """
    if override is not None and override > 0:
        return override

    perimeter = 0.0
    n = len(points)
    for i in range(n):
        j = (i + 1) % n
        perimeter += math.sqrt(
            (points[j][0] - points[i][0]) ** 2 +
            (points[j][1] - points[i][1]) ** 2
        )

    if perimeter < 0.5:
        return 200
    elif perimeter < 2.0:
        return 400
    else:
        return 600


# ═══════════════════════════════════════════════════════════════
#  第 3 步：Centripetal Catmull-Rom 样条（α=0.5）
# ═══════════════════════════════════════════════════════════════

def _catmull_rom_centripetal(points: list, num_output: int) -> list:
    """
    Centripetal Catmull-Rom 样条插值（α=0.5，弦长参数化）。

    闭合曲线：插值前将最后 2 个点 + 前 2 个点绕回接到序列首尾。

    Args:
        points: 预处理后的 [[x,y], ...] 归一化 [0,1] 坐标
        num_output: 目标插值点数

    Returns:
        插值后的点列表（已去重）
    """
    n = len(points)
    if n < 4:
        return points
    if num_output < 4:
        return points

    # ── 3a. 闭合延展 ────────────────────────────────────────
    # 最后 2 点接到前面，前 2 点接到后面
    # [P_{n-2}, P_{n-1}, P_0, P_1, ..., P_{n-1}, P_0, P_1]
    ext = points[-2:] + points + points[:2]
    m = len(ext)  # = n + 4

    # ── 3b. 弦长参数化（α=0.5 → 欧氏距离的平方根） ───────────
    t = [0.0] * m
    for i in range(1, m):
        dx = ext[i][0] - ext[i - 1][0]
        dy = ext[i][1] - ext[i - 1][1]
        chord = math.sqrt(dx * dx + dy * dy)
        t[i] = t[i - 1] + math.sqrt(chord)  # α=0.5 → pow(chord, 0.5)

    # 原始循环：从 ext[2]=P_0 到 ext[n+2]=P_0（绕一圈回到起点）
    loop_start_idx = 2
    loop_end_idx = n + 2
    total_len = t[loop_end_idx] - t[loop_start_idx]
    if total_len < 1e-12:
        return points  # 所有点重合，直接返回

    # ── 3c. 线性辅助 ────────────────────────────────────────
    def _lerp(a, b, u):
        """a * (1-u) + b * u"""
        return (a[0] * (1 - u) + b[0] * u, a[1] * (1 - u) + b[1] * u)

    def _eval_segment(p0, p1, p2, p3, ta, tb, tc, td, t_global):
        """
        用 4 控制点 + 4 弦长参数，在 t_global 处三层递进插值。
        处理零分母：当两参数相同时返回 0.5 权重。
        """
        def _w(u, v, x):
            d = v - u
            if abs(d) < 1e-12:
                return 0.5
            return (x - u) / d

        w01 = _w(ta, tb, t_global)
        a1 = _lerp(p0, p1, w01)

        w12 = _w(tb, tc, t_global)
        a2 = _lerp(p1, p2, w12)

        w23 = _w(tc, td, t_global)
        a3 = _lerp(p2, p3, w23)

        w02 = _w(ta, tc, t_global)
        b1 = _lerp(a1, a2, w02)

        w13 = _w(tb, td, t_global)
        b2 = _lerp(a2, a3, w13)

        w12_2 = _w(tb, tc, t_global)
        return _lerp(b1, b2, w12_2)

    # ── 3d. 按弦长按比例均匀采样 ─────────────────────────────
    result = []
    for k in range(num_output):
        target_t = t[loop_start_idx] + (k / num_output) * total_len

        # 找到 target_t 落在哪个段（segment s 的弦长区间为 t[s+2] ~ t[s+3]）
        seg = -1
        for s in range(n):
            if t[s + 2] <= target_t <= t[s + 3]:
                seg = s
                break
        if seg < 0:
            seg = n - 1

        p0 = ext[seg + 1]
        p1 = ext[seg + 2]
        p2 = ext[seg + 3]
        p3 = ext[seg + 4]
        pt = _eval_segment(p0, p1, p2, p3,
                           t[seg + 1], t[seg + 2], t[seg + 3], t[seg + 4],
                           target_t)
        result.append(pt)

    # ── 3e. 去重相邻点 ──────────────────────────────────────
    deduped = [result[0]]
    for pt in result[1:]:
        if (pt[0] - deduped[-1][0]) ** 2 + (pt[1] - deduped[-1][1]) ** 2 > 1e-16:
            deduped.append(pt)
    while len(deduped) >= 2 and \
            (deduped[0][0] - deduped[-1][0]) ** 2 + \
            (deduped[0][1] - deduped[-1][1]) ** 2 < 1e-16:
        deduped.pop()

    if len(deduped) < 3:
        return points

    return deduped


# ═══════════════════════════════════════════════════════════════
#  第 4 步：画掩膜（超分抗锯齿 + 羽化 + 孔洞）
# ═══════════════════════════════════════════════════════════════

def _render_mask(
    w: int, h: int,
    outer: list,
    holes: Optional[list] = None,
    blur_radius: float = 1.5,
) -> Image.Image:
    """
    在 (w, h) 画布上渲染多边形掩膜。

    超分抗锯齿：4× 画布 → BICUBIC 降采样 → 高斯模糊羽化。

    Args:
        w, h: 原图分辨率
        outer: 外轮廓 [[x,y], ...]（像素坐标）
        holes: 可选，孔洞轮廓列表 [ [[x,y], ...], ... ]
        blur_radius: 羽化半径（像素）

    Returns:
        8-bit 灰度掩膜 Image（0-255）
    """
    # 4× 超分画布
    w4, h4 = w * 4, h * 4

    def _scale(pts):
        return [(int(x * 4), int(y * 4)) for x, y in pts]

    outer4 = _scale(outer)

    mask4 = Image.new("L", (w4, h4), 0)
    ImageDraw.Draw(mask4).polygon(outer4, fill=255)

    # ── 孔洞（用 XOR 实现镂空） ──────────────────────────────
    if holes:
        for hole in holes:
            hole4 = _scale(hole)
            hole_mask = Image.new("L", (w4, h4), 0)
            ImageDraw.Draw(hole_mask).polygon(hole4, fill=255)
            # XOR 要求 "1" 模式（二值），转成 "1" 运算完再转回 "L"
            mask_bin = mask4.convert("1")
            hole_bin = hole_mask.convert("1")
            mask4 = ImageChops.logical_xor(mask_bin, hole_bin).convert("L")

    # ── BICUBIC 降采样 ─────────────────────────────────────
    mask = mask4.resize((w, h), Image.BICUBIC)

    # ── 高斯模糊羽化 ────────────────────────────────────────
    if blur_radius > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    return mask


# ═══════════════════════════════════════════════════════════════
#  主入口
# ═══════════════════════════════════════════════════════════════

def matting_cut(
    image,
    contour_points: list,
    hole_points: Optional[list] = None,
    target_points: Optional[int] = None,
    blur_radius: float = 1.5,
    save_path: Optional[str] = None,
) -> tuple[Image.Image, Image.Image]:
    """
    AI 坐标 → 掩膜 → 抠图的全流程入口。

    Args:
        image: PIL Image 或文件路径
        contour_points: AI 返回的归一化 [0,1] 轮廓点 [(x,y), ...]
        hole_points: 可选，孔洞轮廓（多个孔洞时用 list of list）
        target_points: 插值点数，None 则根据轮廓周长自适应
        blur_radius: 边缘羽化半径（像素）
        save_path: 如果提供，保存结果图片

    Returns:
        (mask_image, result_image)
        mask_image: 8-bit 灰度掩膜（0-255）
        result_image: RGBA 扣图结果
    """
    # ── 加载图片 ──────────────────────────────────────────────
    if isinstance(image, str):
        img = Image.open(image).convert("RGBA")
    elif isinstance(image, Image.Image):
        img = image.convert("RGBA")
    else:
        raise TypeError("image 必须是 PIL Image 或文件路径")

    w, h = img.size

    # ── 第 1 步：预处理 ──────────────────────────────────────
    cleaned = _validate_and_sort(contour_points)

    # ── 第 2 步：自适应点数 ──────────────────────────────────
    n_pts = _adaptive_point_count(cleaned, override=target_points)

    # ── 第 3 步：Centripetal Catmull-Rom 插值 ────────────────
    smooth = _catmull_rom_centripetal(cleaned, n_pts)

    # ── 坐标 → 像素 ──────────────────────────────────────────
    def _to_pixel(pts):
        return [
            (max(0, min(w - 1, int(x * w))),
             max(0, min(h - 1, int(y * h))))
            for x, y in pts
        ]

    outer_px = _to_pixel(smooth)
    holes_px = None
    if hole_points:
        holes_px = [_to_pixel(h) for h in hole_points]

    # ── 第 4 步：渲染掩膜 ────────────────────────────────────
    mask = _render_mask(w, h, outer_px, holes_px, blur_radius)

    # ── 合成结果 ──────────────────────────────────────────────
    result = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    result.paste(img, (0, 0), mask)

    if save_path:
        result.save(save_path, format="PNG")
        mask.save(save_path.replace(".png", "_mask.png"), format="PNG")

    return mask, result


# ═══════════════════════════════════════════════════════════════
#  测试入口
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import os
    import sys

    # 生成椭圆形 50 点
    import math
    cx, cy = 0.5, 0.5
    rx, ry = 0.4, 0.3  # 长轴、短轴
    ellipse_pts = []
    for i in range(50):
        angle = 2 * math.pi * i / 50
        x = cx + rx * math.cos(angle)
        y = cy + ry * math.sin(angle)
        ellipse_pts.append((x, y))

    # 加一个孔洞（小椭圆）
    hole_pts = []
    for i in range(20):
        angle = 2 * math.pi * i / 20
        x = 0.5 + 0.12 * math.cos(angle)
        y = 0.5 + 0.08 * math.sin(angle)
        hole_pts.append((x, y))

    print(f"[TEST] 椭圆 50 点 + 孔洞 20 点")
    print(f"[TEST] 预期插值点数: {_adaptive_point_count(ellipse_pts)}")

    # 用纯色底图和测试图案
    test_img = Image.new("RGBA", (512, 512), (50, 120, 200, 255))
    draw = ImageDraw.Draw(test_img)
    # 画一个渐变填充的椭圆作为"物体"
    draw.ellipse([60, 100, 452, 412], fill=(255, 200, 80, 255), outline=None)
    # 在中心画个小圆模拟"孔洞"
    draw.ellipse([210, 220, 302, 292], fill=(50, 120, 200, 255))

    output_dir = os.path.dirname(os.path.abspath(__file__))
    # 也可以测试用路径输入
    script_dir = os.path.dirname(os.path.abspath(__file__))
    temp_path = os.path.join(script_dir, "..", "tests", "_matting_test_input.png")
    test_img.save(temp_path, format="PNG")
    print(f"[TEST] 测试图片已保存: {temp_path}")

    # 调用主函数（用路径）
    mask, result = matting_cut(
        image=temp_path,
        contour_points=ellipse_pts,
        hole_points=[hole_pts],
        blur_radius=1.5,
        save_path=os.path.join(output_dir, "..", "tests", "_matting_test_output.png"),
    )

    print(f"[TEST] mask: {mask.size}, mode={mask.mode}")
    print(f"[TEST] result: {result.size}, mode={result.mode}")
    print(f"[TEST] 输出已保存到 tests/_matting_test_output.png")
    print("[TEST] ✅ 测试完成")

    # 清理临时文件
    os.remove(temp_path)
