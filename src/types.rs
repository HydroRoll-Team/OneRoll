use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DiceResult {
    pub expression: String,
    pub total: i32,
    pub rolls: Vec<Vec<i32>>,
    pub details: String,
    pub comment: Option<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct DiceRoll {
    pub count: i32,
    pub sides: i32,
    pub modifiers: Vec<DiceModifier>,
}

#[derive(Debug, Clone, PartialEq)]
pub enum DiceModifier {
    Explode,           // !
    ExplodeAlias,      // e (alias of !)
    ExplodeKeepHigh(i32), // KX == explode then keep high X
    Reroll(i32),       // rX
    RerollOnce(i32),   // roX
    RerollUntil(i32),  // RX (until > X; with cap)
    RerollAndAdd(i32), // aX (reroll if <= X and add)
    KeepAlias(i32),    // kX == khX
    KeepHigh(i32),     // khX
    KeepLow(i32),      // klX
    DropHigh(i32),     // dhX
    DropLow(i32),      // dlX
    Unique,            // u
    Sort,              // s (sort results)
    Count(i32),        // cV (count value V)
}


#[derive(Debug, Clone)]
pub enum Expression {
    Number(i32),
    DiceRoll(DiceRoll),
    Add(Box<Expression>, Box<Expression>),
    Subtract(Box<Expression>, Box<Expression>),
    Multiply(Box<Expression>, Box<Expression>),
    Divide(Box<Expression>, Box<Expression>),
    Power(Box<Expression>, Box<Expression>),
    Paren(Box<Expression>),
    WithComment(Box<Expression>, Option<String>),
}

// TODO: Variable storage
#[derive(Debug, Clone, Default)]
pub struct VariableStore {
    pub variables: HashMap<String, i32>,
}

impl VariableStore {
    pub fn new() -> Self {
        Self {
            variables: HashMap::new(),
        }
    }
    
    pub fn set(&mut self, name: &str, value: i32) {
        self.variables.insert(name.to_string(), value);
    }
    
    pub fn get(&self, name: &str) -> Option<i32> {
        self.variables.get(name).copied()
    }
}
