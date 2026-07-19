"""
rate_limiter.py — Gemini API 按 Key 追踪 + 自适应速率控制

核心原则：
  1. 按 API Key 独立追踪（不同 Key 不同配额）
  2. 不硬编码额度上限（只能看 Dashboard，无法 API 查询）
  3. 展示真实用量，不展示不可知的上限
  4. RPM 自适应：从保守起步，无 429 则加速，遇 429 则减速

使用方式：
    from rate_limiter import track_request

    # 获取某 API Key 的追踪器
    tracker = track_request(api_key)

    # RPM 节流（如需要会自动等待）
    tracker.wait()

    # 调用 API 后：
    if resp.status_code == 429:
        tracker.record_429()   # 减速，自适应 RPM 下降
    else:
        tracker.record_success()  # 可能加速

    # 给前端展示
    info = tracker.get_info()
    # → {"rpd_used": 42, "rpm_current": 8, "rpm_range": [2, 30]}

参考文档：https://ai.google.dev/gemini-api/docs/rate-limits
"""

import hashlib
import logging
import threading
import time
from collections import deque
from datetime import date, datetime
from typing import Optional

logger = logging.getLogger(__name__)

# ── 自适应 RPM 参数 ──────────────────────────────────────────
_MIN_RPM = 2          # 最低 RPM（遇 429 后降到这个值）
_MAX_RPM = 30         # 最高 RPM（从不触发 429 的情况下）
_START_RPM = 5        # 初始 RPM
_SPEEDUP_STEP = 1     # 每次成功 +1 RPM
_SLOWDOWN_STEP = 5    # 每次 429 -5 RPM


def _hash_key(api_key: str) -> str:
    """对 API Key 做哈希，避免明文存日志"""
    return hashlib.sha256(api_key.encode()).hexdigest()[:12]


class _KeyTracker:
    """单个 API Key 的跟踪器"""

    def __init__(self, api_key: str):
        self.key_hash = _hash_key(api_key)
        self._lock = threading.Lock()
        # RPM 滑动窗口
        self._timestamps: deque = deque()
        self._current_rpm = _START_RPM
        # RPD 日计数
        self._today: Optional[date] = None
        self._daily_count: int = 0

    # ── 公开方法 ──────────────────────────────────────────────

    def wait(self):
        """等待 RPM 窗口（如必要），限速值自适应"""
        with self._lock:
            now = time.time()
            # 清理过期记录
            while self._timestamps and now - self._timestamps[0] > 60:
                self._timestamps.popleft()

            if len(self._timestamps) >= self._current_rpm:
                # 超出当前 RPM，等最早的过期
                wait = self._timestamps[0] + 60 - now
                if wait > 0:
                    logger.info(
                        "RPM wait %.1fs (%s, %d/min)",
                        wait, self.key_hash, self._current_rpm
                    )
                    time.sleep(wait)
                self._timestamps.popleft()

            self._timestamps.append(time.time())

    def record_success(self):
        """记录一次成功调用 → 可能加速"""
        with self._lock:
            self._check_date()
            self._daily_count += 1
            # 加速：每次成功 +1，不超过上限
            self._current_rpm = min(self._current_rpm + _SPEEDUP_STEP, _MAX_RPM)

    def record_429(self):
        """记录一次 429 限流 → 立即减速"""
        with self._lock:
            self._check_date()
            self._daily_count += 1
            # 减速：当前 RPM 减半，不低于下限
            self._current_rpm = max(_MIN_RPM, self._current_rpm - _SLOWDOWN_STEP)
            logger.warning(
                "429 detected (%s) → RPM slowed to %d/min",
                self.key_hash, self._current_rpm
            )

    def get_info(self) -> dict:
        """返回当前用量信息（给前端展示）"""
        with self._lock:
            self._check_date()
            return {
                "key_hash": self.key_hash,
                "rpd_used": self._daily_count,
                "rpm_current": self._current_rpm,
                "rpm_range": [_MIN_RPM, _MAX_RPM],
                "rpd_exhausted": False,  # 我们不知道上限，所以永不说用尽
            }

    def _check_date(self):
        """跨日重置"""
        today = date.today()
        if self._today != today:
            self._today = today
            self._daily_count = 0


# ── 全局管理器 ────────────────────────────────────────────────
class _Manager:
    """管理所有 API Key 的跟踪器"""

    def __init__(self):
        self._lock = threading.Lock()
        self._trackers: dict[str, _KeyTracker] = {}

    def get(self, api_key: str) -> _KeyTracker:
        """获取（或创建）某 Key 的跟踪器"""
        kh = _hash_key(api_key)
        with self._lock:
            if kh not in self._trackers:
                self._trackers[kh] = _KeyTracker(api_key)
                logger.info("New tracker for key %s (RPM: %d)", kh, _START_RPM)
            return self._trackers[kh]

    def list_all(self) -> list[dict]:
        """列出所有已知 Key 的用量"""
        with self._lock:
            return [t.get_info() for t in self._trackers.values()]


manager = _Manager()


# ── 便捷函数 ──────────────────────────────────────────────────
def track_request(api_key: str) -> _KeyTracker:
    """获取（或创建）某 API Key 的追踪器"""
    return manager.get(api_key)


def list_all_keys() -> list[dict]:
    """列出所有已知 Key 的用量"""
    return manager.list_all()
