import platform
import socket
import time
import psutil
from flask import Flask, render_template, request
from flask_socketio import SocketIO

app = Flask(__name__)
# 允许所有来源跨域，确保手机能连上
socketio = SocketIO(app, cors_allowed_origins="*")

def get_all_ip_addresses():
    """返回 [(网卡名, IPv4), ...]，供启动时打印可访问地址。

    只保留「已启用」且「非回环 / 非链路本地」的地址 —— 否则会把已断开的
    网卡也列出来（拔线后网卡仍保留失效的旧 IP，如无线网卡保留 192.168.1.9），
    把用户引向一个根本打不开的地址。
    """
    ip_list = []
    stats = psutil.net_if_stats()
    for interface, addrs in psutil.net_if_addrs().items():
        st = stats.get(interface)
        if st is not None and not st.isup:
            continue                          # 网卡已断开 → 其 IP 不可达
        for addr in addrs:
            if addr.family != socket.AF_INET:
                continue
            ip = addr.address
            if ip.startswith("127.") or ip.startswith("169.254."):
                continue                      # 回环 / 链路本地（APIPA）
            ip_list.append((interface, ip))
    return ip_list

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/touchpad')
def touchpad_page():
    return render_template('index.html')

@app.route('/k')
def keyboard_page(): 
    return render_template('keyboard.html')

@app.route('/v')
def voice_page():
    return render_template('voice.html')

@app.route('/test')
def vibe_test():
    return render_template('vibe_test.html')

@app.route('/t')
def air_mouse_test():
    return render_template('t.html')

@app.route('/r')
def real_mouse_page():
    return render_template('realmouse.html')

@app.route('/b')
def buttons_page():
    return render_template('buttons.html')

@app.route('/controller')
def controller_page():
    return render_template('controller.html')

@app.route('/diag')
def diag_page():
    """链路诊断页。

    手机上打开后可以实测：当前传输方式（websocket 还是 polling）、往返延迟、
    抖动、丢包、断连次数，以及"有流量 vs 无流量"两种状态下的抖动差异。
    用于在改代码之前先把根因钉死，避免凭感觉调参。
    """
    return render_template('diag.html')


@app.route('/diag/stats')
def diag_stats():
    """运行时统计（JSON）。

    让诊断不必只依赖手机页面 —— 在电脑上 curl 一下就能看到服务端的
    累积位移、积压压缩次数等内部状态。
    """
    from mouse_service import stats as move_stats
    return {'move': move_stats()}


# ─────────────────────────────────────────────────────────────────────
# 链路诊断：探测事件
# ─────────────────────────────────────────────────────────────────────
# 客户端每 100ms 发一个 diag_ping，本端原样回传客户端时间戳（客户端据此
# 算 RTT，不需要时钟同步），并附加"本包与上一包的到达间隔"。
#
# 为什么额外回传到达间隔：客户端发包是固定 100ms，服务端测到的到达间隔
# 若忽大忽小，说明抖动发生在**手机 → 路由器**这一段（上行），而不是在
# 服务端或下行。这能直接区分"链路问题"和"代码问题"。

_diag_last_arrival = {}


@socketio.on('diag_ping')
def handle_diag_ping(data):
    now = time.perf_counter()
    sid = request.sid
    prev = _diag_last_arrival.get(sid)
    _diag_last_arrival[sid] = now

    recv_at = time.perf_counter()
    resp = {'t': (data or {}).get('t')}
    if prev is not None:
        resp['gap'] = round((now - prev) * 1000.0, 2)
    resp['proc'] = round((time.perf_counter() - recv_at) * 1000.0, 3)
    return resp


@socketio.on('diag_load')
def handle_diag_load(data):
    """负载测试包。

    只用来制造与真实触控板同频、同大小的上行流量，然后丢弃 —— 不操作鼠标，
    所以做诊断时不会把电脑光标带跑。
    """
    return None


# 注意：connect 事件由 server.py 注册（那边还要广播 os_info）。
# 本文件不要再注册一次 —— flask-socketio 对同一事件是"后注册的覆盖先注册的"，
# 而 server.py 在 `from web_app import ...` 之后才注册，会把这里的实现顶掉。

@socketio.on('disconnect')
def handle_diag_disconnect():
    _diag_last_arrival.pop(request.sid, None)
    print(f'[airmouse] 断开 {request.sid}', flush=True)


@socketio.on('reset_move')
def handle_reset_move(data=None):
    """客户端每次建连时调用：丢弃服务端残留位移。

    避免断连前攒下的位移在重连瞬间被一次性补上 —— 那会让光标"猛跳一段"。
    """
    from mouse_service import reset_pending
    reset_pending()
    return None
