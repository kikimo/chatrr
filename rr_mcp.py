from pygdbmi.gdbcontroller import GdbController
from typing import Optional, List, Dict
import logging
import json, time

DEFAULT_WRITE_TIMEOUT = 8848

trace_dir = '/home/vince.wu/.local/share/rr/latest-trace'
trace_dir = '/root/.local/share/rr/latest-trace'
trace_dir = '/root/.local/share/rr/nebula-graphd-0'

cmd = ['rr', 'replay', '-i=mi', '--debugger-option="--interpreter=mi3"',  trace_dir]
# cmd = ['rr', 'replay', '-i=mi', trace_dir]

logger = logging.getLogger('rr_mcp')

class RRController(GdbController):
    def __init__( self, command: Optional[List[str]] = None,
        time_to_check_for_additional_output_sec: float = 1,
    ) -> None:
        super().__init__(command=command, time_to_check_for_additional_output_sec=time_to_check_for_additional_output_sec)

    def run_cmd_and_wait(self, cmd:str) -> List[Dict]:
        logger.info(f'running cmd: {cmd}')
        return self.write(cmd) + self.wait_for_stop()

    def _wait(self, typs:List[str], msgs:List[str]) -> List[Dict]:
        resps = []
        done = False
        while not done:
            responses = self.get_gdb_response(timeout_sec=0.5, raise_error_on_timeout=False)
            if responses:
                print(f'responses: {json.dumps(responses, indent=2)}')
                logger.info(f'responses: {json.dumps(responses, indent=2)}')
                resps.extend(responses)
            else:
                continue

            for resp in responses:
                if resp["type"] in typs and resp["message"] in msgs:
                    done = True
        return resps

    def wait_for_ready(self) -> List[Dict]:
        return self._wait(typs=["notify"], msgs=["stopped"])

    def wait_for_stop(self)->List[Dict]:
        return self._wait(["result", 'notify'], ["done", 'stopped'])

gdbmi = RRController(command=cmd, time_to_check_for_additional_output_sec=1)  # 启动 rr + GDB/MI
resps =  gdbmi.wait_for_ready()
print(f'wait for ready: {json.dumps(resps, indent=2)}')
resps = gdbmi.run_cmd_and_wait('c')
print(f'cont : {json.dumps(resps, indent=2)}')
resps = gdbmi.run_cmd_and_wait('bt 128')
print(f'bt 128: {json.dumps(resps, indent=2)}')
gdbmi.write('-gdb-exit')

# # # 发送 MI 命令：设置断点（在 main 函数）
# # response = gdbmi.write('-break-insert main', timeout_sec=DEFAULT_WRITE_TIMEOUT)
# # print("断点响应:", json.dumps(response, indent=2))  # 输出: [{'payload': [{'bkpt': {...]}], 'type': 'result'}]

# # # 重放执行（从 trace 开始）
# # response = gdbmi.write('-exec-run', timeout_sec=DEFAULT_WRITE_TIMEOUT)
# # print("重放响应:", json.dumps(response, indent=2))  # 捕获停止事件、信号等

# # response = gdbmi.write('-exec-continue')
# response = gdbmi.write('c')
# print("run to end:", json.dumps(response, indent=2))  # 捕获停止事件、信号等

# MAX_WAIT_TIME = 30  # 最大等待时间（秒）

# def print_response(label, response):
#     """格式化打印响应，仅显示 result 类型，忽略 notify"""
#     print(f"\n=== {label} ===")
#     for resp in response:
#         if resp["type"] == "result":
#             print(json.dumps(resp, indent=2))
#         elif resp["type"] == "notify":
#             print(f"[忽略异步通知] {resp['message']}")

# # 4. 等待程序崩溃
# while True:
#     # 非阻塞获取 GDB 输出
#     responses = gdbmi.get_gdb_response(timeout_sec=0.1, raise_error_on_timeout=False)
#     for resp in responses:
#         if resp["type"] == "notify" and resp["message"] == "stopped":
#             reason = resp["payload"].get("reason", "")
#             if reason == "signal-received":
#                 signal_name = resp["payload"].get("signal-name", "")
#                 print(f"程序因信号 {signal_name} 停止")
#                 # 获取堆栈信息
#                 # response = gdbmi.write('-interpreter-exec console "bt"', timeout_sec=DEFAULT_WRITE_TIMEOUT)
#                 response = gdbmi.write('bt 128', timeout_sec=DEFAULT_WRITE_TIMEOUT)
#                 print("bt 输出:", json.dumps(response, indent=2))
#                 # print_response("bt 输出", json.dumps(response))
#                 # response = gdbmi.write('-stack-list-frames', timeout_sec=DEFAULT_WRITE_TIMEOUT)
#                 # print_response("栈帧信息 (MI)", response)
#                 break
#     else:
#         # 没有停止事件，继续等待
#         continue
#     break  # 退出外层循环

# done = False
# while not done:
#     responses = gdbmi.get_gdb_response(timeout_sec=0.1, raise_error_on_timeout=False)
#     if responses:
#         print(json.dumps(responses, indent=2))
#     else:
#         continue

#     for resp in responses:
#         if resp["type"] == "result" and resp["message"] == "done":
#             print("done")
#             done = True
   

# # # 反向执行（rr 独有）
# # response = gdbmi.write('-exec-reverse-step', timeout_sec=DEFAULT_WRITE_TIMEOUT)
# # print("反向步进:", response)

# # # 获取栈追踪
# # # response = gdbmi.write('-stack-list-frames', timeout_sec=DEFAULT_WRITE_TIMEOUT)
# # # response = gdbmi.write('-stack-info-frame', timeout_sec=DEFAULT_WRITE_TIMEOUT)
# # response = gdbmi.write('backtrace', timeout_sec=DEFAULT_WRITE_TIMEOUT)
# # print("栈帧:", json.dumps(response, indent=2))

# # response = gdbmi.write('backtrace', timeout_sec=DEFAULT_WRITE_TIMEOUT)
# # print("stack frames:", json.dumps(response, indent=2))


# # 退出
# gdbmi.write('-gdb-exit', timeout_sec=DEFAULT_WRITE_TIMEOUT)
