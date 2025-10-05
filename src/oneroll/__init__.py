"""
OneRoll - High Performance Dice Expression Parser

A dice expression parser implemented in Rust and bound to Python through PyO3.
Supports complex dice expression parsing, various modifiers and mathematical operations.

Main functions:
- Basic Dice Rolling (XdY)
- Mathematical operations (+, -, *, /, ^)
- Modifiers support (!, kh, kl, dh, dl, r, ro)
- Bracket support
- Complete error handling

Example of usage:
# Basic use
import oneroll
result = oneroll.roll("3d6 + 2")
print(result.total) # output total points

# Use the OneRoll class
roller = oneroll.OneRoll()
result = roller.roll("4d6kh3")

# Simple throw
total = oneroll.roll_simple(3, 6)
"""

from typing import Dict, List, Any, Union
from ._core import (
    OneRoll as _OneRoll,
    roll_dice as _roll_dice,
    roll_simple as _roll_simple,
)

__version__ = "1.3.2"
__author__ = "HsiangNianian"
__description__ = "高性能骰子表达式解析器"


# 重新导出主要类和函数，提供更友好的接口
class OneRoll:
    """
    OneRoll 骰子投掷器类

    提供面向对象的骰子投掷接口，支持复杂表达式和各种修饰符。

    示例：
        roller = OneRoll()
        result = roller.roll("3d6 + 2")
        simple_result = roller.roll_simple(3, 6)
        modifier_result = roller.roll_with_modifiers(4, 6, ["kh3"])
    """

    def __init__(self):
        """初始化 OneRoll 实例"""
        self._roller = _OneRoll()

    def roll(self, expression: str) -> Dict[str, Any]:
        """
        解析并计算骰子表达式

        Args:
            expression: 骰子表达式字符串，如 "3d6 + 2", "4d6kh3", "2d6! # 攻击投掷"

        Returns:
            包含以下键的字典：
            - expression: 表达式字符串
            - total: 总点数
            - rolls: 投掷结果列表
            - details: 详细信息
            - comment: 用户注释

        Raises:
            ValueError: 当表达式无效时

        Example:
            result = roller.roll("3d6 + 2")
            print(f"总点数: {result['total']}")
            print(f"详情: {result['details']}")
        """
        return self._roller.roll(expression)

    def roll_simple(self, dice_count: int, dice_sides: int) -> int:
        """
        简单骰子投掷

        Args:
            dice_count: 骰子数量
            dice_sides: 骰子面数

        Returns:
            总点数

        Raises:
            ValueError: 当参数无效时

        Example:
            total = roller.roll_simple(3, 6)  # 投掷 3d6
        """
        return self._roller.roll_simple(dice_count, dice_sides)

    def roll_with_modifiers(
        self, dice_count: int, dice_sides: int, modifiers: List[str]
    ) -> Dict[str, Any]:
        """
        带修饰符的骰子投掷

        Args:
            dice_count: 骰子数量
            dice_sides: 骰子面数
            modifiers: 修饰符列表，如 ["kh3", "!"]

        Returns:
            包含 total, rolls, details 的字典

        Raises:
            ValueError: 当参数或修饰符无效时

        Example:
            result = roller.roll_with_modifiers(4, 6, ["kh3"])  # 4d6kh3
        """
        return self._roller.roll_with_modifiers(dice_count, dice_sides, modifiers)


# 便捷函数
def roll(expression: str) -> Dict[str, Any]:
    """
    解析并计算骰子表达式（便捷函数）

    Args:
        expression: 骰子表达式字符串，支持注释

    Returns:
        投掷结果字典，包含 comment 字段

    Example:
        result = oneroll.roll("3d6 + 2 # 攻击投掷")
        print(result["comment"])  # 输出: "攻击投掷"
    """
    return _roll_dice(expression)


def roll_simple(dice_count: int, dice_sides: int) -> int:
    """
    简单骰子投掷（便捷函数）

    Args:
        dice_count: 骰子数量
        dice_sides: 骰子面数

    Returns:
        总点数

    Example:
        total = oneroll.roll_simple(3, 6)
    """
    return _roll_simple(dice_count, dice_sides)


def roll_multiple(expression: str, times: int) -> List[Dict[str, Any]]:
    """
    多次投掷同一个表达式

    Args:
        expression: 骰子表达式字符串
        times: 投掷次数

    Returns:
        投掷结果列表

    Example:
        results = oneroll.roll_multiple("3d6", 10)
        totals = [r['total'] for r in results]
    """
    return [_roll_dice(expression) for _ in range(times)]


def roll_statistics(expression: str, times: int) -> Dict[str, Union[int, float]]:
    """
    统计多次投掷的结果

    Args:
        expression: 骰子表达式字符串
        times: 投掷次数

    Returns:
        包含统计信息的字典

    Example:
        stats = oneroll.roll_statistics("3d6", 100)
        print(f"平均值: {stats['mean']:.2f}")
    """
    results = roll_multiple(expression, times)
    totals = [r["total"] for r in results]

    return {
        "min": min(totals),
        "max": max(totals),
        "mean": sum(totals) / len(totals),
        "total": sum(totals),
        "count": len(totals),
        "results": totals,
    }


# 常用骰子表达式
class CommonRolls:
    """常用骰子表达式常量"""

    # D&D 常用投掷
    D20 = "1d20"
    D20_ADVANTAGE = "2d20kh1"
    D20_DISADVANTAGE = "2d20kl1"

    # 属性投掷
    ATTRIBUTE_ROLL = "4d6kh3"

    # 伤害投掷
    D6_DAMAGE = "1d6"
    D8_DAMAGE = "1d8"
    D10_DAMAGE = "1d10"
    D12_DAMAGE = "1d12"

    # 生命值
    HIT_POINTS_D6 = "1d6"
    HIT_POINTS_D8 = "1d8"
    HIT_POINTS_D10 = "1d10"
    HIT_POINTS_D12 = "1d12"


# 导出公共接口
__all__ = [
    "OneRoll",
    "roll",
    "roll_simple",
    "roll_multiple",
    "roll_statistics",
    "CommonRolls",
    "__version__",
    "__author__",
    "__description__",
]
