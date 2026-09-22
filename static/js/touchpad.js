/**
 * Touchpad Module for AirMouse
 * Encapsulates movement, scrolling, multi-touch gestures, and long-press dragging.
 */
class Touchpad {
    constructor(elementId, socket, options = {}) {
        this.pad = document.getElementById(elementId);
        if (!this.pad) return;

        this.socket = socket;
        this.getSensitivity = options.getSensitivity || (() => 4.0);
        this.feedback = options.feedback || (() => { });

        this.lx = 0; this.ly = 0; // last x, y
        this.sx = 0; this.sy = 0; // start x, y
        this.hMove = false;
        this.tCount = 0;
        this.maxTCount = 0;
        this.drag = false;
        this.longPressTimer = null;
        this.lastMultiTouchTime = 0;

        // 位移发送缓冲。触摸事件本身由浏览器按帧派发，频率已经 <= 屏幕刷新率，
        // 直接发送不会带来额外延迟；但陀螺仪（devicemotion）是独立于渲染帧的
        // 传感器数据流，频率可能远高于刷新率，统一走 queueMove() 按帧合并。
        this.pdx = 0; this.pdy = 0;
        this._rafId = null;

        this._bindEvents();
    }

    _bindEvents() {
        this.pad.oncontextmenu = (e) => e.preventDefault();

        this.pad.addEventListener('touchstart', e => this._handleTouchStart(e));
        this.pad.addEventListener('touchmove', e => this._handleTouchMove(e), { passive: false });
        this.pad.addEventListener('touchend', e => this._handleTouchEnd(e));
        this.pad.addEventListener('touchcancel', () => this._handleTouchCancel());
    }

    /**
     * 发送一条位移（volatile）。
     *
     * 为什么必须 volatile：链路一抖，Socket.IO 默认会把这些消息**缓冲**下来，
     * 等重连后一次性补发 —— 手感就是"卡一下、然后光标猛跳一大段"。
     * 带 volatile 标记的包在连接不可用时**直接丢弃**，不进缓冲。
     * 对位移来说，丢旧包永远比补发旧包正确：手指早就移到别处了，
     * 光标再追上去只会让人更迷惑。
     */
    _sendMove(dx, dy) {
        if (!this.socket) return;
        if (this.socket.volatile) this.socket.volatile.emit('move', { dx, dy });
        else this.socket.emit('move', { dx, dy });   // 兜底：客户端库过老时没有 volatile
    }

    /**
     * 立即发送一次位移。
     * 先 flush 缓冲，保证陀螺仪攒下的位移不会插到触摸位移之后，否则光标会回跳。
     */
    _emitMove(dx, dy) {
        this._flushPending();
        this._sendMove(dx, dy);
    }

    /**
     * 按帧合并的位移入口，供高频数据源（陀螺仪 devicemotion）使用。
     * 位移累积后一次性发出，不丢精度；同一帧内调用多次也只发一条消息。
     * 触摸路径不走这里 —— 触摸事件本来就按帧派发，直接发没有额外延迟。
     */
    queueMove(dx, dy) {
        this.pdx += dx;
        this.pdy += dy;
        if (this._rafId !== null) return;
        this._rafId = requestAnimationFrame(() => {
            this._rafId = null;
            this._flushPending();
        });
    }

    /** 把缓冲中的位移立刻发出去（手势结束或需要保证顺序时调用）。 */
    _flushPending() {
        if (this._rafId !== null) {
            cancelAnimationFrame(this._rafId);
            this._rafId = null;
        }
        if (this.pdx === 0 && this.pdy === 0) return;
        const dx = this.pdx, dy = this.pdy;
        this.pdx = 0; this.pdy = 0;
        this._sendMove(dx, dy);
    }

