"""
OneRoll - High Performance Dice Expression Parser

A dice expression parser implemented in Rust and bound to Python through PyO3.
Supports complex dice expression parsing, various modifiers and mathematical operations.

Main functions:
- Basic Dice Rolling (XdY)
- Ordered Programs separated by semicolons
- Mathematical operations (+, -, *, /, ^)
- Modifiers support (!, kh, kl, dh, dl, r, ro)
- Bracket support
- Complete error handling

Example of usage:
# Basic use
import oneroll
result = oneroll.roll("3d6 + 2")
print(result.total) # output total points

# Execute a Program
program = oneroll.run("1d20 + 5; 2d6 # encounter")
print([item["total"] for item in program["results"]])

# Use the OneRoll class
roller = oneroll.OneRoll()
result = roller.roll("4d6kh3")

# Simple throw
total = oneroll.roll_simple(3, 6)
"""

import copy
import json
from typing import Any, Callable, Dict, List, NoReturn, Optional, Type, TypeVar, Union

from ._core import (
    OneRoll as _OneRoll,
    ResourcePolicy as _ResourcePolicy,
    __version__,
    roll_dice as _roll_dice,
    roll_simple as _roll_simple,
    run_program as _run_program,
)

__author__ = "HsiangNianian"
__description__ = "高性能骰子表达式解析器"

_T = TypeVar("_T")


class Span:
    """Half-open UTF-8 byte range into the submitted source."""

    def __init__(self, start_byte: int, end_byte: int) -> None:
        self.start_byte = start_byte
        self.end_byte = end_byte

    def to_dict(self) -> Dict[str, int]:
        return {"start_byte": self.start_byte, "end_byte": self.end_byte}


class RandomDescriptor:
    """Replay metadata for a request-scoped random stream."""

    def __init__(self, payload: Dict[str, Any]) -> None:
        self.algorithm = str(payload["algorithm"])
        self.seed = str(payload["seed"])
        self.rng_words = int(payload["rng_words"])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "seed": self.seed,
            "rng_words": self.rng_words,
        }


class BatchFailureDescriptor:
    """Root batch context attached to an atomic sample failure."""

    def __init__(self, payload: Dict[str, Any]) -> None:
        self.algorithm = str(payload["algorithm"])
        self.seed = str(payload["seed"])
        self.samples = int(payload["samples"])
        sample_index = payload.get("sample_index")
        self.sample_index = None if sample_index is None else int(sample_index)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "seed": self.seed,
            "samples": self.samples,
            "sample_index": self.sample_index,
        }


class OneRollError(ValueError):
    """Base exception carrying the RFC-0003 structured error vocabulary."""

    def __init__(
        self, payload: Dict[str, Any], display_message: Optional[str] = None
    ) -> None:
        self._payload = copy.deepcopy(payload)
        self.phase = str(payload["phase"])
        self.code = str(payload["code"])
        self.message = str(payload["message"])

        span = payload.get("span")
        self.span = (
            None
            if span is None
            else Span(int(span["start_byte"]), int(span["end_byte"]))
        )
        self.resource = payload.get("resource")
        self.used = payload.get("used")
        self.requested = payload.get("requested")
        self.limit = payload.get("limit")
        random = payload.get("random")
        self.random = None if random is None else RandomDescriptor(random)
        batch = payload.get("batch")
        self.batch = None if batch is None else BatchFailureDescriptor(batch)
        self.expected = tuple(str(item) for item in payload.get("expected", ()))
        self.replacement = payload.get("replacement")
        super().__init__(display_message or f"[{self.code}] {self.message}")

    def to_dict(self) -> Dict[str, Any]:
        """Return the inner RFC-0003 ExecutionError object."""
        return copy.deepcopy(self._payload)

    def to_envelope(self) -> Dict[str, Any]:
        return {
            "schema_version": "2.0",
            "kind": "error",
            "error": self.to_dict(),
        }


class ParseError(OneRollError):
    pass


class ValidationError(OneRollError):
    pass


