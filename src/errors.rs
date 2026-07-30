use thiserror::Error;

#[derive(Error, Debug)]
pub enum DiceError {
    #[error("解析错误: {0}")]
    ParseError(String),
    #[error("计算错误: {0}")]
    CalculationError(String),
    #[error("[arithmetic.overflow] checked i64 overflow during {operation}")]
    ArithmeticOverflow { operation: &'static str },
    #[error("[arithmetic.divide_by_zero] 除零错误")]
    ArithmeticDivideByZero,
    #[error("[arithmetic.invalid_exponent] exponent {exponent} must fit unsigned 32-bit range")]
    ArithmeticInvalidExponent { exponent: i64 },
    #[error("[random.invalid_seed] seed must be an unsigned 64-bit integer or exactly 64 hexadecimal digits")]
    RandomInvalidSeed,
    #[error("[random.entropy_unavailable] operating-system entropy is unavailable: {reason}")]
    RandomEntropyUnavailable { reason: String },
    #[error("无效的骰子表达式: {0}")]
    InvalidExpression(String),
    #[error("计算预算已耗尽: 最多生成 {limit} 个骰子结果")]
    BudgetExceeded { limit: usize },
    #[error("[limit.parsed_instructions] 程序指令数量超过限制: 最多 {limit} 条")]
    ProgramInstructionLimitExceeded { limit: usize },
    #[error(
        "[limit.{resource}] 计算预算已耗尽: used {used}, requested {requested}, limit {limit}"
    )]
    ResourceLimitExceeded {
        resource: &'static str,
        used: usize,
        requested: usize,
        limit: usize,
    },
    #[error(
        "[limit.generated_values] 计算预算已耗尽: 最多生成 {limit} 个骰子结果; used {used}, requested {requested}"
    )]
    GeneratedValueLimitExceeded {
        used: usize,
        requested: usize,
        limit: usize,
    },
    #[error("[policy.invalid_limit] unknown resource limit: {0}")]
    UnknownResourceLimit(String),
    #[error(
        "[policy.limit_above_hard_max] {resource} limit {requested} exceeds hard maximum {hard_max}"
    )]
    PolicyLimitExceedsHardMaximum {
        resource: &'static str,
        requested: usize,
        hard_max: usize,
    },
}

impl std::convert::From<DiceError> for pyo3::PyErr {
    fn from(err: DiceError) -> pyo3::PyErr {
        pyo3::PyErr::new::<pyo3::exceptions::PyValueError, _>(err.to_string())
    }
}
