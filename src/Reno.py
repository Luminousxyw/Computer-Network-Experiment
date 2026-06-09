"""
TCP Reno 拥塞控制算法模拟器
模拟慢启动、拥塞避免、快速重传、快速恢复
"""

import random
import matplotlib.pyplot as plt

class TCPReno:
    def __init__(self, mss=1, rtt=0.1):
        self.cwnd = 1.0              # 拥塞窗口 (单位: MSS)
        self.ssthresh = 64.0         # 慢启动阈值
        self.dup_ack_count = 0       # 连续重复ACK计数
        self.mss = mss
        self.rtt = rtt
        self.in_fast_recovery = False
        self.time = 0.0

        # 记录数据
        self.cwnd_history = []
        self.time_history = []
        self.loss_events = []        # 丢包发生的时间点

    def on_ack_received(self, is_duplicate=False, loss_prob=0.05):
        """处理一个ACK到达事件"""
        # 随机丢包模拟拥塞
        if random.random() < loss_prob:
            self.on_loss()
            return

        if is_duplicate:
            self.dup_ack_count += 1
            if self.dup_ack_count == 3 and not self.in_fast_recovery:
                self.on_fast_retransmit()
        else:
            self.dup_ack_count = 0
            if self.in_fast_recovery:
                # 快速恢复阶段收到新ACK -> 退出快速恢复
                self.in_fast_recovery = False
                self.cwnd = self.ssthresh
                return

            if self.cwnd < self.ssthresh:
                # 慢启动
                self.cwnd += 1
            else:
                # 拥塞避免 (加性增)
                self.cwnd += 1.0 / self.cwnd

            self.cwnd = max(self.cwnd, 1.0)

    def on_fast_retransmit(self):
        """快速重传 + 快速恢复"""
        self.in_fast_recovery = True
        self.ssthresh = max(self.cwnd / 2, 2.0)
        self.cwnd = self.ssthresh + 3      # Reno经典做法
        self.loss_events.append(self.time)

    def on_loss(self):
        """超时丢包 -> 进入慢启动"""
        self.ssthresh = max(self.cwnd / 2, 2.0)
        self.cwnd = 1.0
        self.dup_ack_count = 0
        self.in_fast_recovery = False
        self.loss_events.append(self.time)

    def simulate(self, duration=30.0, loss_rate=0.03):
        """模拟传输过程"""
        self.time = 0.0
        self.cwnd_history = []
        self.time_history = []
        self.loss_events = []

        while self.time < duration:
            self.cwnd_history.append(self.cwnd)
            self.time_history.append(self.time)

            packets_to_send = int(self.cwnd)
            if packets_to_send == 0:
                self.time += self.rtt
                continue

            for _ in range(packets_to_send):
                # 每个包的传输时间近似为 RTT / cwnd
                self.time += self.rtt / packets_to_send
                # 模拟收到ACK（每个包对应一个ACK）
                self.on_ack_received(is_duplicate=False, loss_prob=loss_rate)

        # 确保最后一个时间点被记录
        self.cwnd_history.append(self.cwnd)
        self.time_history.append(self.time)

    def plot(self):
        """绘制拥塞窗口曲线"""
        plt.figure(figsize=(12, 6))
        plt.plot(self.time_history, self.cwnd_history, 'b-', linewidth=1.5, label='cwnd')

        # 标记丢包事件
        if self.loss_events:
            loss_cwnds = []
            for t in self.loss_events:
                # 找到最接近的时间点对应的cwnd
                idx = min(range(len(self.time_history)), key=lambda i: abs(self.time_history[i] - t))
                loss_cwnds.append(self.cwnd_history[idx])
            plt.scatter(self.loss_events, loss_cwnds, color='red', marker='x', s=80, label='Packet loss')

        plt.xlabel('Time (seconds)')
        plt.ylabel('Congestion Window (cwnd / MSS)')
        plt.title('TCP Reno Congestion Control Simulation')
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig('tcp_reno_result.png', dpi=150)
        plt.show()

    def print_stats(self):
        """打印统计信息"""
        avg_cwnd = sum(self.cwnd_history) / len(self.cwnd_history)
        print(f"模拟时长: {self.time_history[-1]:.2f} 秒")
        print(f"平均拥塞窗口: {avg_cwnd:.2f} MSS")
        print(f"最大拥塞窗口: {max(self.cwnd_history):.2f} MSS")
        print(f"丢包事件次数: {len(self.loss_events)}")


if __name__ == "__main__":
    # 创建Reno对象并运行模拟
    reno = TCPReno(mss=1, rtt=0.1)
    reno.simulate(duration=40.0, loss_rate=0.05)
    reno.plot()
    reno.print_stats()