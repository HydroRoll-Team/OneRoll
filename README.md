# OneRoll - 高性能骰子表达式解析器

一个用 Rust 实现并通过 PyO3 绑定到 Python 的骰子表达式解析器。支持复杂的骰子表达式解析、各种修饰符和数学运算。

## 特性

- 🚀 **高性能**: 使用 Rust 实现核心逻辑，性能优异
- 🎲 **功能丰富**: 支持各种骰子表达式和修饰符
- 🐍 **Python 友好**: 提供清晰的 Python 接口
- 🎨 **美观界面**: 支持 Rich 和 Textual 的交互式界面
- 📊 **统计功能**: 内置统计和分析功能
- 🛠️ **易于使用**: 支持命令行、交互式和 TUI 模式

## 安装

### 从源码构建

```bash
# 克隆仓库
git clone https://github.com/HydroRoll-Team/oneroll.git
cd oneroll

# 安装 maturin
pip install maturin

# 构建并安装
maturin develop
```

### 安装 Python 依赖 (可选)

```bash
pip install rich textual
```

## 快速开始

### 作为 Python SDK 使用

```python
import oneroll

# 基本使用
result = oneroll.roll("3d6 + 2")
print(f"总点数: {result['total']}")

# 使用 OneRoll 类
roller = oneroll.OneRoll()
result = roller.roll("4d6kh3")
print(f"4d6kh3 = {result['total']}")

# 简单投掷
total = oneroll.roll_simple(3, 6)
print(f"3d6 = {total}")
```

### 命令行使用

```bash
# 单次投掷
python -m oneroll "3d6 + 2"

# 统计模式
python -m oneroll --stats "3d6" --times 100

# 交互式模式
python -m oneroll

# 终端用户界面 (TUI)
python -m oneroll --tui
```

## 支持的表达式

### 基本骰子
- `3d6` - 投掷3个6面骰子
- `1d20` - 投掷1个20面骰子
- `2d10` - 投掷2个10面骰子

### 数学运算
- `3d6 + 2` - 骰子结果加常数
- `2d6 * 3` - 骰子结果乘以常数
- `(2d6 + 3) * 2` - 括号和复合运算

### 修饰符
- `!` / `e` - 爆炸骰子: `2d6!` 或 `2d6e`
- `KX` - 爆炸并取高X个: `4d6K3` 等价 `4d6!kh3`
- `khX` / `kX` - 取高: `4d6kh3` 或 `4d6k3`
- `klX` - 取低: `4d6kl2`
- `dhX` - 丢弃高: `5d6dh1`
- `dlX` - 丢弃低: `5d6dl1`
- `rX` - 重投: `3d6r1` (重投小于等于1的结果)
- `roX` - 条件重投: `4d6ro1` (条件重投一次)
- `u` - 去重: `4d6u` (相同点数只计一次)
- `s` - 排序（不改变总和）: `5d6s`
- `cV` - 计数值V出现次数（作为一个结果输出）: `5d6c6`
- `RX` - 直到重投（直至 > X，含安全上限）: `d20R10`
- `aX` - 重投并相加（若 ≤ X 则再掷并加到结果）: `4d6a2`

### 复合表达式
- `6d6dl2kh3` - 丢弃最低2个，然后取最高3个
- `4d6!kh3` - 爆炸骰子，取最高3个
- `3d6r1 + 2d8ro2` - 重投组合

## API 参考

### 便捷函数

```python
# 解析并计算骰子表达式
result = oneroll.roll(expression: str) -> Dict[str, Any]

# 简单骰子投掷
total = oneroll.roll_simple(dice_count: int, dice_sides: int) -> int

# 多次投掷
results = oneroll.roll_multiple(expression: str, times: int) -> List[Dict[str, Any]]

# 统计投掷
stats = oneroll.roll_statistics(expression: str, times: int) -> Dict[str, Any]
```

### OneRoll 类

