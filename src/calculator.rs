use crate::errors::DiceError;
use crate::types::{DiceModifier, DiceResult, DiceRoll, Expression, VariableStore};
use rand::Rng;

pub struct DiceCalculator {
    pub variables: VariableStore,
}

impl DiceCalculator {
    pub fn new() -> Self {
        Self {
            variables: VariableStore::new(),
        }
    }

    pub fn roll_dice(&mut self, dice: &DiceRoll) -> Result<Vec<Vec<i32>>, DiceError> {
        if dice.count <= 0 || dice.sides <= 0 {
            return Err(DiceError::InvalidExpression(
                "骰子数量和面数必须大于0".to_string(),
            ));
        }

        let mut rolls = Vec::new();
        
        for _ in 0..dice.count {
            let mut roll = rand::random::<u32>() % dice.sides as u32 + 1;
            let mut final_rolls = vec![roll as i32];
            
            // handle exploded throwing
            for modifier in &dice.modifiers {
                match modifier {
                    DiceModifier::Explode => {
                        while roll == dice.sides as u32 {
                            roll = rand::random::<u32>() % dice.sides as u32 + 1;
                            final_rolls.push(roll as i32);
                        }
                    }
                    DiceModifier::ExplodeAlias => {
                        while roll == dice.sides as u32 {
                            roll = rand::random::<u32>() % dice.sides as u32 + 1;
                            final_rolls.push(roll as i32);
                        }
                    }
                    _ => {}
                }
            }
            
            // handle reroll variants
            for modifier in &dice.modifiers {
                match modifier {
                    DiceModifier::Reroll(threshold) => {
                        if final_rolls.iter().any(|&r| r <= *threshold) {
                            let new_roll = rand::random::<u32>() % dice.sides as u32 + 1;
                            final_rolls = vec![new_roll as i32];
                        }
                    }
                    DiceModifier::RerollOnce(threshold) => {
                        if let Some(pos) = final_rolls.iter().position(|&r| r <= *threshold) {
                            let new_roll = rand::random::<u32>() % dice.sides as u32 + 1;
                            final_rolls[pos] = new_roll as i32;
                        }
                    }
                    DiceModifier::RerollUntil(threshold) => {
                        // keep rolling until > threshold (safety cap)
                        let mut current = *final_rolls.last().unwrap_or(&((roll) as i32));
                        let mut attempts = 0;
                        const MAX_ATTEMPTS: usize = 100;
                        while current <= *threshold && attempts < MAX_ATTEMPTS {
                            let new_roll = rand::random::<u32>() % dice.sides as u32 + 1;
                            current = new_roll as i32;
                            final_rolls = vec![current];
                            attempts += 1;
                        }
                    }
                    DiceModifier::RerollAndAdd(threshold) => {
                        // if <= threshold, roll again and add to the last value
                        if final_rolls.iter().any(|&r| r <= *threshold) {
                            let new_roll = rand::random::<u32>() % dice.sides as u32 + 1;
                            let mut sum = final_rolls.iter().sum::<i32>();
                            sum += new_roll as i32;
                            final_rolls = vec![sum];
                        }
                    }
                    _ => {}
                }
            }
            
            rolls.push(final_rolls);
        }
        
        // handle keep alias before global aggregation
        let mut final_rolls = rolls;
        for modifier in &dice.modifiers {
            if let DiceModifier::KeepAlias(n) = modifier {
                let all_values: Vec<i32> = final_rolls.iter().flatten().cloned().collect();
                let mut sorted = all_values;
                sorted.sort_by(|a, b| b.cmp(a));
                final_rolls = sorted.iter().take(*n as usize).map(|&v| vec![v]).collect();
            }
        }

        // handle high/low, discard high/low and unique/sort/count
        for modifier in &dice.modifiers {
            match modifier {
                DiceModifier::KeepHigh(n) => {
                    let all_values: Vec<i32> = final_rolls.iter().flatten().cloned().collect();
                    let mut sorted = all_values;
                    sorted.sort_by(|a, b| b.cmp(a));
                    final_rolls = sorted.iter().take(*n as usize).map(|&v| vec![v]).collect();
                }
                DiceModifier::KeepLow(n) => {
                    let all_values: Vec<i32> = final_rolls.iter().flatten().cloned().collect();
                    let mut sorted = all_values;
                    sorted.sort();
                    final_rolls = sorted.iter().take(*n as usize).map(|&v| vec![v]).collect();
                }
                DiceModifier::DropHigh(n) => {
                    let all_values: Vec<i32> = final_rolls.iter().flatten().cloned().collect();
                    let mut sorted = all_values;
                    sorted.sort_by(|a, b| b.cmp(a));
                    final_rolls = sorted.iter().skip(*n as usize).map(|&v| vec![v]).collect();
                }
                DiceModifier::DropLow(n) => {
                    let all_values: Vec<i32> = final_rolls.iter().flatten().cloned().collect();
                    let mut sorted = all_values;
                    sorted.sort();
                    final_rolls = sorted.iter().skip(*n as usize).map(|&v| vec![v]).collect();
                }
                DiceModifier::ExplodeKeepHigh(n) => {
                    // equivalent to explode then keep high n
                    let all_values: Vec<i32> = final_rolls.iter().flatten().cloned().collect();
                    let mut sorted = all_values;
                    sorted.sort_by(|a, b| b.cmp(a));
                    final_rolls = sorted.iter().take(*n as usize).map(|&v| vec![v]).collect();
                }
                DiceModifier::Unique => {
                    use std::collections::HashSet;
                    let mut seen = HashSet::new();
                    let mut uniques: Vec<i32> = Vec::new();
                    for v in final_rolls.iter().flatten() {
                        if seen.insert(*v) {
                            uniques.push(*v);
                        }
                    }
                    final_rolls = uniques.into_iter().map(|v| vec![v]).collect();
                }
                DiceModifier::Sort => {
                    let mut values: Vec<i32> = final_rolls.iter().flatten().cloned().collect();
                    values.sort();
                    final_rolls = values.into_iter().map(|v| vec![v]).collect();
                }
                DiceModifier::Count(target) => {
                    let values: Vec<i32> = final_rolls.iter().flatten().cloned().collect();
                    let count = values.iter().filter(|&&v| v == *target).count() as i32;
                    final_rolls = vec![vec![count]];
                }
                _ => {}
            }
        }
        
        Ok(final_rolls)
    }

