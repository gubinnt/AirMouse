"""鼠标控制服务。

## 为什么不是"收到一条消息就移动一次"

原始实现在 Socket.IO 的事件线程里同步执行 `mouse.move()`，而这次排查发现
真正的开销藏在唤醒逻辑里：

    pynput mouse.move()        0.034 ms
    wake_up_cursor()          11.159 ms   ← 内含 sleep(0.01)
    handle_move() 完整路径     11.130 ms

flask-socketio 在本项目下自动选用 `threading` 模式（未安装 eventlet/gevent），
**同一个连接的消息是串行处理的**。于是服务端吞吐被锁死在 1000/11.13 ≈ 90 条/秒：

    手机 60Hz  → 需要 60 条/秒   勉强跟上，没有余量
    手机 90Hz  → 需要 90 条/秒   每秒积压
    手机 120Hz → 需要 120 条/秒  每秒积压 30 条，滑 3 秒后延迟累积到 1 秒以上

表现出来就是"手指停下来了，光标还在追"。

## 现在的模型：两级流水

  1. `handle_move()` 只把位移累加进缓冲，**立即返回**（微秒级），
     事件线程不再被阻塞，输入不会再排队。
  2. 一个固定帧率（≤144Hz）的后台线程把累积位移整体应用到光标。

好处不只是"更快"，还有：
  - 天然平滑：每一帧应用的是这一帧内累积的真实位移，与手机采样率无关；
  - 天然抗积压：哪怕前端发 500 条/秒，系统调用次数也固定在 144 次/秒；
  - 顺带修掉一个精度问题 —— pynput 会静默丢弃小数位移
    （实测 `move(0.5, 0)` 光标纹丝不动），慢速移动会"发涩"。
    这里保留亚像素余数，下一帧补上。
"""

import platform
import ctypes
import time
import threading

from pynput.mouse import Controller, Button

# macOS 兼容性补丁：处理某些 pyobjc 版本缺失 CGDisplayPixelsHigh 的问题
if platform.system() == 'Darwin':
    try:
        import Quartz
        if not hasattr(Quartz, 'CGDisplayPixelsHigh'):
            def CGDisplayPixelsHigh(display_id):
                return int(Quartz.CGDisplayBounds(display_id).size.height)
            Quartz.CGDisplayPixelsHigh = CGDisplayPixelsHigh
    except Exception:
        pass

mouse = Controller()

# ─────────────────────────────────────────────────────────────────────
# 移动渲染：累积缓冲 + 固定帧率应用
# ─────────────────────────────────────────────────────────────────────

TARGET_FPS = 144
_FRAME_INTERVAL = 1.0 / TARGET_FPS

# 单帧位移上限（像素）。
#
# 正常实时输入下，144Hz 的一帧（6.9ms）里累积的位移远低于这个值；
# 一旦超过，说明这一帧里塞进了"多个现实帧"的位移 —— 典型场景是链路卡顿
# 之后，客户端把缓冲的命令一次性补发过来（Socket.IO 默认行为）。
# 此时按比例压缩到上限：保住方向感，但不让光标"飞"出去。
MAX_STEP_PX = 1000.0

_pending_dx = 0.0      # 已收到、尚未应用的位移
_pending_dy = 0.0
_rem_dx = 0.0          # 亚像素余数，留给下一帧（pynput 会丢弃小数）
_rem_dy = 0.0
_pending_lock = threading.Lock()
_clamped_frames = 0    # 触发过压缩的帧数，供诊断接口读取


def handle_move(data):
    """累积位移后立即返回。

    与旧实现的关键区别：不再同步操作光标。单次调用从 11.13 ms 降到微秒级，
    Socket.IO 事件线程不会被阻塞，所以高频输入不会在服务端排队。
    """
    global _pending_dx, _pending_dy
    with _pending_lock:
        _pending_dx += data['dx']
        _pending_dy += data['dy']


def _take_pending():
    """取出并清空累积位移。"""
    global _pending_dx, _pending_dy
    with _pending_lock:
        dx, dy = _pending_dx, _pending_dy
        _pending_dx = _pending_dy = 0.0
    return dx, dy


