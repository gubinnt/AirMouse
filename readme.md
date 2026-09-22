# Remote Touchpad & Keyboard
内部代号：feishu（飞鼠）

这是一个基于 Python 后端的轻量级远程控制工具，可将移动设备（Android/iOS）转化为电脑的：触控板、键盘、语音输入工具、宏按键面板。

<table style="border: none;">
  <tr style="border: none;">
    <td style="border: none;">
      <img src="img/Screenshot_20260120-225705.jpg" width="400">
    </td>
    <td style="border: none;">
      <img src="img/Screenshot_20260123-224640.jpg" width="400">
    </td>
    <td style="border: none;">
      <img src="img/Screenshot_20260121-210258.jpg" width="400">
    </td>
    <td style="border: none;">
      <img src="img/Screenshot_20260123-224503.jpg" width="400">
    </td>
  </tr>
</table>

2026 03 22
增加手柄映射功能
<img width="2274" height="1263" alt="image" src="https://github.com/user-attachments/assets/64ea98af-8477-4033-88f0-90103079fd03" />


## 🌟 项目亮点

### 1. 简单启动
python一键启动，无需安装手机客户端。

### 2. 触控操作

* **单指**：移动 / 左键单击。
* **双指**：滚动 / 右键单击。
* **三指**：拖拽 / 中键单击。
* **gyro**：陀螺仪飞鼠

并且有提供鼠标前进、后退、中键、上下滚轮的按钮。



## 🛠️ 要求

* **免安装版**：无需任何依赖，Windows 下载即用
* **源码运行**：**Python 3.x**

## 🚀 快速启动

### 方式一：免安装版（Windows，推荐）

