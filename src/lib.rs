//! OneRoll - High-performance dice expression parser
//!
//! This is a dice expression parser implemented in Rust and bound to Python through PyO3.
//! Supports complex dice expression parsing, various modifiers and mathematical operations.

use pyo3::prelude::*;

mod calculator;
mod errors;
mod parser;
mod python_bindings;
pub mod random;
mod resource;
mod types;

#[cfg(test)]
mod conformance_tests;

#[cfg(test)]
mod property_tests;

pub use calculator::DiceCalculator;
pub use errors::DiceError;
pub use parser::DiceParser;
pub use python_bindings::{roll_dice, roll_simple, run_program, OneRoll, PyResourcePolicy};
pub use random::{RandomDescriptor, RandomSeed, RANDOM_PROTOCOL_ID};
pub use resource::ResourcePolicy;
pub use types::{DiceModifier, DiceResult, DiceRoll, Expression, Program, ProgramResult};

#[pymodule]
fn _core(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add_function(wrap_pyfunction!(roll_dice, m)?)?;
    m.add_function(wrap_pyfunction!(run_program, m)?)?;
    m.add_function(wrap_pyfunction!(roll_simple, m)?)?;
    m.add_class::<PyResourcePolicy>()?;
    m.add_class::<OneRoll>()?;
    Ok(())
}
