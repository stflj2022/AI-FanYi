#!/usr/bin/env python3
"""
自动任务编排器 - 完全无人值守
自动处理：
- 进度保存
- 额度监控
- 等待重置
- 任务恢复
- 循环执行
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

class AutoOrchestrator:
    """自动任务编排器"""

    def __init__(self, config_file: str = ".claude/auto-config.json"):
        self.config_file = Path(config_file)
        self.progress_dir = Path(".claude")
        self.task_file = self.progress_dir / "current-task.yaml"
        self.context_file = self.progress_dir / "context-summary.md"
        self.quota_file = self.progress_dir / "quota-usage.json"
        self.checkpoint_dir = self.progress_dir / "checkpoints"

        # 创建目录
        self.progress_dir.mkdir(exist_ok=True)
        self.checkpoint_dir.mkdir(exist_ok=True)

        # 加载配置
        self.config = self.load_config()

    def load_config(self) -> Dict:
        """加载配置"""
        default_config = {
            "check_interval": 300,  # 5分钟检查一次
            "quota_threshold": 80,   # 80%额度阈值
            "max_cycles": None,      # 最大循环次数（None=无限）
            "auto_commit": False,    # 自动提交git
            "notification": {
                "enabled": False,
                "webhook": None
            }
        }

        if self.config_file.exists():
            with open(self.config_file) as f:
                user_config = json.load(f)
                default_config.update(user_config)

        return default_config

    def save_config(self):
        """保存配置"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def log(self, message: str, level: str = "INFO"):
        """记录日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        prefix = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌"
        }.get(level, "•")

        print(f"[{timestamp}] {prefix} {message}")

        # 同时写入日志文件
        log_file = self.progress_dir / "orchestrator.log"
        with open(log_file, 'a') as f:
            f.write(f"[{timestamp}] [{level}] {message}\n")

    def check_quota(self) -> Dict:
        """检查额度"""
        if not self.quota_file.exists():
            # 创建初始文件
            with open(self.quota_file, 'w') as f:
                json.dump({
                    "last_reset": datetime.now().isoformat(),
                    "tokens_used": 0,
                    "max_quota": 1000000
                }, f)
            return {"used": 0, "max": 1000000, "percentage": 0}

        with open(self.quota_file) as f:
            data = json.load(f)

        used = data.get("tokens_used", 0)
        max_quota = data.get("max_quota", 1000000)
        percentage = (used / max_quota) * 100

        # 检查是否应该重置
        last_check = datetime.fromisoformat(data.get("last_check", datetime.now().isoformat()))
        elapsed = (datetime.now() - last_check).total_seconds()

        if elapsed >= 5 * 3600:  # 5小时
            self.log("检测到额度重置周期，重置计数", "SUCCESS")
            data["tokens_used"] = 0
            data["last_reset"] = datetime.now().isoformat()
            with open(self.quota_file, 'w') as f:
                json.dump(data, f, indent=2)
            return {"used": 0, "max": max_quota, "percentage": 0}

        return {"used": used, "max": max_quota, "percentage": percentage}

    def estimate_tokens(self, session_start: datetime) -> int:
        """估算会话使用的 tokens"""
        duration_minutes = (datetime.now() - session_start).total_seconds() / 60
        # 假设平均每分钟 5000 tokens
        return int(duration_minutes * 5000)

    def save_checkpoint(self, phase: str, message: str, next_action: str, context: str = ""):
        """保存检查点"""
        checkpoint = {
            "timestamp": datetime.now().isoformat(),
            "phase": phase,
            "message": message,
            "next_action": next_action,
            "quota": self.check_quota()
        }

        # 保存到检查点文件
        checkpoint_file = self.checkpoint_dir / f"checkpoint_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint, f, indent=2)

        # 更新上下文摘要
        with open(self.context_file, 'w') as f:
            f.write(f"# 任务上下文 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## 当前阶段: {phase}\n\n")
            f.write(f"**状态**: {message}\n\n")
            f.write(f"## 下一步\n\n{next_action}\n\n")
            if context:
                f.write(f"## 详细上下文\n\n{context}\n")

        # 更新当前任务文件
        with open(self.task_file, 'w') as f:
            f.write(f"task_id: auto-task\n")
            f.write(f"last_update: {datetime.now().isoformat()}\n")
            f.write(f"status: in_progress\n")
            f.write(f"current_phase:\n")
            f.write(f"  id: {phase}\n")
            f.write(f"  message: {message}\n")
            f.write(f"  completed_at: {datetime.now().isoformat()}\n")
            f.write(f"next_action: {next_action}\n")

        self.log(f"检查点已保存: {phase}", "SUCCESS")

    def generate_resume_instruction(self) -> str:
        """生成恢复指令"""
        instruction = [
            "╔══════════════════════════════════════════════════════════════╗",
            "║              🤖 自动任务恢复指令 🤖                           ║",
            "╚══════════════════════════════════════════════════════════════╝",
            "",
            "@Claude 继续执行自动任务",
            "",
            "══════════════════════════════════════════════════════════════",
            "📋 当前状态",
            "══════════════════════════════════════════════════════════════",
            ""
        ]

        if self.task_file.exists():
            with open(self.task_file) as f:
                instruction.append(f.read())

        if self.context_file.exists():
            instruction.extend([
                "",
                "══════════════════════════════════════════════════════════════",
                "📖 上下文摘要",
                "══════════════════════════════════════════════════════════════",
                "",
                self.context_file.read_text()
            ])

        instruction.extend([
            "",
            "══════════════════════════════════════════════════════════════",
            "🔧 执行指令",
            "══════════════════════════════════════════════════════════════",
            "",
            "请根据上下文继续执行下一步。",
            "",
            "完成后请运行: make task-auto-save PHASE=next-phase MESSAGE='说明'"
        ])

        return "\n".join(instruction)

    def wait_for_reset(self, seconds: int):
        """等待额度重置"""
        if seconds <= 0:
            return

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60

        self.log(f"等待额度重置: {hours}小时{minutes}分钟", "INFO")

        # 创建等待标记
        with open(self.progress_dir / "waiting-for-reset.json", 'w') as f:
            json.dump({
                "start_time": datetime.now().isoformat(),
                "expected_reset": (datetime.now() + timedelta(seconds=seconds)).isoformat(),
                "wait_seconds": seconds
            }, f)

        # 等待（带进度报告）
        elapsed = 0
        while elapsed < seconds:
            sleep_time = min(300, seconds - elapsed)  # 最多睡5分钟
            time.sleep(sleep_time)
            elapsed += sleep_time

            if elapsed % 300 == 0:  # 每5分钟报告
                remaining = seconds - elapsed
                h = remaining // 3600
                m = (remaining % 3600) // 60
                self.log(f"等待中... 剩余 {h}小时{m}分钟", "INFO")

        self.log("额度已重置！", "SUCCESS")

        # 重置后清理
        if self.progress_dir / "waiting-for-reset.json" in self.progress_dir.iterdir():
            (self.progress_dir / "waiting-for-reset.json").unlink()

        # 重置额度计数
        with open(self.quota_file, 'w') as f:
            json.dump({
                "last_reset": datetime.now().isoformat(),
                "tokens_used": 0,
                "max_quota": 1000000
            }, f)

    def get_time_until_reset(self) -> int:
        """获取距离下次重置的秒数"""
        if not self.quota_file.exists():
            return 5 * 3600

        with open(self.quota_file) as f:
            data = json.load(f)

        last_check = datetime.fromisoformat(data.get("last_check", datetime.now().isoformat()))
        elapsed = (datetime.now() - last_check).total_seconds()
        remaining = 5 * 3600 - elapsed

        return max(0, int(remaining))

    def should_checkpoint(self, session_start: datetime) -> bool:
        """判断是否应该保存检查点"""
        quota = self.check_quota()
        return quota["percentage"] >= self.config["quota_threshold"]

    def auto_save(self, phase: str, message: str, next_action: str, context: str = ""):
        """自动保存进度"""
        self.save_checkpoint(phase, message, next_action, context)

        # 保存恢复指令到文件
        resume_file = self.progress_dir / "RESUME_INSTRUCTION.txt"
        with open(resume_file, 'w') as f:
            f.write(self.generate_resume_instruction())

        self.log(f"恢复指令已保存到 {resume_file}", "INFO")

        # 如果启用了自动提交
        if self.config.get("auto_commit"):
            try:
                subprocess.run(["git", "add", "."], check=True, capture_output=True)
                subprocess.run([
                    "git", "commit", "-m",
                    f"[auto-checkpoint] {phase}: {message}"
                ], check=True, capture_output=True)
                self.log("已自动提交到 Git", "SUCCESS")
            except Exception as e:
                self.log(f"Git 提交失败: {e}", "WARNING")

    def send_notification(self, message: str):
        """发送通知（如果配置）"""
        if not self.config.get("notification", {}).get("enabled"):
            return

        webhook = self.config.get("notification", {}).get("webhook")
        if webhook:
            # 这里可以发送到 webhook（如 Telegram、企业微信等）
            self.log(f"通知已发送: {message}", "INFO")

    def run_cycle(self, session_start: datetime, cycle: int) -> bool:
        """执行一个循环周期"""
        self.log(f"=== 循环 {cycle} 开始 ===", "INFO")

        # 检查额度
        quota = self.check_quota()
        self.log(f"当前额度: {quota['percentage']:.1f}%", "INFO")

        if self.should_checkpoint(session_start):
            self.log("额度超过阈值，准备保存并等待重置", "WARNING")

            # 估算使用量
            estimated = self.estimate_tokens(session_start)
            self.log(f"估算已使用: {estimated} tokens", "INFO")

            # 更新额度文件
            with open(self.quota_file) as f:
                data = json.load(f)
            data["tokens_used"] = estimated
            with open(self.quota_file, 'w') as f:
                json.dump(data, f, indent=2)

            # 保存检查点
            self.auto_save(
                phase="quota-checkpoint",
                message=f"额度 {quota['percentage']:.1f}%，自动保存",
                next_action="等待重置后继续任务",
                context=f"当前循环: {cycle}，已估算使用 {estimated} tokens"
            )

            # 等待重置
            wait_time = self.get_time_until_reset()
            if wait_time > 0:
                self.wait_for_reset(wait_time)

            # 重置会话开始时间
            session_start = datetime.now()

        self.log(f"=== 循环 {cycle} 完成 ===", "SUCCESS")
        return True

    def run(self):
        """运行自动编排器"""
        self.log("启动自动任务编排器", "SUCCESS")
        self.log(f"检查间隔: {self.config['check_interval']}秒", "INFO")
        self.log(f"额度阈值: {self.config['quota_threshold']}%", "INFO")

        session_start = datetime.now()
        cycle = 0

        try:
            while True:
                cycle += 1

                # 检查最大循环次数
                if self.config.get("max_cycles") and cycle > self.config["max_cycles"]:
                    self.log(f"达到最大循环次数 {self.config['max_cycles']}，停止", "INFO")
                    break

                # 执行一个周期
                if not self.run_cycle(session_start, cycle):
                    break

                # 等待下次检查
                self.log(f"等待 {self.config['check_interval']} 秒后下次检查...", "INFO")
                time.sleep(self.config["check_interval"])

        except KeyboardInterrupt:
            self.log("收到中断信号，保存进度", "WARNING")
            self.auto_save(
                phase="interrupted",
                message="用户中断",
                next_action="用户手动恢复后继续",
                context=f"已完成 {cycle} 个循环"
            )
        except Exception as e:
            self.log(f"发生错误: {e}", "ERROR")
            self.auto_save(
                phase="error",
                message=f"错误: {e}",
                next_action="检查错误后恢复",
                context=f"循环 {cycle} 时发生"
            )
            raise


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='自动任务编排器')
    parser.add_argument('--config', default='.claude/auto-config.json', help='配置文件路径')
    parser.add_argument('--check', action='store_true', help='只检查额度')
    parser.add_argument('--save', nargs=4, metavar=('PHASE', 'MESSAGE', 'NEXT', 'CONTEXT'),
                       help='保存检查点')
    parser.add_argument('--resume', action='store_true', help='生成恢复指令')
    parser.add_argument('--wait', action='store_true', help='等待额度重置')

    args = parser.parse_args()

    orchestrator = AutoOrchestrator(args.config)

    if args.check:
        quota = orchestrator.check_quota()
        print(f"额度: {quota['percentage']:.1f}% ({quota['used']}/{quota['max']})")
        print(f"距重置: {orchestrator.get_time_until_reset()}秒")

    elif args.save:
        orchestrator.auto_save(args.save[0], args.save[1], args.save[2], args.save[3] or "")

    elif args.resume:
        print(orchestrator.generate_resume_instruction())

    elif args.wait:
        orchestrator.wait_for_reset(orchestrator.get_time_until_reset())

    else:
        orchestrator.run()


if __name__ == '__main__':
    main()
