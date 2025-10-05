#!/usr/bin/env python3
"""
OneRoll interactive dice roll program

Supports command line parameters and interactive mode.

Example of usage:
# Direct throw
python -m oneroll "3d6 + 2"

# Interactive mode
python -m oneroll

# Statistical Mode
python -m oneroll --stats "3d6" --times 100
"""

import sys
import argparse
from typing import List, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn

from . import OneRoll, roll, roll_simple, roll_multiple, roll_statistics, CommonRolls
import oneroll

console = Console()


class OneRollCLI:
    """OneRoll command line interface"""

    def __init__(self):
        self.roller = OneRoll()
        self.history: List[Dict[str, Any]] = []

    def print_result(self, result: Dict[str, Any], expression: str = None):
        """Pretty print the dice roll result"""
        if expression is None:
            expression = result.get("expression", "Unknown")

        # Create result panel
        total = result["total"]
        details = result["details"]
        rolls = result["rolls"]

        # Select color based on result value
        if total >= 15:
            color = "green"
        elif total >= 10:
            color = "yellow"
        else:
            color = "red"

        # Build display text
        text = Text()
        text.append(f"🎲 {expression}\n", style="bold blue")
        text.append(f"总点数: ", style="bold")
        text.append(f"{total}", style=f"bold {color}")
        text.append(f"\n详情: {details}", style="white")

        if rolls:
            text.append(f"\n投掷结果: ", style="bold")
            text.append(f"{rolls}", style="cyan")

        # Display comment
        comment = result.get("comment", "")
        if comment:
            text.append(f"\n注释: ", style="bold")
            text.append(f"{comment}", style="italic blue")

        panel = Panel(text, title="Dice Roll Result", border_style=color)
        console.print(panel)

    def print_statistics(self, stats: Dict[str, Any], expression: str):
        """Print statistics information"""
        table = Table(title=f"统计结果: {expression} (投掷 {stats['count']} 次)")
        table.add_column("统计项", style="cyan")
        table.add_column("数值", style="green")

        table.add_row("最小值", str(stats["min"]))
        table.add_row("最大值", str(stats["max"]))
        table.add_row("平均值", f"{stats['mean']:.2f}")
        table.add_row("总和", str(stats["total"]))
        table.add_row("投掷次数", str(stats["count"]))

        console.print(table)

    def print_history(self):
        """Print dice roll history"""
        if not self.history:
            console.print("暂无投掷历史", style="yellow")
            return

        table = Table(title="投掷历史")
        table.add_column("序号", style="cyan")
        table.add_column("表达式", style="green")
        table.add_column("总点数", style="yellow")
        table.add_column("注释", style="blue")
        table.add_column("详情", style="white")

        for i, result in enumerate(self.history[-10:], 1):  # only show last 30 times
            table.add_row(
                str(i),
                result.get("expression", "Unknown"),
                str(result["total"]),
                result.get("comment", ""),
                result["details"],
            )

        console.print(table)

    def show_help(self):
        """show help information"""
        help_text = """
🎲 OneRoll 骰子表达式解析器

支持的表达式格式：
• 基本骰子: 3d6, 1d20, 2d10
• 数学运算: 3d6 + 2, 2d6 * 3, (2d6 + 3) * 2
• 修饰符:
  - ! 爆炸骰子: 2d6!
  - kh 取高: 4d6kh3
  - kl 取低: 4d6kl2
  - dh 丢弃高: 5d6dh1
  - dl 丢弃低: 5d6dl1
  - r 重投: 3d6r1
  - ro 条件重投: 4d6ro1
• 注释: 在表达式末尾使用 # 添加注释

常用命令：
• help - 显示帮助
• history - 显示投掷历史
• stats <表达式> <次数> - 统计投掷
• clear - 清空历史
• quit/exit - 退出程序

常用表达式：
• d20 - 1d20
• advantage - 2d20kh1 (优势)
• disadvantage - 2d20kl1 (劣势)
• attribute - 4d6kh3 (属性投掷)
        """

        console.print(Panel(help_text, title="帮助信息", border_style="blue"))

    def interactive_mode(self):
        """Interactive Mode"""
        console.print(Panel.fit("🎲 OneRoll 交互式掷骰程序", style="bold blue"))
        console.print("输入 'help' 查看帮助，输入 'quit' 退出程序\n")

        while True:
            try:
                user_input = Prompt.ask("🎲 请输入骰子表达式").strip()

                if not user_input:
                    continue

                # handle special command
                if user_input.lower() in ["quit", "exit", "q"]:
                    if Confirm.ask("确定要退出吗？"):
                        break
                    continue

                if user_input.lower() == "help":
                    self.show_help()
                    continue

                if user_input.lower() == "history":
                    self.print_history()
                    continue

                if user_input.lower() == "clear":
                    self.history.clear()
                    console.print("历史已清空", style="green")
                    continue

                if user_input.lower().startswith("stats "):
                    parts = user_input.split()
                    if len(parts) >= 3:
                        expression = parts[1]
                        try:
                            times = int(parts[2])
                            if times > 1000:
                                console.print("统计次数不能超过1000次", style="red")
                                continue

                            with Progress(
                                SpinnerColumn(),
                                TextColumn("[progress.description]{task.description}"),
                                console=console,
                            ) as progress:
                                task = progress.add_task(
                                    f"正在统计 {expression}...", total=None
                                )
                                stats = roll_statistics(expression, times)
                                progress.stop()

                            self.print_statistics(stats, expression)
                        except ValueError:
                            console.print("统计次数必须是数字", style="red")
                        except Exception as e:
                            console.print(f"统计错误: {e}", style="red")
                    else:
                        console.print("用法: stats <表达式> <次数>", style="red")
                    continue

                # resolve regular expression's alias
                expression = self._resolve_expression_alias(user_input)

                # execute roll
                try:
                    result = roll(expression)
                    self.history.append(result)
                    self.print_result(result, user_input)
                except Exception as e:
                    console.print(f"错误: {e}", style="red")

            except KeyboardInterrupt:
                if Confirm.ask("\n确定要退出吗？"):
                    break
            except EOFError:
                break

    def _resolve_expression_alias(self, user_input: str) -> str:
        """resolve regular expression's alias"""
        aliases = {
            "d20": CommonRolls.D20,
            "advantage": CommonRolls.D20_ADVANTAGE,
            "disadvantage": CommonRolls.D20_DISADVANTAGE,
            "attr": CommonRolls.ATTRIBUTE_ROLL,
            "attribute": CommonRolls.ATTRIBUTE_ROLL,
        }

        return aliases.get(user_input.lower(), user_input)

    def run(self, args):
        """run tui mode"""
        if args.tui:
            # start tui
            try:
                from .tui import run_tui

                run_tui()
            except ImportError:
                console.print(
                    "TUI 模式需要安装 textual: pip install textual", style="red"
                )
                sys.exit(1)
            except Exception as e:
                console.print(f"TUI 启动失败: {e}", style="red")
                sys.exit(1)

        elif args.expression:
            # single roll mode
            try:
                result = roll(args.expression)
                self.print_result(result)
            except Exception as e:
                console.print(f"错误: {e}", style="red")
                sys.exit(1)

        elif args.stats:
            # stats mode
            try:
                times = args.times or 100
                if times > 10000:
                    console.print("统计次数不能超过10000次", style="red")
                    sys.exit(1)

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    task = progress.add_task(f"正在统计 {args.stats}...", total=None)
                    stats = roll_statistics(args.stats, times)
                    progress.stop()

                self.print_statistics(stats, args.stats)
            except Exception as e:
                console.print(f"错误: {e}", style="red")
                sys.exit(1)

        else:
            # interactive mode
            self.interactive_mode()


def main():
    parser = argparse.ArgumentParser(
        description="OneRoll 骰子表达式解析器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s "3d6 + 2"              # 单次投掷
  %(prog)s --stats "3d6" --times 100  # 统计模式
  %(prog)s --tui                  # 终端用户界面
  %(prog)s                         # 交互式模式
        """,
    )

    parser.add_argument("expression", nargs="?", help='骰子表达式，如 "3d6 + 2"')

    parser.add_argument("--stats", help="统计模式，指定要统计的表达式")

    parser.add_argument("--times", type=int, default=100, help="统计次数，默认100次")

    parser.add_argument("--version", action="version", version=oneroll.__version__)

    parser.add_argument("--tui", action="store_true", help="启动终端用户界面 (TUI)")

    args = parser.parse_args()

    cli = OneRollCLI()
    cli.run(args)


if __name__ == "__main__":
    main()
