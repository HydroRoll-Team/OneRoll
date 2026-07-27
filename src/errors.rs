use thiserror::Error;

#[derive(Error, Debug)]
pub enum DiceError {
    #[error("解析错误: {0}")]
    ParseError(String),
    #[error("计算错误: {0}")]
    CalculationError(String),
    #[error("无效的骰子表达式: {0}")]
    InvalidExpression(String),
    #[error("计算预算已耗尽: 最多生成 {limit} 个骰子结果")]
    BudgetExceeded { limit: usize },
    #[error("程序指令数量超过限制: 最多 {limit} 条")]
    ProgramInstructionLimitExceeded { limit: usize },
}

impl std::convert::From<DiceError> for pyo3::PyErr {
    fn from(err: DiceError) -> pyo3::PyErr {
        pyo3::PyErr::new::<pyo3::exceptions::PyValueError, _>(err.to_string())
    }
}