```python
roller = oneroll.OneRoll()

# 解析并计算骰子表达式
result = roller.roll(expression: str) -> Dict[str, Any]

# 简单骰子投掷
total = roller.roll_simple(dice_count: int, dice_sides: int) -> int

# 带修饰符的投掷
result = roller.roll_with_modifiers(
    dice_count: int, 
    dice_sides: int, 
    modifiers: List[str]
) -> Dict[str, Any]
```

### 常用表达式常量

```python
# D&D 常用投掷
oneroll.CommonRolls.D20              # "1d20"
oneroll.CommonRolls.D20_ADVANTAGE    # "2d20kh1"
oneroll.CommonRolls.D20_DISADVANTAGE # "2d20kl1"
oneroll.CommonRolls.ATTRIBUTE_ROLL   # "4d6kh3"
```

## 使用模式

### 1. 命令行模式

```bash
# 直接投掷
python -m oneroll "3d6 + 2"

# 统计模式
python -m oneroll --stats "3d6" --times 100

# 显示版本
python -m oneroll --version
```

### 2. 交互式模式

```bash
python -m oneroll
```

支持的命令：
- `help` - 显示帮助
- `history` - 显示投掷历史
- `stats <表达式> <次数>` - 统计投掷
- `clear` - 清空历史
- `quit/exit` - 退出程序

### 3. 终端用户界面 (TUI)

```bash
python -m oneroll --tui
```

特性：
- 美观的终端界面
- 快速投掷按钮
- 投掷历史记录
- 统计功能
- 键盘快捷键支持

### 4. Python SDK 模式

```python
import oneroll

# 基本使用
result = oneroll.roll("3d6 + 2")

# 统计功能
stats = oneroll.roll_statistics("3d6", 100)
print(f"平均值: {stats['mean']:.2f}")

# 多次投掷
results = oneroll.roll_multiple("2d6", 10)
totals = [r['total'] for r in results]
```

## 示例

### D&D 游戏示例

```python
import oneroll

roller = oneroll.OneRoll()

# 属性投掷
attr_result = roller.roll(oneroll.CommonRolls.ATTRIBUTE_ROLL)
print(f"属性投掷: {attr_result['total']}")

# 攻击投掷
attack_roll = roller.roll("1d20 + 5")
print(f"攻击投掷: {attack_roll['total']}")

# 伤害投掷
damage_roll = roller.roll("2d6 + 3")
print(f"伤害投掷: {damage_roll['total']}")
```

### 统计示例

```python
import oneroll

# 统计 3d6 投掷 100 次
stats = oneroll.roll_statistics("3d6", 100)

print(f"最小值: {stats['min']}")
print(f"最大值: {stats['max']}")
print(f"平均值: {stats['mean']:.2f}")
print(f"总和: {stats['total']}")
```

## 项目结构

```
OneRoll/
├── src/                    # Rust 源码
│   ├── lib.rs             # 主入口文件
│   ├── errors.rs          # 错误类型
│   ├── types.rs           # 数据类型
│   ├── calculator.rs      # 计算逻辑
│   ├── parser.rs          # 解析逻辑
│   ├── python_bindings.rs # Python 绑定
│   └── oneroll/
│       ├── __init__.py    # Python 包入口
│       ├── __main__.py    # 命令行入口
│       ├── _core.pyi      # 类型注解
│       └── grammar.pest   # 语法定义
├── examples/              # 示例代码
├── tests/                 # 测试代码
└── docs/                  # 文档
```

## 开发

### 构建

```bash
# 开发构建
maturin develop

# 发布构建
maturin build
```

### 测试

```bash
# 运行测试
python -m pytest tests/

# 运行示例
python examples/sdk_example.py
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 更新日志

### v0.0.1
- 初始版本
- 支持基本骰子表达式
- 支持数学运算和修饰符
- 提供 Python SDK 接口
- 支持命令行和交互式模式
- 支持 TUI 界面
- 内置统计功能
