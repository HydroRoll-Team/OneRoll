use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

use crate::calculator::DiceCalculator;
use crate::parser::DiceParser;
use crate::resource::{ResourcePolicy, RESOURCE_LIMITS};
use crate::types::{DiceModifier, DiceResult, DiceRoll, Expression, ProgramResult};

fn dice_result_to_dict<'py>(py: Python<'py>, result: &DiceResult) -> PyResult<&'py PyDict> {
    let dict = PyDict::new(py);
    dict.set_item("expression", &result.expression)?;
    dict.set_item("total", result.total)?;
    dict.set_item("rolls", &result.rolls)?;
    dict.set_item("details", &result.details)?;
    dict.set_item("comment", result.comment.as_deref().unwrap_or(""))?;
    Ok(dict)
}

fn program_result_to_object(py: Python<'_>, result: &ProgramResult) -> PyResult<PyObject> {
    let instructions = PyList::empty(py);
    for instruction in &result.results {
        instructions.append(dice_result_to_dict(py, instruction)?)?;
    }

    let dict = PyDict::new(py);
    dict.set_item("results", instructions)?;
    dict.set_item("comment", result.comment.as_deref().unwrap_or(""))?;
    Ok(dict.into())
}

#[pyclass(name = "ResourcePolicy", frozen)]
#[derive(Clone)]
pub struct PyResourcePolicy {
    pub(crate) inner: ResourcePolicy,
}

#[pymethods]
impl PyResourcePolicy {
    #[new]
    fn new() -> Self {
        Self {
            inner: ResourcePolicy::default(),
        }
    }

    fn with_limit(&self, name: &str, limit: i64) -> PyResult<Self> {
        if limit < 0 {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "[policy.invalid_limit] {name} limit must be non-negative"
            )));
        }
        Ok(Self {
            inner: self
                .inner
                .with_limit(name, limit as usize)
                .map_err(PyErr::from)?,
        })
    }

    fn limits(&self, py: Python<'_>) -> PyResult<PyObject> {
        let limits = PyDict::new(py);
        for definition in RESOURCE_LIMITS {
            limits.set_item(
                definition.name,
                self.inner
                    .limit(definition.name)
                    .expect("registered resource limit"),
            )?;
        }
        Ok(limits.into())
    }

    fn hard_limits(&self, py: Python<'_>) -> PyResult<PyObject> {
        let limits = PyDict::new(py);
        for definition in RESOURCE_LIMITS {
            limits.set_item(definition.name, definition.hard_max)?;
        }
        Ok(limits.into())
    }
}

#[pyclass]
pub struct OneRoll {
    policy: ResourcePolicy,
}

#[pymethods]
impl OneRoll {
    #[new]
    fn new(policy: Option<PyRef<'_, PyResourcePolicy>>) -> Self {
        Self {
            policy: policy
                .map(|policy| policy.inner.clone())
                .unwrap_or_default(),
        }
    }

    fn roll(&mut self, expression: &str) -> PyResult<PyObject> {
        Python::with_gil(|py| {
            let mut calculator = DiceCalculator::with_policy(self.policy.clone());
            let expr = DiceParser::parse_expression_with_policy(expression, &self.policy)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

            let result = calculator
                .evaluate_expression(&expr)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

            let dict = PyDict::new(py);
            dict.set_item("expression", &result.expression)?;
            dict.set_item("total", result.total)?;
            dict.set_item("rolls", result.rolls)?;
            dict.set_item("details", &result.details)?;
            dict.set_item("comment", result.comment.as_deref().unwrap_or(""))?;

            Ok(dict.into())
        })
    }

    fn run(&mut self, program: &str) -> PyResult<PyObject> {
        Python::with_gil(|py| {
            let mut calculator = DiceCalculator::with_policy(self.policy.clone());
            let program = DiceParser::parse_program_with_policy(program, &self.policy)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
            let result = calculator
                .evaluate_program(&program)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

            program_result_to_object(py, &result)
        })
    }

    fn roll_multiple(&mut self, expression: &str, times: usize) -> PyResult<PyObject> {
        Python::with_gil(|py| {
            let expression = DiceParser::parse_expression_with_policy(expression, &self.policy)
                .map_err(PyErr::from)?;
            let mut calculator = DiceCalculator::with_policy(self.policy.clone());
            let results = calculator
                .evaluate_batch(&expression, times)
                .map_err(PyErr::from)?;
            let items = PyList::empty(py);
            for result in &results {
                items.append(dice_result_to_dict(py, result)?)?;
            }
            Ok(items.into())
        })
    }

