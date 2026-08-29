use crate::random::RandomDescriptor;
use serde::{Deserialize, Serialize};
use thiserror::Error;

pub const ERROR_SCHEMA_VERSION: &str = "2.0";

#[derive(Clone, Copy, Debug, Deserialize, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum ErrorPhase {
    Parse,
    Validate,
    Evaluate,
    Cancel,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq, Serialize)]
pub struct SourceSpan {
    pub start_byte: usize,
    pub end_byte: usize,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq, Serialize)]
pub struct ExecutionError {
    pub phase: ErrorPhase,
    pub code: String,
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub span: Option<SourceSpan>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub resource: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub used: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub requested: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub limit: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub random: Option<RandomDescriptor>,
    #[serde(skip_serializing_if = "Vec::is_empty", default)]
    pub expected: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub replacement: Option<String>,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq, Serialize)]
pub struct ErrorEnvelope {
    pub schema_version: String,
    pub kind: String,
    pub error: ExecutionError,
}

#[derive(Error, Debug)]
pub enum DiceError {
    #[error("解析错误: {message}")]
    ParseSyntax {
        message: String,
        span: SourceSpan,
        expected: Vec<String>,
    },
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
    #[error("[policy.invalid_limit] {0}")]
    PolicyInvalidLimit(String),
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
    #[error("{source}")]
    Context {
        #[source]
        source: Box<DiceError>,
        phase: Option<ErrorPhase>,
        span: Option<SourceSpan>,
        random: Option<RandomDescriptor>,
    },
}

impl DiceError {
    pub fn with_phase(self, phase: ErrorPhase) -> Self {
        match self {
            Self::Context {
                source,
                span,
                random,
                ..
            } => Self::Context {
                source,
                phase: Some(phase),
                span,
                random,
            },
            source => Self::Context {
                source: Box::new(source),
                phase: Some(phase),
                span: None,
                random: None,
            },
        }
    }

    pub fn with_random(self, random: RandomDescriptor) -> Self {
        match self {
            Self::Context {
                source,
                phase,
                span,
                ..
            } => Self::Context {
                source,
                phase,
                span,
                random: Some(random),
            },
            source => Self::Context {
                source: Box::new(source),
                phase: None,
                span: None,
                random: Some(random),
            },
        }
    }

    pub fn with_span(self, span: SourceSpan) -> Self {
        match self {
            Self::Context {
                source,
                phase,
                random,
                ..
            } => Self::Context {
                source,
                phase,
                span: Some(span),
                random,
            },
            source => Self::Context {
                source: Box::new(source),
                phase: None,
                span: Some(span),
                random: None,
            },
        }
    }

    pub fn with_fallback_span(self, span: SourceSpan) -> Self {
        if self.execution_error().span.is_some() {
            self
        } else {
            self.with_span(span)
        }
    }

    pub fn root_cause(&self) -> &Self {
        match self {
            Self::Context { source, .. } => source.root_cause(),
            error => error,
        }
    }

    pub fn execution_error(&self) -> ExecutionError {
        let (phase, span, random) = self.context();
        let mut error = self.root_cause().base_execution_error();
        if let Some(phase) = phase {
            error.phase = phase;
        }
        if span.is_some() {
            error.span = span;
        }
        if random.is_some() {
            error.random = random;
        }
        error
    }

    pub fn envelope(&self) -> ErrorEnvelope {
        ErrorEnvelope {
            schema_version: ERROR_SCHEMA_VERSION.to_string(),
            kind: "error".to_string(),
            error: self.execution_error(),
        }
    }

    pub fn envelope_json(&self) -> String {
        serde_json::to_string(&self.envelope())
            .expect("the RFC-0003 error envelope must always serialize")
    }

