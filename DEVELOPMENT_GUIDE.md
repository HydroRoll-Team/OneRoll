# OneRoll 开发指南

## 项目开发流程

### 1. 添加新功能

#### 步骤 1: 更新语法定义 (grammar.pest)
```pest
// 在 grammar.pest 中添加新的语法规则
comment = { "#" ~ (!"\n" ~ ANY)* }
dice_expr = { dice_term ~ (op ~ dice_term)* ~ comment? }
```

#### 步骤 2: 更新类型定义 (types.rs)
```rust
// 在 types.rs 中添加新的数据结构
#[derive(Debug, Clone)]
pub enum Expression {
    // ... 现有变体
    WithComment(Box<Expression>, Option<String>),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DiceResult {
    pub expression: String,
    pub total: i32,
    pub rolls: Vec<Vec<i32>>,
    pub details: String,
    pub comment: Option<String>,  // 新增字段
}
```

#### 步骤 3: 更新解析器 (parser.rs)
```rust
// 在 parser.rs 中添加解析逻辑
impl DiceParser {
    fn parse_comment(pair: pest::iterators::Pair<Rule>) -> Result<Option<String>, DiceError> {
        match pair.as_rule() {
            Rule::comment => {
                let comment = pair.as_str().trim_start_matches('#').trim();
                Ok(if comment.is_empty() { None } else { Some(comment.to_string()) })
            }
            _ => Ok(None),
        }
    }
}
```

#### 步骤 4: 更新计算器 (calculator.rs)
```rust
// 在 calculator.rs 中处理新功能
impl DiceCalculator {
    pub fn evaluate_expression(&mut self, expr: &Expression) -> Result<DiceResult, DiceError> {
        match expr {
            // ... 现有处理逻辑
            Expression::WithComment(expr, comment) => {
                let mut result = self.evaluate_expression(expr)?;
                result.comment = comment.clone();
                Ok(result)
            }
        }
    }
}
```

#### 步骤 5: 更新 Python 绑定 (python_bindings.rs)
```rust
// 在 python_bindings.rs 中暴露新功能
#[pyfunction]
pub fn roll_dice(expression: &str) -> PyResult<PyObject> {
    Python::with_gil(|py| {
        let mut calculator = DiceCalculator::new();
        let expr = DiceParser::parse_expression(expression)?;
        let result = calculator.evaluate_expression(&expr)?;
        
        let dict = PyDict::new(py);
        dict.set_item("expression", &result.expression)?;
        dict.set_item("total", result.total)?;
        dict.set_item("rolls", result.rolls)?;
        dict.set_item("details", &result.details)?;
        dict.set_item("comment", result.comment.as_deref().unwrap_or(""))?;  // 新增
        
        Ok(dict.into())
    })
}
```

#### 步骤 6: 更新类型注解 (_core.pyi)
```python
# 在 _core.pyi 中更新类型定义
def roll_dice(expression: str) -> Dict[str, Any]:
    """
    解析并计算骰子表达式
    
    Returns:
        包含以下键的字典：
        - expression: str - 表达式字符串
        - total: int - 总点数
        - rolls: List[List[int]] - 投掷结果列表
        - details: str - 详细信息
        - comment: str - 用户注释 (新增)
    """
    ...
```

#### 步骤 7: 更新 Python 接口 (__init__.py)
```python
# 在 __init__.py 中更新文档和示例
def roll(expression: str) -> Dict[str, Any]:
    """
    解析并计算骰子表达式（便捷函数）
    
    Args:
        expression: 骰子表达式字符串，支持注释
                   如 "3d6 + 2 # 攻击投掷"
    
    Returns:
        投掷结果字典，包含 comment 字段
        
    Example:
        result = oneroll.roll("3d6 + 2 # 攻击投掷")
        print(result["comment"])  # 输出: "攻击投掷"
    """
    return _roll_dice(expression)
```

#### 步骤 8: 更新用户界面
```python
# 在 __main__.py 中更新显示逻辑
def print_result(self, result: Dict[str, Any], expression: str = None):
    """美化打印投掷结果"""
    # ... 现有逻辑
    comment = result.get("comment", "")
    if comment:
        display_text += f"\n[bold]注释:[/bold] {comment}"
    
    self.update(display_text)
```

### 2. 修复 Bug

#### 步骤 1: 重现问题
```bash
# 创建一个测试用例来重现 bug
python -c "import oneroll; print(oneroll.roll('问题表达式'))"
```

#### 步骤 2: 定位问题
```bash
# 使用调试模式编译
RUST_LOG=debug maturin develop
```

