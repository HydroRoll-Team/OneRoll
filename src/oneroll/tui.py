#!/usr/bin/env python3
"""
OneRoll Terminal User Interface (TUI)

An interactive dice roll interface created using textual.
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Input, Button, Static, DataTable, Tabs, Tab
from textual.reactive import reactive
from textual.message import Message
from typing import List, Dict, Any
import json
from datetime import datetime

from . import OneRoll, roll, roll_statistics, CommonRolls


class RollResult(Message):
    """Throw result message"""

    def __init__(self, result: Dict[str, Any], expression: str) -> None:
        self.result = result
        self.expression = expression
        super().__init__()


class ExpressionInput(Input):
    """Expression input box"""

    def __init__(self) -> None:
        super().__init__(
            placeholder="输入骰子表达式，如 3d6 + 2", id="expression_input"
        )

    def on_key(self, event) -> None:
        if event.key == "enter":
            self.post_message(RollResult(roll(self.value), self.value))
            self.value = ""


class QuickRollButton(Button):
    """Quick Throw Button"""

    def __init__(self, label: str, expression: str) -> None:
        self.expression = expression
        super().__init__(label, id=f"quick_{expression}")

    def on_button_pressed(self) -> None:
        self.post_message(RollResult(roll(self.expression), self.expression))


class RollHistory(DataTable):
    """Throw History Table"""

    def __init__(self) -> None:
        super().__init__()
        self.add_columns("时间", "表达式", "总点数", "详情")

    def add_roll(self, result: Dict[str, Any], expression: str) -> None:
        """Add throw record"""
        time_str = datetime.now().strftime("%H:%M:%S")
        self.add_row(time_str, expression, str(result["total"]), result["details"])
        # keep table at bottom
        self.scroll_end()


class StatisticsPanel(Static):
    """Statistics Panel"""

    def __init__(self) -> None:
        super().__init__("统计功能", id="stats_panel")

    def show_statistics(self, expression: str, times: int = 100) -> None:
        """Show statistics information"""
        try:
            stats = roll_statistics(expression, times)
            stats_text = f"""
统计结果: {expression} (投掷 {stats["count"]} 次)

最小值: {stats["min"]}
最大值: {stats["max"]}
平均值: {stats["mean"]:.2f}
总和: {stats["total"]}
            """
            self.update(stats_text)
        except Exception as e:
            self.update(f"统计错误: {e}")


class RollDisplay(Static):
    """The throwing result shows"""

    def __init__(self) -> None:
        super().__init__("等待投掷...", id="roll_display")

    def show_result(self, result: Dict[str, Any], expression: str) -> None:
        """Display throwing result"""
        total = result["total"]
        details = result["details"]
        rolls = result["rolls"]

        # a kind of color selection based on result
        if total >= 15:
            color = "green"
        elif total >= 10:
            color = "yellow"
        else:
            color = "red"

        display_text = f"""[bold blue]🎲 {expression}[/bold blue]

[bold]总点数:[/bold] [bold {color}]{total}[/bold {color}]
[bold]详情:[/bold] {details}

[bold]投掷结果:[/bold] {rolls}"""

        # show the comment
        comment = result.get("comment", "")
        if comment:
            display_text += (
                f"\n\n[bold]注释:[/bold] [italic blue]{comment}[/italic blue]"
            )

        self.update(display_text)


class OneRollTUI(App):
    """OneRoll 终端用户界面"""

    CSS = """
    Screen {
        layout: vertical;
    }
    
    #expression_input {
        margin: 1;
    }
    
    #roll_display {
        height: 8;
        border: solid $primary;
        margin: 1;
        padding: 1;
    }
    
    #stats_panel {
        height: 8;
        border: solid $secondary;
        margin: 1;
        padding: 1;
    }
    
    #history_table {
        height: 10;
        margin: 1;
    }
    
    .quick_buttons {
        height: 3;
        margin: 1;
    }
    
    Button {
        margin: 1;
    }
    """

    def compose(self) -> ComposeResult:
        """UI components"""
        yield Header()

        with Container():
            yield ExpressionInput()

            with Horizontal(classes="quick_buttons"):
                yield QuickRollButton("D20", CommonRolls.D20)
                yield QuickRollButton("优势", CommonRolls.D20_ADVANTAGE)
                yield QuickRollButton("劣势", CommonRolls.D20_DISADVANTAGE)
                yield QuickRollButton("属性", CommonRolls.ATTRIBUTE_ROLL)
                yield QuickRollButton("3D6", "3d6")
                yield QuickRollButton("2D6", "2d6")

            yield RollDisplay()

            with Tabs():
                with Tab("历史记录", id="history_tab"):
                    yield RollHistory(id="history_table")

                with Tab("统计", id="stats_tab"):
                    yield StatisticsPanel()

        yield Footer()

    def on_mount(self) -> None:
        """Initialization during interface mount"""
        self.title = "OneRoll 骰子投掷器"
        self.sub_title = "高性能骰子表达式解析器"

        # Set focus to the input box
        self.query_one(ExpressionInput).focus()

    def on_roll_result(self, message: RollResult) -> None:
        # display result
        roll_display = self.query_one(RollDisplay)
        roll_display.show_result(message.result, message.expression)

        # add history
        history_table = self.query_one(RollHistory)
        history_table.add_roll(message.result, message.expression)

    def on_key(self, event) -> None:
        if event.key == "ctrl+q":
            self.exit()
        elif event.key == "ctrl+h":
            self.show_help()
        elif event.key == "ctrl+s":
            self.show_statistics()

    def show_help(self) -> None:
        help_text = """
OneRoll 骰子投掷器

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

快捷键：
• Ctrl+Q - 退出程序
• Ctrl+H - 显示帮助
• Ctrl+S - 显示统计
• Enter - 执行投掷
        """

        self.notify(help_text, title="帮助信息", timeout=10)

    def show_statistics(self) -> None:
        self.notify("统计功能开发中...", title="统计")


def run_tui():
    app = OneRollTUI()
    app.run()


if __name__ == "__main__":
    run_tui()