    fn context(
        &self,
    ) -> (
        Option<ErrorPhase>,
        Option<SourceSpan>,
        Option<RandomDescriptor>,
    ) {
        match self {
            Self::Context {
                source,
                phase,
                span,
                random,
            } => {
                let (inner_phase, inner_span, inner_random) = source.context();
                (
                    phase.or(inner_phase),
                    span.clone().or(inner_span),
                    random.clone().or(inner_random),
                )
            }
            Self::ParseSyntax { span, .. } => (Some(ErrorPhase::Parse), Some(span.clone()), None),
            _ => (None, None, None),
        }
    }

    fn base_execution_error(&self) -> ExecutionError {
        let mut error = ExecutionError {
            phase: ErrorPhase::Evaluate,
            code: String::new(),
            message: String::new(),
            span: None,
            resource: None,
            used: None,
            requested: None,
            limit: None,
            random: None,
            expected: Vec::new(),
            replacement: None,
        };

        match self {
            Self::ParseSyntax {
                message,
                span,
                expected,
            } => {
                error.phase = ErrorPhase::Parse;
                error.code = "parse.invalid_syntax".to_string();
                error.message = message.clone();
                error.span = Some(span.clone());
                error.expected = expected.clone();
            }
            Self::ParseError(message) => {
                error.phase = ErrorPhase::Parse;
                error.code = "parse.invalid_syntax".to_string();
                error.message = message.clone();
            }
            Self::CalculationError(message) => {
                error.code = "evaluate.internal".to_string();
                error.message = message.clone();
            }
            Self::ArithmeticOverflow { operation } => {
                error.code = "arithmetic.overflow".to_string();
                error.message = format!("checked i64 overflow during {operation}");
            }
            Self::ArithmeticDivideByZero => {
                error.code = "arithmetic.divide_by_zero".to_string();
                error.message = "division by zero".to_string();
            }
            Self::ArithmeticInvalidExponent { exponent } => {
                error.code = "arithmetic.invalid_exponent".to_string();
                error.message = format!("exponent {exponent} must fit unsigned 32-bit range");
            }
            Self::RandomInvalidSeed => {
                error.phase = ErrorPhase::Validate;
                error.code = "random.invalid_seed".to_string();
                error.message =
                    "seed must be an unsigned 64-bit integer or exactly 64 hexadecimal digits"
                        .to_string();
            }
            Self::RandomEntropyUnavailable { .. } => {
                error.code = "random.entropy_unavailable".to_string();
                error.message = "operating-system entropy is unavailable".to_string();
            }
            Self::InvalidExpression(message) => {
                error.phase = ErrorPhase::Validate;
                error.code = "validate.invalid_expression".to_string();
                error.message = message.clone();
            }
            Self::BudgetExceeded { limit } => {
                error.code = "limit.generated_values".to_string();
                error.message = "generated value budget exceeded".to_string();
                error.resource = Some("generated_values".to_string());
                error.used = Some(*limit);
                error.requested = Some(1);
                error.limit = Some(*limit);
            }
            Self::ProgramInstructionLimitExceeded { limit } => {
                error.phase = ErrorPhase::Parse;
                error.code = "limit.parsed_instructions".to_string();
                error.message = "parsed instruction budget exceeded".to_string();
                error.resource = Some("parsed_instructions".to_string());
                error.used = Some(*limit);
                error.requested = Some(1);
                error.limit = Some(*limit);
            }
            Self::ResourceLimitExceeded {
                resource,
                used,
                requested,
                limit,
            } => {
                error.code = format!("limit.{resource}");
                error.message = format!("{resource} budget exceeded");
                error.resource = Some((*resource).to_string());
                error.used = Some(*used);
                error.requested = Some(*requested);
                error.limit = Some(*limit);
            }
            Self::GeneratedValueLimitExceeded {
                used,
                requested,
                limit,
            } => {
                error.code = "limit.generated_values".to_string();
                error.message = "generated value budget exceeded".to_string();
                error.resource = Some("generated_values".to_string());
                error.used = Some(*used);
                error.requested = Some(*requested);
                error.limit = Some(*limit);
            }
            Self::PolicyInvalidLimit(message) => {
                error.phase = ErrorPhase::Validate;
                error.code = "policy.invalid_limit".to_string();
                error.message = message.clone();
            }
            Self::UnknownResourceLimit(resource) => {
                error.phase = ErrorPhase::Validate;
                error.code = "policy.invalid_limit".to_string();
                error.message = format!("unknown resource limit: {resource}");
            }
            Self::PolicyLimitExceedsHardMaximum {
                resource,
                requested,
                hard_max,
            } => {
                error.phase = ErrorPhase::Validate;
                error.code = "policy.limit_above_hard_max".to_string();
                error.message =
                    format!("{resource} limit {requested} exceeds hard maximum {hard_max}");
            }
            Self::Context { source, .. } => return source.base_execution_error(),
        }
        error
    }
}