不需要装 Python，下载双击即用。从 [Releases](https://github.com/gubinnt/AirMouse/releases/latest)
下载 `AirMouseServer.exe`，放到桌面或自己的文件夹
（**不要放 `Program Files`**，程序需要往同目录写证书和配置），双击运行即可。
控制台会打印手机可访问的地址：

```
➤  https://192.168.1.9:5892 [推荐]
```

首次运行会自动在 exe 同目录生成 `cert.pem`、`key.pem`（自签证书）和
`macro_configs.json`、`gamepad_configs.json`（宏 / 手柄配置）。
需要控制以管理员权限运行的程序时，右键选「以管理员身份运行」。

### 方式二：源码运行

> 1 安装python3.11 ， 2 双击直接启动 AirMouseserver.bat ，会自动检查依赖和启动服务器。  
> 3 如果需要控制高权限程序，需要使用管理员权限启动。

 **安装依赖**：
```bash
pip install -r requirments.txt
```

 **运行服务端**：
```bash
python server.py
```




 **连接**（两种方式通用）：
确保手机与电脑在同一局域网，用手机浏览器访问**控制台里打印的那个地址**。

* **免安装版**：地址就在控制台输出里，默认 `5888`；若该端口被系统保留或占用
  （Hyper-V / WSL 会划走一部分端口段），程序会自动向后顺延到可用端口。
  也可以自己指定：
  ```bat
  set AIRMOUSE_PORT=18888
  AirMouseServer.exe
  ```
* **源码运行**：默认 `5888`。

例如： https://192.168.31.18:5888/ 

注意，浏览器会提示网页不安全，需要手工点进去信任，因为我们用的是自签的证书
> CHROME 浏览器安全限制，只有https网页才能传输陀螺仪数据。

**手机端建议使用 Edge / Chrome 打开。** 部分手机自带浏览器（尤其国产 ROM 定制版、
UC、夸克等）遇到自签证书时不会给出「继续访问」的入口，页面会一直转圈加载不出来，
看着像服务没起来，其实是浏览器策略问题。换成 Edge / Chrome 后，点一次
「高级 → 继续前往 xxx（不安全）」即可正常使用。

---

## 📂 项目结构

* `server.py`: Python 后端逻辑，处理 Socket 信号并调用系统接口。
* `templates/index.html`: 触控板页面。
* `templates/keyboard.html`: 键盘输入页面。
* `templates/voice.html`: 语音输入页面。
* `macro.html`: 宏按键页面。
* `macro_config.json`: 宏按键配置文件。
---

## 🔧 调优说明
- 建议使用安卓手机+chrome浏览器。
- 虽然 ios  safari 浏览器也可以正常使用，但是鼠标的移动会变得卡卡的。

# macos相关
使用mac版本需要线修改一些py代码，才能正常使用。
```py
# 删除printscreen键

SPECIAL_KEYS = {
    'ctrl': Key.ctrl, 'ctrl_r': Key.ctrl_r,
    'shift': Key.shift, 'shift_r': Key.shift_r,
    'alt': Key.alt, 'alt_r': Key.alt_r,
    'win': Key.cmd, 'command': Key.cmd, 'meta': Key.cmd,
    'enter': Key.enter, 'esc': Key.esc, 'tab': Key.tab, 'backspace': Key.backspace,
    'space': Key.space, 'delete': Key.delete,
    'up': Key.up, 'down': Key.down, 'left': Key.left, 'right': Key.right,
    'f1': Key.f1, 'f2': Key.f2, 'f3': Key.f3, 'f4': Key.f4, 'f5': Key.f5, 'f6': Key.f6,
    'f7': Key.f7, 'f8': Key.f8, 'f9': Key.f9, 'f10': Key.f10, 'f11': Key.f11, 'f12': Key.f12
}

# 修改滚动方向,它滚动方向和 Windows 是反过来的
@socketio.on('scroll')
def handle_scroll(data):
    # 处理双指滑动或按钮连发发来的滚动信号
    mouse.scroll(0, -data['dy']) 
```

    
## 更新日志

2026-09-23 Windows 单文件版 v1.0.3
- [x]  修复链路抖动时"卡一下、光标猛跳一段"：Socket.IO 在断连期间会把消息**缓冲起来**，重连后一次性补发。鼠标位移现在改用 `socket.volatile` 发送 —— 连接未就绪时**直接丢弃旧包**，而不是攒着等重连（对位移来说，丢旧包远比补发正确）。点击 / 拖拽 / 滚轮 / 按键**保持可靠传输不变**，丢一次点击就是一次误操作
- [x]  修复位移跨帧积压导致光标甩飞：链路卡顿后恢复时，累积位移可能在一帧内全部应用。现给单帧位移设上限并按比例压缩（保方向），同时新增 `reset_move` 事件在每次建连时清空服务端残留位移 —— [下载](https://github.com/gubinnt/AirMouse/releases/tag/v1.0.3)
- [x]  缩短重连真空期：重连退避由默认 1 秒起步改为 **0.1 秒**起步（上限 0.5 秒），连接超时 4 秒。每次重连都有一段命令真空期，缩短它等于直接减少卡顿窗口
- [x]  新增 `/diag` 链路诊断页：手机上直接查看**传输方式**（websocket 还是被降级成 polling）、RTT 曲线与 P95 / 最大 / 抖动 σ、**空闲态与负载态的抖动对比**（判断空口竞争占比）、上行到达间隔、断连重连次数、屏幕刷新率，并给出中文判读结论。负载测试走独立事件，**不会操作鼠标**
- [x]  新增 `/diag/stats` JSON 接口，服务端记录每次**接入 / 断开**日志（含时间戳），重连次数从"靠猜"变成"可看"
- [x]  修复启动时推荐地址混入失效网卡：地址列表现在过滤**已断开的接口**与 `169.254.x.x` 链路本地地址（本机实测由 14 条降到 6 条，不再把已拔掉网线的旧 IP 当推荐地址打出来）

2026-09-22 Windows 单文件版 v1.0.2
- [x]  修复鼠标移动不流畅（高刷新率屏幕尤其明显）：移动事件在服务端是**逐条串行执行**的，而每次执行中含一次 10 ms 等待（实测单次 11.13 ms），整体吞吐被锁在约 90 条/秒。60Hz 手机勉强跟上，120Hz 高刷屏每秒积压 30 条，连续滑动 3 秒后延迟累积超过 1 秒，表现就是"手指停下来了、光标还在追"。现改为「累积位移 + 144Hz 统一应用」，单次处理 11.13 ms → 0.37 µs，120Hz 连续滑动 3 秒的积压由 4007 ms 降到 0 ms —— [下载](https://github.com/gubinnt/AirMouse/releases/tag/v1.0.2)
- [x]  修复慢速移动"发涩"：pynput 会静默丢弃小数位移（`move(0.5, 0)` 光标完全不动），慢速微调时几乎没反应。现保留亚像素余数，累积到下一帧补齐
- [x]  飞鼠（陀螺仪）改走按帧合并：`devicemotion` 是独立于渲染帧的传感器数据流，采样率可能高于屏幕刷新率，合并后大幅减少消息量
- [x]  点击 / 拖拽 / 滚轮前先结算待应用的位移，动作位置更准确（避免快速点击落在尚未更新完的位置上）
- [x]  触控板位置判定改用平方比较，省掉热路径上每帧一次的开方运算

2026-09-22 Windows 单文件版 v1.0.1
- [x]  修复端口探测在 Windows 上的误判：`SO_REUSEADDR` 在 Windows 与 Unix 上语义不同 —— Unix 下它只影响 `TIME_WAIT`，Windows 下却允许绑定**已被其它 socket 占用**的地址。由于 werkzeug 自身会设置 `allow_reuse_address`，重复启动第二个实例时探测会把"端口已被占用"误判为可用，两个进程抢同一端口、浏览器连到哪个不确定。Windows 上改用 `SO_EXCLUSIVEADDRUSE` 明确排他，第二个实例现在会正确顺延（实测 `5892` → `5893`）—— [下载](https://github.com/gubinnt/AirMouse/releases/tag/v1.0.1)

2026-09-22 Windows 单文件版 v1.0.0
- [x]  新增 Windows 免安装单文件打包，产出 `AirMouseServer.exe`（约 16.5 MB），双击即用、无需装 Python —— [下载](https://github.com/gubinnt/AirMouse/releases/tag/v1.0.0)
- [x]  修复端口落在系统保留段内导致无法启动：`5888` 可能被 Hyper-V / WSL 划走（本机实测保留段 `5792-5891`），绑定会以 `WSAEACCES (10013)` 失败；现在启动前自动探测端口，被占则向后回退，也可用 `AIRMOUSE_PORT` 指定
- [x]  修复 Windows 控制台打印 emoji（`print("🚀 ...")`）抛 `UnicodeEncodeError` 导致进程直接退出，启动时把控制台切到 UTF-8
- [x]  修复打包后证书 / 配置文件相对路径失效：改为首次运行自动把 `cert.pem`、`key.pem`、`macro_configs.json`、`gamepad_configs.json` 释放到 exe 同目录
- [x]  补入 `gyro/`、`laji/` 下的调试页到 `templates/`，`/t` 与 `/test` 路由不再 500
- [x]  文档补充免安装版用法与手机端浏览器建议：手机自带浏览器（国产 ROM 定制版 / UC / 夸克等）遇到自签证书可能不给「继续访问」入口，页面一直转圈，建议改用 Edge / Chrome

2026-01-23 Day3
- [x]  两个手指快速抬起导致识别成鼠标跳转修复
- [x]  “单指长按拖拽”功能
- [x]  将触控板逻辑提取为独立模块 `touchpad.js`，实现多页面同步更新


2026-01-21 Day2
- [x]  点击返回时强制清除所有长按功能，以防止影响触控
- [x]  飞鼠增加一些微小动作滤除，防手抖

- [x]  键盘上下左右 无效 另外位置也不舒服
- [x]  键盘del 按钮位置不对 应该在F12右边
- [x]  缺少printscreen 按钮
- [x]  缺少反斜杠按钮（在括号右边）

- [x]  输入条太小并不能实时语音上屏（之前让他实时上屏存在一点问题）
- [x]  或许我可以再搞个独立页面专门用来语音上屏,并且可以切换实时上屏和输入框模式
- [x]  记住gyro模式，如果之前是开启那么回到页面自动开启
- [x]  键盘模式默认就横过来展示，无视手机的方向（如果检测到是手机）
  
2026-01-21 Day1
- [x]  实现整体基础架构
- [x]  实现飞鼠功能还有鼠标控制功能以及三指拖动功能等
- [x]  实现键盘功能
