from pygdbmi.gdbcontroller import GdbController
import subprocess  # 用于构建 rr 命令

# 构建 rr replay 命令（相当于 rr replay -i=mi trace_dir）
# 注意：pygdbmi 支持自定义启动命令
trace_dir = '/home/vince.wu/.local/share/rr/latest-trace'
# --interpreter=mi3
cmd = ['rr', 'replay', '-i=mi', '--debugger-option="--interpreter=mi"',  trace_dir]
# cmd = ['rr', 'replay', '-d', 'gdb --interpreter=mi3', trace_dir]
gdbmi = GdbController(command=cmd, time_to_check_for_additional_output_sec=1)  # 启动 rr + GDB/MI

# 发送 MI 命令：设置断点（在 main 函数）
response = gdbmi.write('-break-insert main', timeout_sec=1)
print("断点响应:", response)  # 输出: [{'payload': [{'bkpt': {...]}], 'type': 'result'}]

# 重放执行（从 trace 开始）
response = gdbmi.write('-exec-run', timeout_sec=1)
print("重放响应:", response)  # 捕获停止事件、信号等

# 反向执行（rr 独有）
response = gdbmi.write('-exec-reverse-step', timeout_sec=1)
print("反向步进:", response)

# 获取栈追踪
response = gdbmi.write('-stack-list-frames', timeout_sec=1)
print("栈帧:", response)

# 退出
gdbmi.write('-gdb-exit', timeout_sec=1)
