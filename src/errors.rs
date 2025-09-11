use thiserror::Error;

#[derive(Error, Debug)]
pub enum DiceError {
    #[error("解析错误: {0}")]
    ParseError(String),
    #[error("计算错误: {0}")]
    CalculationError(String),
    #[error("无效的骰子表达式: {0}")]
    InvalidExpression(String),
}

impl std::convert::From<DiceError> for pyo3::PyErr {
    fn from(err: DiceError) -> pyo3::PyErr {
        pyo3::PyErr::new::<pyo3::exceptions::PyValueError, _>(err.to_string())
    }
}
