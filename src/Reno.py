import random
import os
import matplotlib.pyplot as plt


class TCPReno:
    def __init__(self, mss=1, rtt=0.1):
        self.cwnd = 1.0
        self.ssthresh = 64.0
        self.dup_ack_count = 0
        self.mss = mss
        self.rtt = rtt
        self.in_fast_recovery = False
        self.time = 0.0
        self.cwnd_history = []
        self.time_history = []
        self.loss_events = []

    def on_ack_received(self, is_duplicate=False, loss_prob=0.05):
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
                self.in_fast_recovery = False
                self.cwnd = self.ssthresh
                return

            if self.cwnd < self.ssthresh:
                self.cwnd += 1
            else:
                self.cwnd += 1.0 / self.cwnd
            self.cwnd = max(self.cwnd, 1.0)

    def on_fast_retransmit(self):
        self.in_fast_recovery = True
        self.ssthresh = max(self.cwnd / 2, 2.0)
        self.cwnd = self.ssthresh + 3
        self.loss_events.append(self.time)

    def on_loss(self):
        self.ssthresh = max(self.cwnd / 2, 2.0)
        self.cwnd = 1.0
        self.dup_ack_count = 0
        self.in_fast_recovery = False
        self.loss_events.append(self.time)

    def simulate(self, duration=30.0, loss_rate=0.03):
        self.time = 0.0
        self.cwnd_history.clear()
        self.time_history.clear()
        self.loss_events.clear()

        while self.time < duration:
            self.cwnd_history.append(self.cwnd)
            self.time_history.append(self.time)

            packets_to_send = int(self.cwnd)
            if packets_to_send == 0:
                self.time += self.rtt
                continue

            for _ in range(packets_to_send):
                self.time += self.rtt / packets_to_send
                self.on_ack_received(is_duplicate=False, loss_prob=loss_rate)

        self.cwnd_history.append(self.cwnd)
        self.time_history.append(self.time)

    def plot(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        save_dir = os.path.join(script_dir, '..', 'out', 'pic')
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, 'tcp_reno_result.png')

        plt.figure(figsize=(12, 6))
        plt.plot(self.time_history, self.cwnd_history, 'b-', linewidth=1.5, label='cwnd')

        if self.loss_events:
            loss_cwnds = []
            for t in self.loss_events:
                idx = min(range(len(self.time_history)), key=lambda i: abs(self.time_history[i] - t))
                loss_cwnds.append(self.cwnd_history[idx])
            plt.scatter(self.loss_events, loss_cwnds, color='red', marker='x', s=80, label='Packet loss')

        plt.xlabel('Time (seconds)')
        plt.ylabel('Congestion Window (cwnd / MSS)')
        plt.title('TCP Reno Congestion Control Simulation')
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(save_path, dpi=150)
        print(f"图片已保存至: {save_path}")
        plt.show()

    def print_stats(self):
        avg_cwnd = sum(self.cwnd_history) / len(self.cwnd_history)
        print(f"模拟时长: {self.time_history[-1]:.2f} 秒")
        print(f"平均拥塞窗口: {avg_cwnd:.2f} MSS")
        print(f"最大拥塞窗口: {max(self.cwnd_history):.2f} MSS")
        print(f"丢包事件次数: {len(self.loss_events)}")


if __name__ == "__main__":
    reno = TCPReno(mss=1, rtt=0.1)
    reno.simulate(duration=40.0, loss_rate=0.05)
    reno.plot()
    reno.print_stats()