    pub fn evaluate_expression(&mut self, expr: &Expression) -> Result<DiceResult, DiceError> {
        match expr {
            Expression::Number(n) => Ok(DiceResult {
                expression: n.to_string(),
                total: *n,
                rolls: vec![],
                details: format!("{}", n),
                comment: None,
            }),
            Expression::DiceRoll(dice) => {
                let rolls = self.roll_dice(dice)?;
                let total: i32 = rolls.iter().flatten().sum();
                let details = format!(
                    "{}d{}{} = {} (详情: {:?})",
                    dice.count,
                    dice.sides,
                    self.modifiers_to_string(&dice.modifiers),
                    total,
                    rolls
                );
                Ok(DiceResult {
                    expression: format!("{}d{}", dice.count, dice.sides),
                    total,
                    rolls,
                    details,
                    comment: None,
                })
            }
            Expression::Add(left, right) => {
                let left_result = self.evaluate_expression(left)?;
                let right_result = self.evaluate_expression(right)?;
                Ok(DiceResult {
                    expression: format!("({}) + ({})", left_result.expression, right_result.expression),
                    total: left_result.total + right_result.total,
                    rolls: [left_result.rolls, right_result.rolls].concat(),
                    details: format!("{} + {} = {}", left_result.total, right_result.total, left_result.total + right_result.total),
                    comment: None,
                })
            }
            Expression::Subtract(left, right) => {
                let left_result = self.evaluate_expression(left)?;
                let right_result = self.evaluate_expression(right)?;
                Ok(DiceResult {
                    expression: format!("({}) - ({})", left_result.expression, right_result.expression),
                    total: left_result.total - right_result.total,
                    rolls: [left_result.rolls, right_result.rolls].concat(),
                    details: format!("{} - {} = {}", left_result.total, right_result.total, left_result.total - right_result.total),
                    comment: None,
                })
            }
            Expression::Multiply(left, right) => {
                let left_result = self.evaluate_expression(left)?;
                let right_result = self.evaluate_expression(right)?;
                Ok(DiceResult {
                    expression: format!("({}) * ({})", left_result.expression, right_result.expression),
                    total: left_result.total * right_result.total,
                    rolls: [left_result.rolls, right_result.rolls].concat(),
                    details: format!("{} * {} = {}", left_result.total, right_result.total, left_result.total * right_result.total),
                    comment: None,
                })
            }
            Expression::Divide(left, right) => {
                let left_result = self.evaluate_expression(left)?;
                let right_result = self.evaluate_expression(right)?;
                if right_result.total == 0 {
                    return Err(DiceError::CalculationError("除零错误".to_string()));
                }
                Ok(DiceResult {
                    expression: format!("({}) / ({})", left_result.expression, right_result.expression),
                    total: left_result.total / right_result.total,
                    rolls: [left_result.rolls, right_result.rolls].concat(),
                    details: format!("{} / {} = {}", left_result.total, right_result.total, left_result.total / right_result.total),
                    comment: None,
                })
            }
            Expression::Power(left, right) => {
                let left_result = self.evaluate_expression(left)?;
                let right_result = self.evaluate_expression(right)?;
                let result = left_result.total.pow(right_result.total as u32);
                Ok(DiceResult {
                    expression: format!("({}) ^ ({})", left_result.expression, right_result.expression),
                    total: result,
                    rolls: [left_result.rolls, right_result.rolls].concat(),
                    details: format!("{} ^ {} = {}", left_result.total, right_result.total, result),
                    comment: None,
                })
            }
            Expression::Paren(expr) => self.evaluate_expression(expr),
            Expression::WithComment(expr, comment) => {
                let mut result = self.evaluate_expression(expr)?;
                result.comment = comment.clone();
                Ok(result)
            }
        }
    }