impl std::convert::From<DiceError> for pyo3::PyErr {
    fn from(err: DiceError) -> pyo3::PyErr {
        let payload = err.envelope_json();
        let py_err = pyo3::PyErr::new::<pyo3::exceptions::PyValueError, _>(err.to_string());
        pyo3::Python::with_gil(|py| {
            let _ = py_err.value(py).setattr("_oneroll_error_json", payload);
        });
        py_err
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn resource_error_serializes_as_the_rfc_0003_envelope() {
        let error = DiceError::ResourceLimitExceeded {
            resource: "work_units",
            used: 10,
            requested: 2,
            limit: 10,
        };
        let payload = serde_json::to_value(error.envelope()).unwrap();

        assert_eq!(payload["schema_version"], "2.0");
        assert_eq!(payload["kind"], "error");
        assert_eq!(payload["error"]["phase"], "evaluate");
        assert_eq!(payload["error"]["code"], "limit.work_units");
        assert_eq!(payload["error"]["resource"], "work_units");
        assert_eq!(payload["error"]["used"], 10);
        assert_eq!(payload["error"]["requested"], 2);
        assert_eq!(payload["error"]["limit"], 10);
        assert!(payload.get("results").is_none());
    }

    #[test]
    fn context_preserves_phase_span_and_random_metadata() {
        let random = RandomDescriptor {
            algorithm: "oneroll-chacha12-v1".to_string(),
            seed: "0".repeat(64),
            rng_words: 3,
        };
        let error = DiceError::ArithmeticDivideByZero
            .with_span(SourceSpan {
                start_byte: 2,
                end_byte: 3,
            })
            .with_phase(ErrorPhase::Validate)
            .with_random(random.clone());
        let structured = error.execution_error();

        assert_eq!(structured.phase, ErrorPhase::Validate);
        assert_eq!(structured.span.unwrap().start_byte, 2);
        assert_eq!(structured.random, Some(random));
        assert!(matches!(
            error.root_cause(),
            DiceError::ArithmeticDivideByZero
        ));
    }

    #[test]
    fn public_error_families_have_stable_phase_and_code_pairs() {
        let cases = vec![
            (
                DiceError::ParseError("bad syntax".to_string()),
                ErrorPhase::Parse,
                "parse.invalid_syntax",
            ),
            (
                DiceError::InvalidExpression("bad value".to_string()),
                ErrorPhase::Validate,
                "validate.invalid_expression",
            ),
            (
                DiceError::RandomInvalidSeed,
                ErrorPhase::Validate,
                "random.invalid_seed",
            ),
            (
                DiceError::ArithmeticDivideByZero,
                ErrorPhase::Evaluate,
                "arithmetic.divide_by_zero",
            ),
            (
                DiceError::RandomEntropyUnavailable {
                    reason: "offline".to_string(),
                },
                ErrorPhase::Evaluate,
                "random.entropy_unavailable",
            ),
            (
                DiceError::PolicyInvalidLimit("negative".to_string()),
                ErrorPhase::Validate,
                "policy.invalid_limit",
            ),
        ];

        for (error, phase, code) in cases {
            let structured = error.execution_error();
            assert_eq!(structured.phase, phase);
            assert_eq!(structured.code, code);
            assert!(!structured.message.is_empty());
        }
    }
}
