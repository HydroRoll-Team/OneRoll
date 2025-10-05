from typing import Dict, List, Any, Union

DiceResult = Dict[str, Any]
RollHistory = List[DiceResult]
ModifierList = List[str]

def roll_dice(expression: str) -> DiceResult:
    """
    Analyze and calculate dice expressions

    Args:
        expression: Dice expression string, supports the following formats:
        - Basic dice: "3d6", "1d20", "2d10"
        - Mathematical operations: "3d6 + 2", "2d6 * 3", "(2d6 + 3) * 2"
        - Modifiers: "2d6!", "4d6kh3", "5d6dl1", "3d6r1", "4d6ro1"

    Returns:
        A dictionary containing the following keys:
        - expression: str - expression string
        - total: int - Total points
        - rolls: List[List[int]] - List of throw results
        - details: str - details
        - comment: str - User comment

    Raises:
        ValueError: When the expression is invalid

    Example:
        result = roll_dice("3d6 + 2")
        print(result["total"]) # output total points
    """
    ...

def roll_simple(dice_count: int, dice_sides: int) -> int:
    """
    Simple dice throw

    Args:
        dice_count: The number of dice must be greater than 0
        dice_sides: The number of dice faces must be greater than 0

    Returns:
        Total points

    Raises:
        ValueError: When the parameter is invalid

    Example:
        total = roll_simple(3, 6) # Roll 3 6-sided dice
    """
    ...

class OneRoll:
    """
    OneRoll dice thrower category

    Provides an object-oriented dice throwing interface, supporting complex expressions and various modifiers.
    """

    def __init__(self) -> None:
        """
        Initialize OneRoll Object

        Example:
            roller = OneRoll()
        """
        ...

    def roll(self, expression: str) -> DiceResult:
        """
        Analyze and calculate dice expressions

        Args:
            expression: Dice expression string, supports the following formats:
            - Basic dice: "3d6", "1d20", "2d10"
            - Mathematical operations: "3d6 + 2", "2d6 * 3", "(2d6 + 3) * 2"
            - Modifiers: "2d6!", "4d6kh3", "5d6dl1", "3d6r1", "4d6ro1"

        Returns:
            A dictionary containing the following keys:
            - expression: str - expression string
            - total: int - Total points
            - rolls: List[List[int]] - List of throw results
            - details: str - details
            - comment: str - User comment

        Raises:
            ValueError: When the expression is invalid

        Example:
            roller = OneRoll()
            result = roller.roll("3d6 + 2")
            print(f"Total points: {result['total']}")
        """
        ...

    def roll_simple(self, dice_count: int, dice_sides: int) -> int:
        """
        Simple dice throw

        Args:
            dice_count: The number of dice must be greater than 0
            dice_sides: The number of dice faces must be greater than 0

        Returns:
            Total points

        Raises:
            ValueError: When the parameter is invalid

        Example:
            roller = OneRoll()
            total = roller.roll_simple(3, 6) # Throw 3 6-sided dice
        """
        ...

    def roll_with_modifiers(
        self, dice_count: int, dice_sides: int, modifiers: ModifierList
    ) -> DiceResult:
        """
        Dice throw with modifier

        Args:
            dice_count: The number of dice must be greater than 0
            dice_sides: The number of dice faces must be greater than 0
            modifiers: modifier list, supports the following formats:
            - "!" - Explosion dice
            - "r<number>" - Re-submit, such as "r1"
            - "ro<number>" - Conditional re-submission, such as "ro1"
            - "kh<number>" - Take the height, such as "kh3"
            - "kl<number>" - Take the low, such as "kl2"
            - "dh<number>" - discard the height, such as "dh1"
            - "dl<number>" - discard low, such as "dl1"

        Returns:
            A dictionary containing the following keys:
            - total: int - Total points
            - rolls: List[List[int]] - List of throw results
            - details: str - details

        Raises:
            ValueError: When the parameter or modifier is invalid

        Example:
            roller = OneRoll()
            result = roller.roll_with_modifiers(4, 6, ["kh3"]) # 4d6kh3
            print(f"Total points: {result['total']}")
        """
        ...

def is_valid_expression(expression: str) -> bool:
    """
    Check if the expression is valid

    Args:
        expression: The expression string to check

    Returns:
        Return True if the expression is valid, otherwise return False

    Example:
        if is_valid_expression("3d6 + 2"):
        result = roll_dice("3d6 + 2")
    """
    ...

def parse_expression(expression: str) -> Dict[str, Any]:
    """
    Parses expressions but not throwing

    Args:
        expression: The expression string to parse

    Returns:
        Analytical results dictionary

    Raises:
        ValueError: When the expression is invalid
    """
    ...

class RollStatistics:
    """Throw statistics"""

    min: int
    max: int
    mean: float
    total: int
    count: int
    results: List[int]

def roll_multiple(expression: str, times: int) -> RollHistory:
    """
    Throw the same expression multiple times

    Args:
        expression: dice expression string
        times: The number of throws must be greater than 0

    Returns:
        Throw result list

    Raises:
        ValueError: When the parameter is invalid

    Example:
        results = roll_multiple("3d6", 10)
        totals = [r["total"] for r in results]
    """
    ...

def roll_statistics(expression: str, times: int) -> RollStatistics:
    """
    Statistics of multiple throws

    Args:
        expression: dice expression string
        times: The number of throws must be greater than 0

    Returns:
        Object containing statistics

    Raises:
        ValueError: When the parameter is invalid

    Example:
        stats = roll_statistics("3d6", 100)
        print(f"Average: {stats.mean:.2f}")
    """
    ...

class CommonRolls:
    """Commonly used dice expression constants"""

    D20: str
    D20_ADVANTAGE: str
    D20_DISADVANTAGE: str
    ATTRIBUTE_ROLL: str
    D6_DAMAGE: str
    D8_DAMAGE: str
    D10_DAMAGE: str
    D12_DAMAGE: str
    HIT_POINTS_D6: str
    HIT_POINTS_D8: str
    HIT_POINTS_D10: str
    HIT_POINTS_D12: str