    pub fn modifiers_to_string(&self, modifiers: &[DiceModifier]) -> String {
        let mut result = String::new();
        for modifier in modifiers {
            match modifier {
                DiceModifier::Explode => result.push('!'),
                DiceModifier::ExplodeAlias => result.push('e'),
                DiceModifier::ExplodeKeepHigh(n) => result.push_str(&format!("K{}", n)),
                DiceModifier::Reroll(n) => result.push_str(&format!("r{}", n)),
                DiceModifier::RerollOnce(n) => result.push_str(&format!("ro{}", n)),
                DiceModifier::RerollUntil(n) => result.push_str(&format!("R{}", n)),
                DiceModifier::RerollAndAdd(n) => result.push_str(&format!("a{}", n)),
                DiceModifier::KeepAlias(n) => result.push_str(&format!("k{}", n)),
                DiceModifier::KeepHigh(n) => result.push_str(&format!("kh{}", n)),
                DiceModifier::KeepLow(n) => result.push_str(&format!("kl{}", n)),
                DiceModifier::DropHigh(n) => result.push_str(&format!("dh{}", n)),
                DiceModifier::DropLow(n) => result.push_str(&format!("dl{}", n)),
                DiceModifier::Unique => result.push('u'),
                DiceModifier::Sort => result.push('s'),
                DiceModifier::Count(v) => result.push_str(&format!("c{}", v)),
            }
        }
        result
    }

}