    fn roll_simple(&mut self, dice_count: i32, dice_sides: i32) -> PyResult<i64> {
        let mut calculator = DiceCalculator::with_policy(self.policy.clone());
        let dice = DiceRoll {
            count: dice_count,
            sides: dice_sides,
            modifiers: vec![],
        };

        calculator
            .roll_simple(&dice)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))
    }

    fn roll_with_modifiers(
        &mut self,
        dice_count: i32,
        dice_sides: i32,
        modifiers: Vec<String>,
    ) -> PyResult<PyObject> {
        Python::with_gil(|py| {
            let mut calculator = DiceCalculator::with_policy(self.policy.clone());
            let mut dice_modifiers = Vec::new();

            for modifier_str in modifiers {
                let modifier = match modifier_str.as_str() {
                    "!" => DiceModifier::Explode,
                    s if s.starts_with("r") && !s.starts_with("ro") => {
                        let num = s[1..].parse::<i32>().map_err(|_| {
                            PyErr::new::<pyo3::exceptions::PyValueError, _>("无效的重投数值")
                        })?;
                        DiceModifier::Reroll(num)
                    }
                    s if s.starts_with("ro") => {
                        let num = s[2..].parse::<i32>().map_err(|_| {
                            PyErr::new::<pyo3::exceptions::PyValueError, _>("无效的条件重投数值")
                        })?;
                        DiceModifier::RerollOnce(num)
                    }
                    s if s.starts_with("kh") => {
                        let num = s[2..].parse::<i32>().map_err(|_| {
                            PyErr::new::<pyo3::exceptions::PyValueError, _>("无效的取高数值")
                        })?;
                        DiceModifier::KeepHigh(num)
                    }
                    s if s.starts_with("kl") => {
                        let num = s[2..].parse::<i32>().map_err(|_| {
                            PyErr::new::<pyo3::exceptions::PyValueError, _>("无效的取低数值")
                        })?;
                        DiceModifier::KeepLow(num)
                    }
                    s if s.starts_with("dh") => {
                        let num = s[2..].parse::<i32>().map_err(|_| {
                            PyErr::new::<pyo3::exceptions::PyValueError, _>("无效的丢弃高数值")
                        })?;
                        DiceModifier::DropHigh(num)
                    }
                    s if s.starts_with("dl") => {
                        let num = s[2..].parse::<i32>().map_err(|_| {
                            PyErr::new::<pyo3::exceptions::PyValueError, _>("无效的丢弃低数值")
                        })?;
                        DiceModifier::DropLow(num)
                    }
                    _ => {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            "未知的修饰符",
                        ))
                    }
                };
                dice_modifiers.push(modifier);
            }

            let dice = DiceRoll {
                count: dice_count,
                sides: dice_sides,
                modifiers: dice_modifiers,
            };

            let result = calculator
                .evaluate_expression(&Expression::DiceRoll(dice))
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

            let dict = PyDict::new(py);
            dict.set_item("total", result.total)?;
            dict.set_item("rolls", result.rolls)?;
            dict.set_item("details", &result.details)?;

            Ok(dict.into())
        })
    }
}

#[pyfunction]
pub fn roll_dice(expression: &str) -> PyResult<PyObject> {
    Python::with_gil(|py| {
        let mut calculator = DiceCalculator::new();
        let expr = DiceParser::parse_expression(expression)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

        let result = calculator
            .evaluate_expression(&expr)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

        let dict = PyDict::new(py);
        dict.set_item("expression", &result.expression)?;
        dict.set_item("total", result.total)?;
        dict.set_item("rolls", result.rolls)?;
        dict.set_item("details", &result.details)?;
        dict.set_item("comment", result.comment.as_deref().unwrap_or(""))?;

        Ok(dict.into())
    })
}

#[pyfunction]
pub fn run_program(program: &str) -> PyResult<PyObject> {
    Python::with_gil(|py| {
        let mut calculator = DiceCalculator::new();
        let program = DiceParser::parse_program(program)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
        let result = calculator
            .evaluate_program(&program)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

        program_result_to_object(py, &result)
    })
}

#[pyfunction]
pub fn roll_simple(dice_count: i32, dice_sides: i32) -> PyResult<i64> {
    let mut calculator = DiceCalculator::new();
    let dice = DiceRoll {
        count: dice_count,
        sides: dice_sides,
        modifiers: vec![],
    };

    calculator
        .roll_simple(&dice)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))
}
