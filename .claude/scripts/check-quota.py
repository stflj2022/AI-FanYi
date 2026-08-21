#!/usr/bin/env python3
"""
智谱 API 额度监控工具
监控额度使用情况，预测重置时间，建议任务暂停点
"""

import json
import os
import sys
from datetime import datetime, timedelta

class QuotaMonitor:
    def __init__(self):
        self.quota_file = ".claude/quota-usage.json"
        self.reset_interval_hours = 5
        self.max_tokens_per_cycle = 1000000  # 假设每5小时约1M tokens
        self.load_data()

    def load_data(self):
        """加载额度使用数据"""
        if os.path.exists(self.quota_file):
            with open(self.quota_file, 'r') as f:
                data = json.load(f)
                self.last_reset = datetime.fromisoformat(data['last_reset'])
                self.tokens_used = data.get('tokens_used', 0)
                self.last_check = datetime.fromisoformat(data['last_check'])
        else:
            self.last_reset = datetime.now()
            self.tokens_used = 0
            self.last_check = datetime.now()

    def save_data(self):
        """保存额度使用数据"""
        os.makedirs(os.path.dirname(self.quota_file), exist_ok=True)
        with open(self.quota_file, 'w') as f:
            json.dump({
                'last_reset': self.last_reset.isoformat(),
                'tokens_used': self.tokens_used,
                'last_check': datetime.now().isoformat(),
                'max_quota': self.max_tokens_per_cycle
            }, f, indent=2)

    def get_time_until_reset(self):
        """计算距离下次重置的时间"""
        elapsed = datetime.now() - self.last_reset
        reset_time = self.last_reset + timedelta(hours=self.reset_interval_hours)
        remaining = reset_time - datetime.now()
        return remaining

    def estimate_tokens_used(self, session_duration_minutes=None):
        """估算已使用的 tokens"""
        if session_duration_minutes:
            # 假设平均每分钟使用约 5K tokens（包括输入输出）
            estimated = session_duration_minutes * 5000
            return min(estimated, self.max_tokens_per_cycle)
        return self.tokens_used

    def get_status(self):
        """获取当前状态"""
        time_until_reset = self.get_time_until_reset()
        remaining_tokens = self.max_tokens_per_cycle - self.tokens_used
        usage_ratio = self.tokens_used / self.max_tokens_per_cycle

        return {
            'last_reset': self.last_reset,
            'next_reset': self.last_reset + timedelta(hours=self.reset_interval_hours),
            'time_until_reset': time_until_reset,
            'tokens_used': self.tokens_used,
            'tokens_remaining': remaining_tokens,
            'usage_ratio': usage_ratio,
            'usage_percentage': usage_ratio * 100
        }

    def print_status(self):
        """打印状态信息"""
        status = self.get_status()

        print("=" * 50)
        print("智谱 API 额度监控")
        print("=" * 50)
        print()

        # 时间信息
        print("📅 时间信息:")
        print(f"  上次重置: {status['last_reset'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  下次重置: {status['next_reset'].strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # 剩余时间
        hours, remainder = divmod(status['time_until_reset'].seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        print("⏱️  时间剩余:")
        print(f"  距离重置: {hours} 小时 {minutes} 分钟")
        print()

        # 额度信息
        print("💰 额度使用:")
        print(f"  已使用: {status['tokens_used']:,} tokens")
        print(f"  剩余: {status['tokens_remaining']:,} tokens")
        print(f"  使用率: {status['usage_percentage']:.1f}%")
        print()

        # 状态指示
        if status['usage_percentage'] < 50:
            print("✅ 状态: 额度充足，可以继续任务")
        elif status['usage_percentage'] < 80:
            print("⚠️  状态: 额度使用过半，建议准备保存进度")
        elif status['usage_percentage'] < 95:
            print("⚠️  状态: 额度即将耗尽，建议立即保存进度并等待重置")
        else:
            print("🚨 状态: 额度已耗尽，请等待重置")
        print()

        # 建议
        if status['time_until_reset'].total_seconds() < 1800:  # 少于30分钟
            print("💡 建议: 重置即将到来，可以考虑等待重置后再开始新任务")

        print("=" * 50)

    def record_usage(self, tokens):
        """记录 token 使用"""
        self.tokens_used += tokens
        self.save_data()

    def should_pause(self):
        """判断是否应该暂停任务"""
        status = self.get_status()
        return status['usage_percentage'] > 80 or status['time_until_reset'].total_seconds() < 600

    def save_progress_if_needed(self):
        """如果需要则保存进度"""
        if self.should_pause():
            print()
            print("⚠️  检测到额度不足或即将重置")
            print()
            print("建议操作:")
            print("  1. 保存当前进度")
            print("  2. 等待额度重置")
            print("  3. 恢复任务继续执行")
            print()
            return True
        return False


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='智谱 API 额度监控')
    parser.add_argument('--json', action='store_true', help='以 JSON 格式输出')
    parser.add_argument('--check-only', action='store_true', help='只检查是否需要暂停')
    parser.add_argument('--record', type=int, metavar='TOKENS', help='记录 token 使用量')

    args = parser.parse_args()

    monitor = QuotaMonitor()

    if args.record:
        monitor.record_usage(args.record)
        print(f"✓ 已记录使用 {args.record:,} tokens")
        monitor.print_status()
    elif args.check_only:
        if monitor.save_progress_if_needed():
            sys.exit(1)  # 需要暂停
        else:
            print("✅ 额度充足，可以继续")
            sys.exit(0)
    elif args.json:
        status = monitor.get_status()
        print(json.dumps(status, indent=2, default=str))
    else:
        monitor.print_status()


if __name__ == '__main__':
    main()
