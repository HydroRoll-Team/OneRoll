# OneRoll 功能开发示例：注释功能

本文档展示了如何为 OneRoll 项目添加新功能的完整开发流程，以添加注释功能为例。

## 功能需求

添加注释功能，允许用户在骰子表达式末尾使用 `#` 添加注释，返回结果中包含注释信息。

**示例：**
- `3d6 + 2 # 攻击投掷` → 返回 `{'total': 14, 'comment': '攻击投掷', ...}`
- `4d6kh3 # 属性投掷` → 返回 `{'total': 15, 'comment': '属性投掷', ...}`

## 开发步骤

### 1. 更新语法定义 (grammar.pest)

```pest
// 添加注释规则
comment = { "#" ~ (!"\n" ~ ANY)* }

// 修改主表达式规则以支持可选注释
dice_expr = { dice_term ~ (op ~ dice_term)* ~ comment? }
```

### 2. 更新类型定义 (types.rs)

```rust
// 为 DiceResult 添加注释字段
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DiceResult {
    pub expression: String,
    pub total: i32,
    pub rolls: Vec<Vec<i32>>,
    pub details: String,
    pub comment: Option<String>,  // 新增字段
}

// 为 Expression 添加注释变体
#[derive(Debug, Clone)]
pub enum Expression {
    // ... 现有变体
    WithComment(Box<Expression>, Option<String>),  // 新增变体
}
```

### 3. 更新解析器 (parser.rs)

```rust
// 添加注释解析函数
fn parse_comment(pair: pest::iterators::Pair<Rule>) -> Result<Option<String>, DiceError> {
    match pair.as_rule() {
        Rule::comment => {
            let comment = pair.as_str().trim_start_matches('#').trim();
            Ok(if comment.is_empty() { None } else { Some(comment.to_string()) })
        }
        _ => Ok(None),
    }
}

// 修改主解析逻辑以处理注释
Rule::dice_expr => {
    let mut pairs = pair.into_inner();
    let mut expr = Self::parse_dice_term(pairs.next().unwrap())?;
    
    while let Some(pair) = pairs.next() {
        match pair.as_rule() {
            Rule::op => {
                // ... 操作符处理逻辑
            }
            Rule::comment => {
                let comment = Self::parse_comment(pair)?;
                if let Some(comment_text) = comment {
                    expr = Expression::WithComment(Box::new(expr), Some(comment_text));
                }
            }
            _ => {}
        }
    }
    Ok(expr)
}
```

### 4. 更新计算器 (calculator.rs)

```rust
// 为所有 DiceResult 创建添加 comment: None
Expression::Number(n) => Ok(DiceResult {
    expression: n.to_string(),
    total: *n,
    rolls: vec![],
    details: format!("{}", n),
    comment: None,  // 新增
}),

// 添加注释处理逻辑
Expression::WithComment(expr, comment) => {
    let mut result = self.evaluate_expression(expr)?;
    result.comment = comment.clone();
    Ok(result)
}
```

### 5. 更新 Python 绑定 (python_bindings.rs)

```rust
// 在所有返回字典中添加注释字段
let dict = PyDict::new(py);
dict.set_item("expression", &result.expression)?;
dict.set_item("total", result.total)?;
dict.set_item("rolls", result.rolls)?;
dict.set_item("details", &result.details)?;
dict.set_item("comment", result.comment.as_deref().unwrap_or(""))?;  // 新增

Ok(dict.into())
```

### 6. 更新类型注解 (_core.pyi)

```python
def roll_dice(expression: str) -> Dict[str, Any]:
    """
    解析并计算骰子表达式
    
    Returns:
        包含以下键的字典：
        - expression: str - 表达式字符串
        - total: int - 总点数
        - rolls: List[List[int]] - 投掷结果列表
        - details: str - 详细信息
        - comment: str - 用户注释  # 新增
    """
    ...
```

### 7. 更新 Python 接口 (__init__.py)

```python
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
```