class EvaluationError(OneRollError):
    pass


class ResourceLimitError(EvaluationError):
    pass


class RandomError(EvaluationError):
    pass


class ArithmeticEvaluationError(EvaluationError):
    pass


class CancellationError(OneRollError):
    pass


class DeadlineExceededError(CancellationError):
    pass


def _exception_class(payload: Dict[str, Any]) -> Type[OneRollError]:
    phase = payload["phase"]
    code = str(payload["code"])
    if phase == "parse":
        return ParseError
    if code == "execution.deadline_exceeded":
        return DeadlineExceededError
    if phase == "cancel":
        return CancellationError
    if code.startswith("limit."):
        return ResourceLimitError
    if code.startswith("random."):
        return RandomError
    if code.startswith("arithmetic."):
        return ArithmeticEvaluationError
    if phase == "validate":
        return ValidationError
    return EvaluationError


def _raise_structured(core_error: ValueError) -> NoReturn:
    encoded = getattr(core_error, "_oneroll_error_json", None)
    if not isinstance(encoded, str):
        raise core_error
    envelope = json.loads(encoded)
    payload = envelope["error"]
    raise _exception_class(payload)(payload, str(core_error)) from None


def _call_core(operation: Callable[..., _T], *args: Any) -> _T:
    try:
        return operation(*args)
    except ValueError as error:
        _raise_structured(error)


class ResourcePolicy:
    """Immutable resource limits with structured validation failures."""

    def __init__(self, inner: Optional[_ResourcePolicy] = None) -> None:
        self._inner = inner or _ResourcePolicy()

    def with_limit(self, name: str, limit: int) -> "ResourcePolicy":
        return ResourcePolicy(_call_core(self._inner.with_limit, name, limit))

    def limits(self) -> Dict[str, int]:
        return self._inner.limits()

    def hard_limits(self) -> Dict[str, int]:
        return self._inner.hard_limits()


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

    def __init__(self, policy: Optional[ResourcePolicy] = None) -> None:
        """初始化 OneRoll 实例"""
        self._roller = _OneRoll(None if policy is None else policy._inner)

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
        return _call_core(self._roller.roll, expression)

    def run(self, program: str) -> Dict[str, Any]:
        """Execute a semicolon-separated program in order."""
        return _call_core(self._roller.run, program)

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
        return _call_core(self._roller.roll_simple, dice_count, dice_sides)

    def roll_multiple(self, expression: str, times: int) -> List[Dict[str, Any]]:
        """Roll an expression repeatedly under one shared request budget."""
        if times <= 0:
            raise ValidationError(
                {
                    "phase": "validate",
                    "code": "input.invalid_batch_samples",
                    "message": "times must be greater than zero",
                }
            )
        return _call_core(self._roller.roll_multiple, expression, times)

    def roll_statistics(
        self, expression: str, times: int
    ) -> Dict[str, Union[int, float, List[int]]]:
        """Calculate statistics under one shared request budget."""
        results = self.roll_multiple(expression, times)
        totals = [result["total"] for result in results]
        return {
            "min": min(totals),
            "max": max(totals),
            "mean": sum(totals) / len(totals),
            "total": sum(totals),
            "count": len(totals),
            "results": totals,
        }

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
        return _call_core(
            self._roller.roll_with_modifiers, dice_count, dice_sides, modifiers
        )


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
    return _call_core(_roll_dice, expression)


def run(program: str) -> Dict[str, Any]:
    """Execute one or more semicolon-separated instructions."""
    return _call_core(_run_program, program)


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
    return _call_core(_roll_simple, dice_count, dice_sides)


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
    return OneRoll().roll_multiple(expression, times)


def roll_statistics(
    expression: str, times: int
) -> Dict[str, Union[int, float, List[int]]]:
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
    return OneRoll().roll_statistics(expression, times)


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
    "ResourcePolicy",
    "roll",
    "run",
    "roll_simple",
    "roll_multiple",
    "roll_statistics",
    "CommonRolls",
    "__version__",
    "__author__",
    "__description__",
]