#### 步骤 3: 修复代码
```rust
// 在相应的模块中修复问题
impl DiceCalculator {
    pub fn roll_dice(&mut self, dice: &DiceRoll) -> Result<Vec<Vec<i32>>, DiceError> {
        // 修复逻辑
        if dice.count <= 0 || dice.sides <= 0 {
            return Err(DiceError::InvalidExpression(
                "骰子数量和面数必须大于0".to_string(),
            ));
        }
        
        // 添加边界检查
        if dice.count > 1000 {
            return Err(DiceError::InvalidExpression(
                "骰子数量不能超过1000".to_string(),
            ));
        }
        
        // ... 其余逻辑
    }
}
```

#### 步骤 4: 添加测试
```python
# 在 tests/ 目录中添加测试
def test_large_dice_count():
    """测试大量骰子的边界情况"""
    with pytest.raises(ValueError, match="骰子数量不能超过1000"):
        oneroll.roll("1001d6")
```

#### 步骤 5: 验证修复
```bash
# 重新构建并测试
maturin develop
python -m pytest tests/
```

### 3. 调整参数

#### 步骤 1: 识别需要调整的参数
```rust
// 在 calculator.rs 中定义常量
const MAX_DICE_COUNT: i32 = 1000;
const MAX_DICE_SIDES: i32 = 10000;
const MAX_EXPRESSION_LENGTH: usize = 1000;
```

#### 步骤 2: 创建配置结构
```rust
// 在 types.rs 中添加配置结构
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OneRollConfig {
    pub max_dice_count: i32,
    pub max_dice_sides: i32,
    pub max_expression_length: usize,
    pub enable_comments: bool,
}

impl Default for OneRollConfig {
    fn default() -> Self {
        Self {
            max_dice_count: 1000,
            max_dice_sides: 10000,
            max_expression_length: 1000,
            enable_comments: true,
        }
    }
}
```

#### 步骤 3: 更新计算器以使用配置
```rust
// 在 calculator.rs 中使用配置
pub struct DiceCalculator {
    config: OneRollConfig,
}

impl DiceCalculator {
    pub fn new() -> Self {
        Self {
            config: OneRollConfig::default(),
        }
    }
    
    pub fn with_config(config: OneRollConfig) -> Self {
        Self { config }
    }
    
    pub fn roll_dice(&mut self, dice: &DiceRoll) -> Result<Vec<Vec<i32>>, DiceError> {
        if dice.count > self.config.max_dice_count {
            return Err(DiceError::InvalidExpression(
                format!("骰子数量不能超过{}", self.config.max_dice_count),
            ));
        }
        
        // ... 其余逻辑
    }
}
```

#### 步骤 4: 暴露配置接口
```rust
// 在 python_bindings.rs 中暴露配置
#[pyclass]
pub struct OneRoll {
    calculator: DiceCalculator,
}

#[pymethods]
impl OneRoll {
    #[new]
    fn new() -> Self {
        Self {
            calculator: DiceCalculator::new(),
        }
    }
    
    fn with_config(config: PyObject) -> PyResult<Self> {
        Python::with_gil(|py| {
            let config_dict = config.downcast::<PyDict>(py)?;
            let max_dice_count = config_dict.get_item("max_dice_count")?.extract()?;
            let max_dice_sides = config_dict.get_item("max_dice_sides")?.extract()?;
            
            let config = OneRollConfig {
                max_dice_count,
                max_dice_sides,
                max_expression_length: 1000,
                enable_comments: true,
            };
            
            Ok(Self {
                calculator: DiceCalculator::with_config(config),
            })
        })
    }
}
```

## 开发工具和命令

### 构建和测试
```bash
# 开发构建
maturin develop

# 发布构建
maturin build

# 运行测试
python -m pytest tests/

# 类型检查
mypy src/oneroll/

# 代码格式化
black src/oneroll/
```

### 调试
```bash
# 调试构建
RUST_LOG=debug maturin develop

# 运行特定测试
python -m pytest tests/test_specific.py::test_function -v

# 性能分析
python -m cProfile -s cumtime examples/sdk_example.py
```

### 文档
```bash
# 生成文档
cargo doc --open

# 更新 README
# 手动更新 README.md

# 更新类型注解
# 手动更新 _core.pyi
```

## 版本管理

### 语义化版本
- **主版本号**: 不兼容的 API 修改
- **次版本号**: 向下兼容的功能性新增
- **修订号**: 向下兼容的问题修正

### 发布流程
1. 更新版本号
2. 更新 CHANGELOG.md
3. 运行测试
4. 构建发布版本
5. 创建 Git 标签
6. 发布到 PyPI

## 贡献指南

### 提交规范
```
feat: 添加注释支持
fix: 修复大量骰子的性能问题
docs: 更新 API 文档
test: 添加边界情况测试
```

### 代码审查
1. 功能完整性
2. 性能影响
3. 向后兼容性
4. 测试覆盖率
5. 文档更新