### 8. 更新用户界面

#### 命令行界面 (__main__.py)
```python
def print_result(self, result: Dict[str, Any], expression: str = None):
    """美化打印投掷结果"""
    # ... 现有逻辑
    
    # 显示注释
    comment = result.get("comment", "")
    if comment:
        text.append(f"\n注释: ", style="bold")
        text.append(f"{comment}", style="italic blue")
    
    panel = Panel(text, title="投掷结果", border_style=color)
    console.print(panel)
```

#### TUI 界面 (tui.py)
```python
def show_result(self, result: Dict[str, Any], expression: str) -> None:
    """显示投掷结果"""
    # ... 现有逻辑
    
    # 显示注释
    comment = result.get("comment", "")
    if comment:
        display_text += f"\n\n[bold]注释:[/bold] [italic blue]{comment}[/italic blue]"
    
    self.update(display_text)
```

## 构建和测试

### 构建项目
```bash
maturin develop
```

### 测试新功能
```python
# 基本测试
import oneroll
result = oneroll.roll("3d6 + 2 # 攻击投掷")
print(f"总点数: {result['total']}, 注释: {result['comment']}")

# 命令行测试
python -m oneroll "4d6kh3 # 属性投掷"

# 复杂表达式测试
python -c "import oneroll; print(oneroll.roll('2d6! # 爆炸骰子攻击'))"
```

## 测试结果

```
总点数: 14, 注释: 攻击投掷
```

```
╭──────────────────────────────────────────────── 投掷结果 ────────────────────────────────────────────────╮
│ 🎲 4d6                                                                                                   │
│ 总点数: 13                                                                                               │
│ 详情: 4d6kh3 = 13 (详情: [[5], [4], [4]])                                                                │
│ 投掷结果: [[5], [4], [4]]                                                                                │
│ 注释: 属性投掷                                                                                           │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

## 开发要点

### 1. 模块化开发
- 每个功能都在相应的模块中实现
- 保持代码的清晰结构和职责分离

### 2. 类型安全
- 所有新功能都有完整的类型注解
- 使用 Option<T> 处理可选字段

### 3. 向后兼容
- 新功能不影响现有 API
- 可选字段使用默认值

### 4. 用户体验
- 更新所有用户界面以显示新功能
- 提供清晰的文档和示例

### 5. 错误处理
- 处理边界情况（如空注释）
- 保持现有的错误处理机制

## 扩展建议

### 1. 注释验证
```rust
// 可以添加注释长度限制
if comment.len() > MAX_COMMENT_LENGTH {
    return Err(DiceError::InvalidExpression("注释过长".to_string()));
}
```

### 2. 注释格式化
```rust
// 可以添加注释格式化选项
pub struct CommentOptions {
    pub max_length: usize,
    pub allow_special_chars: bool,
    pub trim_whitespace: bool,
}
```

### 3. 注释统计
```python
# 可以添加注释相关的统计功能
def get_comment_statistics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """分析注释使用情况"""
    comments = [r.get('comment', '') for r in results if r.get('comment')]
    return {
        'total_comments': len(comments),
        'unique_comments': len(set(comments)),
        'most_common': max(set(comments), key=comments.count) if comments else None
    }
```

## 总结

这个示例展示了为 OneRoll 项目添加新功能的完整流程：

1. **语法定义** → 定义新语法规则
2. **类型定义** → 添加新的数据结构
3. **解析器** → 实现解析逻辑
4. **计算器** → 处理新功能
5. **Python 绑定** → 暴露给 Python
6. **类型注解** → 提供类型信息
7. **Python 接口** → 更新文档和示例
8. **用户界面** → 在所有界面中支持新功能

这种模块化的开发方式确保了：
- 代码的可维护性
- 功能的完整性
- 用户体验的一致性
- 向后兼容性

通过这个流程，你可以轻松地为 OneRoll 添加更多功能，如自定义修饰符、条件表达式、变量支持等。
