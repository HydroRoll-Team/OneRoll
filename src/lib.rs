//! OneRoll - High-performance dice expression parser
//!
//! This is a dice expression parser implemented in Rust and bound to Python through PyO3.
//! Supports complex dice expression parsing, various modifiers and mathematical operations.

use pyo3::prelude::*;

mod errors;
mod types;
mod calculator;
mod parser;
mod python_bindings;

pub use errors::DiceError;
pub use types::{DiceResult, DiceRoll, DiceModifier, Expression};
pub use calculator::DiceCalculator;
pub use parser::DiceParser;
pub use python_bindings::{OneRoll, roll_dice, roll_simple};

#[pymodule]
fn _core(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(roll_dice, m)?)?;
    m.add_function(wrap_pyfunction!(roll_simple, m)?)?;
    m.add_class::<OneRoll>()?;
    Ok(())
}