#!/usr/bin/env python3
"""
OneRoll 注释功能示例

展示如何使用 OneRoll 的注释功能来标记和记录骰子投掷。
"""

import oneroll
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

def basic_comment_example():
    """基本注释功能示例"""
    console.print(Panel.fit("基本注释功能示例", style="bold blue"))
    
    # 基本注释
    result = oneroll.roll("3d6 + 2 # 攻击投掷")
    console.print(f"表达式: {result['expression']}")
    console.print(f"总点数: {result['total']}")
    console.print(f"注释: {result['comment']}")
    console.print()

def dnd_comment_example():
    """D&D 游戏注释示例"""
    console.print(Panel.fit("D&D 游戏注释示例", style="bold green"))
    
    # 模拟一场 D&D 战斗
    expressions = [
        "1d20 + 5 # 攻击检定",
        "2d6 + 3 # 伤害投掷",
        "1d20 + 3 # 法术豁免检定",
        "4d6kh3 # 力量属性投掷",
        "2d20kh1 # 优势攻击检定",
        "1d4 + 1 # 治疗药水"
    ]
    
    table = Table(title="D&D 战斗记录")
    table.add_column("表达式", style="cyan")
    table.add_column("总点数", style="green")
    table.add_column("注释", style="yellow")
    table.add_column("结果", style="white")
    
    for expr in expressions:
        result = oneroll.roll(expr)
        total = result['total']
        
        # 根据注释类型判断结果
        if "攻击检定" in result['comment']:
            if total >= 15:
                outcome = "命中!"
            else:
                outcome = "未命中"
        elif "伤害投掷" in result['comment']:
            outcome = f"造成 {total} 点伤害"
        elif "豁免检定" in result['comment']:
            if total >= 12:
                outcome = "豁免成功"
            else:
                outcome = "豁免失败"
        elif "属性投掷" in result['comment']:
            outcome = f"属性值: {total}"
        elif "优势" in result['comment']:
            outcome = "优势投掷"
        else:
            outcome = "投掷完成"
        
        table.add_row(
            expr,
            str(total),
            result['comment'],
            outcome
        )
    
    console.print(table)

def rpg_session_example():
    """RPG 会话记录示例"""
    console.print(Panel.fit("RPG 会话记录示例", style="bold magenta"))
    
    # 模拟一个 RPG 会话
    session_log = [
        ("1d20 + 4 # 开锁检定", "尝试打开宝箱"),
        ("3d6 # 宝箱陷阱伤害", "触发陷阱"),
        ("1d20 + 2 # 敏捷豁免", "躲避陷阱"),
        ("2d8 + 2 # 宝箱中的金币", "发现宝藏"),
        ("1d100 # 随机遭遇", "探索洞穴"),
        ("4d6kh3 # 新角色属性", "创建角色")
    ]
    
    for expr, description in session_log:
        result = oneroll.roll(expr)
        console.print(f"[bold]{description}[/bold]")
        console.print(f"  投掷: {expr}")
        console.print(f"  结果: {result['total']}")
        console.print(f"  注释: {result['comment']}")
        console.print()

def complex_expression_comment_example():
    """复杂表达式注释示例"""
    console.print(Panel.fit("复杂表达式注释示例", style="bold red"))
    
    complex_expressions = [
        "2d6 + 3d8 - 5 # 复合伤害计算",
        "(2d6 + 3) * 2 # 暴击伤害",
        "4d6!kh3 # 爆炸骰子属性投掷",
        "6d6dl2kh3 # 复杂修饰符测试",
        "3d6r1 + 2d8ro2 # 重投组合攻击"
    ]
    
    for expr in complex_expressions:
        try:
            result = oneroll.roll(expr)
            console.print(f"[bold cyan]{expr}[/bold cyan]")
            console.print(f"  总点数: [bold green]{result['total']}[/bold green]")
            console.print(f"  注释: [bold yellow]{result['comment']}[/bold yellow]")
            console.print(f"  详情: {result['details']}")
            console.print()
        except Exception as e:
            console.print(f"[red]错误: {expr} - {e}[/red]")
            console.print()

def comment_statistics_example():
    """注释统计示例"""
    console.print(Panel.fit("注释统计示例", style="bold yellow"))
    
    # 统计不同类型的投掷
    attack_rolls = oneroll.roll_multiple("1d20 + 5 # 攻击检定", 10)
    damage_rolls = oneroll.roll_multiple("2d6 + 3 # 伤害投掷", 10)
    
    # 计算攻击命中率
    attack_totals = [r['total'] for r in attack_rolls]
    hit_count = sum(1 for total in attack_totals if total >= 15)
    hit_rate = hit_count / len(attack_totals) * 100
    
    # 计算平均伤害
    damage_totals = [r['total'] for r in damage_rolls]
    avg_damage = sum(damage_totals) / len(damage_totals)
    
    console.print(f"攻击检定统计:")
    console.print(f"  命中率: {hit_rate:.1f}% ({hit_count}/{len(attack_totals)})")
    console.print(f"  平均攻击值: {sum(attack_totals) / len(attack_totals):.1f}")
    console.print()
    
    console.print(f"伤害投掷统计:")
    console.print(f"  平均伤害: {avg_damage:.1f}")
    console.print(f"  最小伤害: {min(damage_totals)}")
    console.print(f"  最大伤害: {max(damage_totals)}")
    console.print()

def error_handling_example():
    """错误处理示例"""
    console.print(Panel.fit("错误处理示例", style="bold red"))
    
    # 测试各种边界情况
    test_cases = [
        "3d6 # 正常注释",
        "3d6 #",  # 空注释
        "3d6",    # 无注释
        "3d6 # 这是一个很长的注释，用来测试长注释的显示效果",
        "3d6 # 中文注释测试",
        "3d6 # 特殊字符: !@#$%^&*()",
    ]
    
    for expr in test_cases:
        try:
            result = oneroll.roll(expr)
            comment = result.get('comment', '')
            if comment:
                console.print(f"✅ {expr}")
                console.print(f"   注释: '{comment}'")
            else:
                console.print(f"✅ {expr} (无注释)")
        except Exception as e:
            console.print(f"❌ {expr} - 错误: {e}")
        console.print()

def main():
    """主函数"""
    console.print(Panel.fit("OneRoll 注释功能示例", style="bold blue"))
    console.print("展示如何使用 # 在骰子表达式中添加注释\n")
    
    basic_comment_example()
    dnd_comment_example()
    rpg_session_example()
    complex_expression_comment_example()
    comment_statistics_example()
    error_handling_example()
    
    console.print(Panel.fit("示例完成！注释功能让骰子投掷更有意义！", style="bold green"))

if __name__ == "__main__":
    main()