    _handleTouchStart(e) {
        const prevTCount = this.tCount;
        this.tCount = e.targetTouches.length;

        if (this.tCount === 1 && prevTCount === 0) {
            this.maxTCount = 1;
        } else {
            this.maxTCount = Math.max(this.maxTCount, this.tCount);
        }

        const touch = e.targetTouches[0];
        this.lx = touch.clientX;
        this.ly = touch.clientY;
        this.sx = this.lx;
        this.sy = this.ly;
        this.hMove = false;

        // Long press for drag (single finger)
        if (this.tCount === 1) {
            this.longPressTimer = setTimeout(() => {
                this.drag = true;
                this.socket.emit('drag_start');
                this.pad.style.background = "#001a33";
                this.feedback();
            }, 500);
        }

        // Three finger visual feedback (drag starts on move)
        if (this.tCount === 3) {
            this.pad.style.background = "#001a33";
        }
    }

    _handleTouchMove(e) {
        e.preventDefault();
        const prevTCount = this.tCount;
        this.tCount = e.targetTouches.length;
        this.maxTCount = Math.max(this.maxTCount, this.tCount);

        const touch = e.targetTouches[0];
        const cx = touch.clientX, cy = touch.clientY;

        // Multi-touch to single-touch lock (300ms)
        if (prevTCount >= 2 && this.tCount === 1) {
            this.lastMultiTouchTime = Date.now();
        }

        // Movement threshold
        // 用平方比较代替 Math.hypot，省掉热路径上每帧一次的开方
        const mdx = cx - this.sx, mdy = cy - this.sy;
        if (mdx * mdx + mdy * mdy > 25) {
            this.hMove = true;
            if (this.longPressTimer) {
                clearTimeout(this.longPressTimer);
                this.longPressTimer = null;
            }
            // Three finger drag start
            if (this.tCount === 3 && !this.drag) {
                this.drag = true;
                this.socket.emit('drag_start');
            }
        }

        const sensitivity = this.getSensitivity();

        if (this.tCount === 1 || this.tCount === 3) {
            if (Date.now() - this.lastMultiTouchTime > 300) {
                this._emitMove(
                    (cx - this.lx) * sensitivity,
                    (cy - this.ly) * sensitivity
                );
            }
            this.lx = cx;
            this.ly = cy;
        } else if (this.tCount === 2) {
            // 滚动时持续更新lastMultiTouchTime, 确保松手后300ms内不移动鼠标
            this.lastMultiTouchTime = Date.now();
            const dy = cy - this.ly;
            if (Math.abs(dy) > 5) {
                this.socket.emit('scroll', { dy: dy > 0 ? 1 : -1 });
                this.ly = cy;
            }
        }
    }

    _handleTouchEnd(e) {
        this._flushPending();
        const prevTCount = this.tCount;
        this.tCount = e.targetTouches.length;

        if (prevTCount >= 2 && this.tCount === 1) {
            this.lastMultiTouchTime = Date.now();
        }

        if (this.longPressTimer) {
            clearTimeout(this.longPressTimer);
            this.longPressTimer = null;
        }

        if (this.drag) {
            if (this.tCount === 0) {
                this.socket.emit('drag_end');
                this.drag = false;
                this.pad.style.background = ""; // Rely on original CSS or handle here
            }
        } else if (this.tCount === 0) {
            if (!this.hMove) {
                if (this.maxTCount === 1) this.socket.emit('click', { button: 'left' });
                else if (this.maxTCount === 2) this.socket.emit('click', { button: 'right' });
                else if (this.maxTCount === 3) this.socket.emit('click', { button: 'middle' });
            }
        }

        if (this.tCount === 0) {
            this.maxTCount = 0;
            this.pad.style.background = "";
            // If there's a global stopScroll, it should be handled outside or via callback
            if (window.stopScroll) window.stopScroll();
        }
    }

    _handleTouchCancel() {
        this._flushPending();
        this.tCount = 0;
        this.maxTCount = 0;
        this.pad.style.background = "";
        if (this.drag) {
            this.socket.emit('drag_end');
            this.drag = false;
        }
        if (this.longPressTimer) {
            clearTimeout(this.longPressTimer);
            this.longPressTimer = null;
        }
        if (window.stopScroll) window.stopScroll();
    }

    // External access to current multitouch lock
    isLocked() {
        return (Date.now() - this.lastMultiTouchTime < 300);
    }

    getLastMultiTouchTime() {
        return this.lastMultiTouchTime;
    }
}

// Export for use in scripts
window.TouchpadModule = Touchpad;
