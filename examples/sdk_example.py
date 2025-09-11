#!/usr/bin/env python3
"""
OneRoll SDK 使用示例

展示如何使用 OneRoll 作为 Python SDK 进行骰子投掷。
"""

import oneroll
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

def basic_usage_example():
    """基本使用示例"""
    console.print(Panel.fit("基本使用示例", style="bold blue"))
    
    # 使用便捷函数
    result = oneroll.roll("3d6 + 2")
    console.print(f"3d6 + 2 = {result['total']}")
    
    # 使用 OneRoll 类
    roller = oneroll.OneRoll()
    result = roller.roll("4d6kh3")
    console.print(f"4d6kh3 = {result['total']}")
    
    # 简单投掷
    total = oneroll.roll_simple(2, 10)
    console.print(f"2d10 = {total}")

def dnd_example():
    """D&D 游戏示例"""
    console.print(Panel.fit("D&D 游戏示例", style="bold green"))
    
    roller = oneroll.OneRoll()
    
    # 属性投掷
    attr_result = roller.roll(oneroll.CommonRolls.ATTRIBUTE_ROLL)
    console.print(f"属性投掷 (4d6kh3): {attr_result['total']}")
    
    # 攻击投掷
    attack_roll = roller.roll("1d20 + 5")
    console.print(f"攻击投掷 (1d20 + 5): {attack_roll['total']}")
    
    # 伤害投掷
    damage_roll = roller.roll("2d6 + 3")
    console.print(f"伤害投掷 (2d6 + 3): {damage_roll['total']}")
    
    # 优势/劣势投掷
    advantage_roll = roller.roll(oneroll.CommonRolls.D20_ADVANTAGE)
    console.print(f"优势投掷 (2d20kh1): {advantage_roll['total']}")

def statistics_example():
    """统计示例"""
    console.print(Panel.fit("统计示例", style="bold yellow"))
    
    # 多次投掷统计
    stats = oneroll.roll_statistics("3d6", 100)
    
    table = Table(title="3d6 投掷统计 (100次)")
    table.add_column("统计项", style="cyan")
    table.add_column("数值", style="green")
    
    table.add_row("最小值", str(stats['min']))
    table.add_row("最大值", str(stats['max']))
    table.add_row("平均值", f"{stats['mean']:.2f}")
    table.add_row("总和", str(stats['total']))
    
    console.print(table)

def modifier_example():
    """修饰符示例"""
    console.print(Panel.fit("修饰符示例", style="bold magenta"))
    
    roller = oneroll.OneRoll()
    
    # 爆炸骰子
    explode_result = roller.roll("2d6!")
    console.print(f"爆炸骰子 (2d6!): {explode_result['total']}")
    
    # 取高
    keep_high_result = roller.roll("4d6kh3")
    console.print(f"取高 (4d6kh3): {keep_high_result['total']}")
    
    # 取低
    keep_low_result = roller.roll("4d6kl2")
    console.print(f"取低 (4d6kl2): {keep_low_result['total']}")
    
    # 丢弃高
    drop_high_result = roller.roll("5d6dh1")
    console.print(f"丢弃高 (5d6dh1): {drop_high_result['total']}")
    
    # 重投
    reroll_result = roller.roll("3d6r1")
    console.print(f"重投 (3d6r1): {reroll_result['total']}")

def complex_expression_example():
    """复杂表达式示例"""
    console.print(Panel.fit("复杂表达式示例", style="bold red"))
    
    roller = oneroll.OneRoll()
    
    expressions = [
        "2d6 + 3d8 - 5",
        "(2d6 + 3) * 2",
        "4d6!kh3",
        "6d6dl2kh3",
        "3d6r1 + 2d8ro2",
        "10d10kh1",
        "2d20kh1 + 5"
    ]
    
    for expr in expressions:
        try:
            result = roller.roll(expr)
            console.print(f"{expr:15} = {result['total']:2d}")
        except Exception as e:
            console.print(f"{expr:15} = 错误: {e}")

def error_handling_example():
    """错误处理示例"""
    console.print(Panel.fit("错误处理示例", style="bold red"))
    
    invalid_expressions = [
        "0d6",
        "3d0",
        "d6",
        "3d",
        "3d6 / 0",
        "invalid"
    ]
    
    for expr in invalid_expressions:
        try:
            result = oneroll.roll(expr)
            console.print(f"{expr:15} = {result['total']}")
        except Exception as e:
            console.print(f"{expr:15} = 错误: {e}")

def main():
    """主函数"""
    console.print(Panel.fit("OneRoll SDK 使用示例", style="bold blue"))
    
    basic_usage_example()
    console.print()
    
    dnd_example()
    console.print()
    
    statistics_example()
    console.print()
    
    modifier_example()
    console.print()
    
    complex_expression_example()
    console.print()
    
    error_handling_example()
    
    console.print(Panel.fit("示例完成！", style="bold green"))

if __name__ == "__main__":
    main()
