use pyo3::prelude::*;
use pyo3::types::PyDict;

use crate::calculator::DiceCalculator;
use crate::parser::DiceParser;
use crate::types::{DiceModifier, DiceRoll};

#[pyclass]
pub struct OneRoll;

#[pymethods]
impl OneRoll {
    #[new]
    fn new() -> Self {
        Self
    }

    fn roll(&mut self, expression: &str) -> PyResult<PyObject> {
        Python::with_gil(|py| {
            let mut calculator = DiceCalculator::new();
            let expr = DiceParser::parse_expression(expression)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
            
            let result = calculator.evaluate_expression(&expr)
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

    fn roll_simple(&mut self, dice_count: i32, dice_sides: i32) -> PyResult<i32> {
        let mut calculator = DiceCalculator::new();
        let dice = DiceRoll {
            count: dice_count,
            sides: dice_sides,
            modifiers: vec![],
        };
        
        let rolls = calculator.roll_dice(&dice)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
        
        Ok(rolls.iter().flatten().sum())
    }

    fn roll_with_modifiers(&mut self, dice_count: i32, dice_sides: i32, modifiers: Vec<String>) -> PyResult<PyObject> {
        Python::with_gil(|py| {
            let mut calculator = DiceCalculator::new();
            let mut dice_modifiers = Vec::new();
            
            for modifier_str in modifiers {
                let modifier = match modifier_str.as_str() {
                    "!" => DiceModifier::Explode,
                    s if s.starts_with("r") && !s.starts_with("ro") => {
                        let num = s[1..].parse::<i32>()
                            .map_err(|_| PyErr::new::<pyo3::exceptions::PyValueError, _>("无效的重投数值"))?;
                        DiceModifier::Reroll(num)
                    }
                    s if s.starts_with("ro") => {
                        let num = s[2..].parse::<i32>()
                            .map_err(|_| PyErr::new::<pyo3::exceptions::PyValueError, _>("无效的条件重投数值"))?;
                        DiceModifier::RerollOnce(num)
                    }
                    s if s.starts_with("kh") => {
                        let num = s[2..].parse::<i32>()
                            .map_err(|_| PyErr::new::<pyo3::exceptions::PyValueError, _>("无效的取高数值"))?;
                        DiceModifier::KeepHigh(num)
                    }
                    s if s.starts_with("kl") => {
                        let num = s[2..].parse::<i32>()
                            .map_err(|_| PyErr::new::<pyo3::exceptions::PyValueError, _>("无效的取低数值"))?;
                        DiceModifier::KeepLow(num)
                    }
                    s if s.starts_with("dh") => {
                        let num = s[2..].parse::<i32>()
                            .map_err(|_| PyErr::new::<pyo3::exceptions::PyValueError, _>("无效的丢弃高数值"))?;
                        DiceModifier::DropHigh(num)
                    }
                    s if s.starts_with("dl") => {
                        let num = s[2..].parse::<i32>()
                            .map_err(|_| PyErr::new::<pyo3::exceptions::PyValueError, _>("无效的丢弃低数值"))?;
                        DiceModifier::DropLow(num)
                    }
                    _ => return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("未知的修饰符")),
                };
                dice_modifiers.push(modifier);
            }
            
            let dice = DiceRoll {
                count: dice_count,
                sides: dice_sides,
                modifiers: dice_modifiers,
            };
            
            let rolls = calculator.roll_dice(&dice)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
            
            let total: i32 = rolls.iter().flatten().sum();
            let details = format!("{}d{}{} = {} (详情: {:?})", 
                dice_count, dice_sides, 
                calculator.modifiers_to_string(&dice.modifiers),
                total, rolls);
            
            let dict = PyDict::new(py);
            dict.set_item("total", total)?;
            dict.set_item("rolls", rolls)?;
            dict.set_item("details", &details)?;
            
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
        
        let result = calculator.evaluate_expression(&expr)
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
pub fn roll_simple(dice_count: i32, dice_sides: i32) -> PyResult<i32> {
    let mut calculator = DiceCalculator::new();
    let dice = DiceRoll {
        count: dice_count,
        sides: dice_sides,
        modifiers: vec![],
    };
    
    let rolls = calculator.roll_dice(&dice)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
    
    Ok(rolls.iter().flatten().sum())
}