def flush_move():
    """把累积位移立即应用到光标。

    需要"动作发生在当前正确位置"的场景（点击、拖拽、滚轮）会先调用它，
    否则这些动作可能作用在尚未更新完的位置上。
    """
    global _rem_dx, _rem_dy, _clamped_frames
    dx, dy = _take_pending()
    if not dx and not dy:
        return
    # 积压保护：单帧位移过大 = 这一帧里混进了"多个现实帧"的位移
    mag = max(abs(dx), abs(dy))
    if mag > MAX_STEP_PX:
        k = MAX_STEP_PX / mag
        dx *= k
        dy *= k
        _clamped_frames += 1
    x, y = dx + _rem_dx, dy + _rem_dy
    ix, iy = int(x), int(y)
    _rem_dx, _rem_dy = x - ix, y - iy
    if ix or iy:
        mouse.move(ix, iy)
        wake_up_cursor()


def reset_pending():
    """丢弃尚未应用的位移。

    客户端每次建连（含重连）都会调用一次，避免把断连前残留的位移在重连
    瞬间一次性补上 —— 那正是"卡一下、然后光标猛跳一段"的成因之一。
    """
    global _pending_dx, _pending_dy, _rem_dx, _rem_dy
    with _pending_lock:
        _pending_dx = _pending_dy = 0.0
        _rem_dx = _rem_dy = 0.0


def stats():
    """运行时统计，供诊断接口读取。"""
    with _pending_lock:
        px, py = _pending_dx, _pending_dy
    return {
        'pending_dx': px,
        'pending_dy': py,
        'clamped_frames': _clamped_frames,
        'target_fps': TARGET_FPS,
        'max_step_px': MAX_STEP_PX,
    }


def _render_loop():
    """按固定帧率把累积位移应用到光标。

    用"目标时间累加 + 动态补偿"而不是固定的 sleep(1/144)，这样即使系统
    sleep 精度不足（Windows 默认定时器分辨率较粗）也不会累积漂移。
    """
    next_t = time.perf_counter()
    while True:
        next_t += _FRAME_INTERVAL
        delay = next_t - time.perf_counter()
        if delay > 0:
            time.sleep(delay)
        else:
            # 落后超过一帧（系统忙），重置基准，不做追赶式补帧
            next_t = time.perf_counter()
        try:
            flush_move()
        except Exception:
            pass


threading.Thread(target=_render_loop, daemon=True, name='airmouse-render').start()


# ─────────────────────────────────────────────────────────────────────
# 光标唤醒
# ─────────────────────────────────────────────────────────────────────

_WAKE_MIN_INTERVAL = 0.5   # 秒：两次唤醒之间的最小间隔
_last_wake = 0.0


def wake_up_cursor(force=False):
    """把光标从"系统未跟踪"状态唤醒。

    旧实现每次移动都执行，且内含 10 ms sleep，实测单次 11.2 ms —— 因为
    同一连接的消息串行处理，这一项就锁死了整体吞吐。现在按时间节流：
    一次连续滑动最多触发一到两次。
    """
    global _last_wake
    if platform.system() != 'Windows':
        return
    now = time.monotonic()
    if not force and now - _last_wake < _WAKE_MIN_INTERVAL:
        return
    _last_wake = now
    MOUSEEVENTF_MOVE = 0x0001
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_MOVE, 1, 1, 0, 0)
    time.sleep(0.001)
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_MOVE, -1, -1, 0, 0)


# ─────────────────────────────────────────────────────────────────────
# 按键 / 拖拽 / 滚轮
# ─────────────────────────────────────────────────────────────────────
# 以下每个入口都先 flush_move()，确保动作落在最新位置上。
# 位置若滞后，快速点击会点偏，拖拽起始点也会错。

def handle_click(data):
    flush_move()
    button_type = data.get('button')
    if button_type == 'left':
        mouse.click(Button.left)
    elif button_type == 'right':
        mouse.click(Button.right)
    elif button_type == 'middle':
        mouse.click(Button.middle)
    elif button_type == 'x1':
        mouse.click(Button.x1)
    elif button_type == 'x2':
        mouse.click(Button.x2)


def handle_drag_start():
    flush_move()
    mouse.release(Button.left)
    mouse.press(Button.left)


def handle_drag_end():
    mouse.release(Button.left)


def handle_mid_down():
    flush_move()
    mouse.release(Button.middle)
    mouse.press(Button.middle)


def handle_mid_up():
    mouse.release(Button.middle)


def handle_scroll(data):
    # dx: 水平, dy: 垂直
    flush_move()
    dx = data.get('dx', 0)
    dy = data.get('dy', 0)

    # macOS 滚动方向通常与 Windows 相反
    if platform.system() == 'Darwin':
        mouse.scroll(-dx, -dy)
    else:
        mouse.scroll(dx, dy)
