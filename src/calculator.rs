use crate::errors::DiceError;
use crate::resource::{ExecutionBudget, ResourcePolicy};
use crate::types::{
    DiceModifier, DiceResult, DiceRoll, Expression, Program, ProgramResult, VariableStore,
};
use serde::Serialize;

pub struct DiceCalculator {
    pub variables: VariableStore,
    policy: ResourcePolicy,
    budget: ExecutionBudget,
    legacy_roll_limit: Option<usize>,
    legacy_generated_rolls: usize,
}

impl DiceCalculator {
    pub fn new() -> Self {
        Self::with_policy(ResourcePolicy::default())
    }

    pub fn with_policy(policy: ResourcePolicy) -> Self {
        Self {
            variables: VariableStore::new(),
            budget: ExecutionBudget::new(policy.clone()),
            policy,
            legacy_roll_limit: None,
            legacy_generated_rolls: 0,
        }
    }

    pub fn with_roll_limit(max_generated_rolls: usize) -> Self {
        let policy = ResourcePolicy::default();
        Self {
            variables: VariableStore::new(),
            budget: ExecutionBudget::new(policy.clone()),
            policy,
            legacy_roll_limit: Some(max_generated_rolls),
            legacy_generated_rolls: 0,
        }
    }

    fn reset_request_budget(&mut self) {
        self.budget = ExecutionBudget::new(self.policy.clone());
        self.legacy_generated_rolls = 0;
    }

    fn charge_instruction_activation(&mut self) -> Result<(), DiceError> {
        self.budget.charge("executed_instructions", 1)?;
        self.budget.charge("work_units", 1)
    }

    fn roll_face(&mut self, sides: i32) -> Result<u32, DiceError> {
        if let Some(limit) = self.legacy_roll_limit {
            if self.legacy_generated_rolls >= limit {
                return Err(DiceError::BudgetExceeded { limit });
            }
            self.legacy_generated_rolls += 1;
        } else {
            self.budget.charge("generated_values", 1)?;
            self.budget.charge("rng_words", 1)?;
        }
        self.budget.charge("work_units", 1)?;
        Ok(rand::random::<u32>() % sides as u32 + 1)
    }

    pub fn roll_dice(&mut self, dice: &DiceRoll) -> Result<Vec<Vec<i32>>, DiceError> {
        self.reset_request_budget();
        self.charge_instruction_activation()?;
        let rolls = self.roll_dice_with_budget(dice)?;
        self.charge_output_items_for_rolls(&rolls)?;
        self.charge_serialized_output(&rolls)?;
        Ok(rolls)
    }

    pub fn roll_simple(&mut self, dice: &DiceRoll) -> Result<i32, DiceError> {
        self.reset_request_budget();
        self.charge_instruction_activation()?;
        let rolls = self.roll_dice_with_budget(dice)?;
        let total = rolls.iter().flatten().sum();
        self.budget.charge("output_items", 1)?;
        self.charge_serialized_output(&total)?;
        Ok(total)
    }

    fn roll_dice_with_budget(&mut self, dice: &DiceRoll) -> Result<Vec<Vec<i32>>, DiceError> {
        if dice.count <= 0 || dice.sides <= 0 {
            return Err(DiceError::InvalidExpression(
                "骰子数量和面数必须大于0".to_string(),
            ));
        }

        let source_items = usize::try_from(dice.count).map_err(|_| {
            DiceError::InvalidExpression("骰子数量必须可以表示为资源计数".to_string())
        })?;
        self.budget.ensure("source_items", source_items)?;
        self.budget.ensure("collection_items", source_items)?;

        let mut rolls = Vec::with_capacity(source_items);
        let mut collected_values = 0usize;

        for _ in 0..dice.count {
            let mut roll = self.roll_face(dice.sides)?;
            collected_values = collected_values.saturating_add(1);
            self.budget.ensure("collection_items", collected_values)?;
            let mut final_rolls = vec![roll as i32];

            // handle exploded throwing
            for modifier in &dice.modifiers {
                match modifier {
                    DiceModifier::Explode => {
                        while roll == dice.sides as u32 {
                            roll = self.roll_face(dice.sides)?;
                            collected_values = collected_values.saturating_add(1);
                            self.budget.ensure("collection_items", collected_values)?;
                            final_rolls.push(roll as i32);
                        }
                    }
                    DiceModifier::ExplodeAlias => {
                        while roll == dice.sides as u32 {
                            roll = self.roll_face(dice.sides)?;
                            collected_values = collected_values.saturating_add(1);
                            self.budget.ensure("collection_items", collected_values)?;
                            final_rolls.push(roll as i32);
                        }
                    }
                    _ => {}
                }
            }

            // handle reroll variants
            for modifier in &dice.modifiers {
                match modifier {
                    DiceModifier::Reroll(threshold)
                        if final_rolls.iter().any(|&r| r <= *threshold) =>
                    {
                        let new_roll = self.roll_face(dice.sides)?;
                        final_rolls = vec![new_roll as i32];
                    }
                    DiceModifier::RerollOnce(threshold) => {
                        if let Some(pos) = final_rolls.iter().position(|&r| r <= *threshold) {
                            let new_roll = self.roll_face(dice.sides)?;
                            final_rolls[pos] = new_roll as i32;
                        }
                    }
                    DiceModifier::RerollUntil(threshold) => {
                        // keep rolling until > threshold; the shared roll budget
                        // bounds expressions that can never satisfy the condition.
                        let mut current = *final_rolls.last().unwrap_or(&((roll) as i32));
                        while current <= *threshold {
                            let new_roll = self.roll_face(dice.sides)?;
                            current = new_roll as i32;
                            final_rolls = vec![current];
                        }
                    }
                    // if <= threshold, roll again and add to the last value
                    DiceModifier::RerollAndAdd(threshold)
                        if final_rolls.iter().any(|&r| r <= *threshold) =>
                    {
                        let new_roll = self.roll_face(dice.sides)?;
                        let mut sum = final_rolls.iter().sum::<i32>();
                        sum += new_roll as i32;
                        final_rolls = vec![sum];
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
                self.charge_modifier_work(&final_rolls)?;
                let all_values: Vec<i32> = final_rolls.iter().flatten().cloned().collect();
                let mut sorted = all_values;
                sorted.sort_by(|a, b| b.cmp(a));
                final_rolls = sorted.iter().take(*n as usize).map(|&v| vec![v]).collect();
            }
        }

        // handle high/low, discard high/low and unique/sort/count
        for modifier in &dice.modifiers {
            if !matches!(modifier, DiceModifier::KeepAlias(_)) {
                self.charge_modifier_work(&final_rolls)?;
            }
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

        self.budget
            .ensure("collection_items", Self::roll_item_count(&final_rolls))?;
        Ok(final_rolls)
    }

    fn roll_item_count(rolls: &[Vec<i32>]) -> usize {
        rolls
            .iter()
            .fold(0usize, |total, values| total.saturating_add(values.len()))
    }

    fn charge_modifier_work(&mut self, rolls: &[Vec<i32>]) -> Result<(), DiceError> {
        self.budget
            .charge("work_units", Self::roll_item_count(rolls))
    }

    fn charge_output_items_for_rolls(&mut self, rolls: &[Vec<i32>]) -> Result<(), DiceError> {
        self.budget
            .charge("output_items", Self::roll_item_count(rolls))
    }

    fn charge_output_items_for_result(&mut self, result: &DiceResult) -> Result<(), DiceError> {
        self.budget.charge(
            "output_items",
            1usize.saturating_add(Self::roll_item_count(&result.rolls)),
        )
    }

    fn charge_serialized_output<T: Serialize>(&mut self, value: &T) -> Result<(), DiceError> {
        let bytes = serde_json::to_vec(value)
            .map_err(|error| DiceError::CalculationError(error.to_string()))?
            .len();
        self.budget.charge("output_bytes", bytes)
    }

    pub fn evaluate_expression(&mut self, expr: &Expression) -> Result<DiceResult, DiceError> {
        self.reset_request_budget();
        self.charge_instruction_activation()?;
        let result = self.evaluate_expression_with_budget(expr)?;
        self.charge_output_items_for_result(&result)?;
        self.charge_serialized_output(&result)?;
        Ok(result)
    }

    pub fn evaluate_program(&mut self, program: &Program) -> Result<ProgramResult, DiceError> {
        self.reset_request_budget();
        self.budget
            .ensure("collection_items", program.instructions.len())?;
        let mut results = Vec::with_capacity(program.instructions.len());
        for instruction in &program.instructions {
            self.charge_instruction_activation()?;
            let result = self.evaluate_expression_with_budget(instruction)?;
            self.charge_output_items_for_result(&result)?;
            results.push(result);
        }

        let result = ProgramResult {
            results,
            comment: program.comment.clone(),
        };
        self.charge_serialized_output(&result)?;
        Ok(result)
    }

    pub fn evaluate_batch(
        &mut self,
        expression: &Expression,
        samples: usize,
    ) -> Result<Vec<DiceResult>, DiceError> {
        self.reset_request_budget();
        self.budget.charge("batch_samples", samples)?;
        self.budget.ensure("collection_items", samples)?;
        let mut results = Vec::with_capacity(samples);
        for _ in 0..samples {
            self.charge_instruction_activation()?;
            let result = self.evaluate_expression_with_budget(expression)?;
            self.charge_output_items_for_result(&result)?;
            results.push(result);
        }
        self.charge_serialized_output(&results)?;
        Ok(results)
    }

    fn evaluate_expression_with_budget(
        &mut self,
        expr: &Expression,
    ) -> Result<DiceResult, DiceError> {
        self.budget.enter_nesting()?;
        let result = self.evaluate_expression_node(expr);
        self.budget.leave_nesting();
        result
    }

    fn evaluate_expression_node(&mut self, expr: &Expression) -> Result<DiceResult, DiceError> {
        self.budget.charge("work_units", 1)?;
        match expr {
            Expression::Number(n) => Ok(DiceResult {
                expression: n.to_string(),
                total: *n,
                rolls: vec![],
                details: format!("{}", n),
                comment: None,
            }),
            Expression::DiceRoll(dice) => {
                let rolls = self.roll_dice_with_budget(dice)?;
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
                let left_result = self.evaluate_expression_with_budget(left)?;
                let right_result = self.evaluate_expression_with_budget(right)?;
                Ok(DiceResult {
                    expression: format!(
                        "({}) + ({})",
                        left_result.expression, right_result.expression
                    ),
                    total: left_result.total + right_result.total,
                    rolls: [left_result.rolls, right_result.rolls].concat(),
                    details: format!(
                        "{} + {} = {}",
                        left_result.total,
                        right_result.total,
                        left_result.total + right_result.total
                    ),
                    comment: None,
                })
            }
            Expression::Subtract(left, right) => {
                let left_result = self.evaluate_expression_with_budget(left)?;
                let right_result = self.evaluate_expression_with_budget(right)?;
                Ok(DiceResult {
                    expression: format!(
                        "({}) - ({})",
                        left_result.expression, right_result.expression
                    ),
                    total: left_result.total - right_result.total,
                    rolls: [left_result.rolls, right_result.rolls].concat(),
                    details: format!(
                        "{} - {} = {}",
                        left_result.total,
                        right_result.total,
                        left_result.total - right_result.total
                    ),
                    comment: None,
                })
            }
            Expression::Multiply(left, right) => {
                let left_result = self.evaluate_expression_with_budget(left)?;
                let right_result = self.evaluate_expression_with_budget(right)?;
                Ok(DiceResult {
                    expression: format!(
                        "({}) * ({})",
                        left_result.expression, right_result.expression
                    ),
                    total: left_result.total * right_result.total,
                    rolls: [left_result.rolls, right_result.rolls].concat(),
                    details: format!(
                        "{} * {} = {}",
                        left_result.total,
                        right_result.total,
                        left_result.total * right_result.total
                    ),
                    comment: None,
                })
            }
            Expression::Divide(left, right) => {
                let left_result = self.evaluate_expression_with_budget(left)?;
                let right_result = self.evaluate_expression_with_budget(right)?;
                if right_result.total == 0 {
                    return Err(DiceError::CalculationError("除零错误".to_string()));
                }
                Ok(DiceResult {
                    expression: format!(
                        "({}) / ({})",
                        left_result.expression, right_result.expression
                    ),
                    total: left_result.total / right_result.total,
                    rolls: [left_result.rolls, right_result.rolls].concat(),
                    details: format!(
                        "{} / {} = {}",
                        left_result.total,
                        right_result.total,
                        left_result.total / right_result.total
                    ),
                    comment: None,
                })
            }
            Expression::Power(left, right) => {
                let left_result = self.evaluate_expression_with_budget(left)?;
                let right_result = self.evaluate_expression_with_budget(right)?;
                let result = left_result.total.pow(right_result.total as u32);
                Ok(DiceResult {
                    expression: format!(
                        "({}) ^ ({})",
                        left_result.expression, right_result.expression
                    ),
                    total: result,
                    rolls: [left_result.rolls, right_result.rolls].concat(),
                    details: format!(
                        "{} ^ {} = {}",
                        left_result.total, right_result.total, result
                    ),
                    comment: None,
                })
            }
            Expression::Paren(expr) => self.evaluate_expression_with_budget(expr),
            Expression::WithComment(expr, comment) => {
                let mut result = self.evaluate_expression_with_budget(expr)?;
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

impl Default for DiceCalculator {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn dice(count: i32, modifiers: Vec<DiceModifier>) -> DiceRoll {
        DiceRoll {
            count,
            sides: 1,
            modifiers,
        }
    }

    fn assert_budget_exceeded<T: std::fmt::Debug>(
        result: Result<T, DiceError>,
        expected_limit: usize,
    ) {
        match result {
            Err(DiceError::BudgetExceeded { limit }) => assert_eq!(limit, expected_limit),
            other => panic!("expected budget exhaustion, got {other:?}"),
        }
    }

    #[test]
    fn explosion_exhausts_the_configured_budget() {
        for modifier in [DiceModifier::Explode, DiceModifier::ExplodeAlias] {
            let mut calculator = DiceCalculator::with_roll_limit(2);

            assert_budget_exceeded(calculator.roll_dice(&dice(1, vec![modifier])), 2);
        }
    }

    #[test]
    fn every_reroll_variant_consumes_the_configured_budget() {
        for modifier in [
            DiceModifier::Reroll(1),
            DiceModifier::RerollOnce(1),
            DiceModifier::RerollUntil(1),
            DiceModifier::RerollAndAdd(1),
        ] {
            let mut calculator = DiceCalculator::with_roll_limit(1);

            assert_budget_exceeded(calculator.roll_dice(&dice(1, vec![modifier])), 1);
        }
    }

    #[test]
    fn combined_rerolls_share_the_configured_budget() {
        let mut calculator = DiceCalculator::with_roll_limit(2);

        assert_budget_exceeded(
            calculator.roll_dice(&dice(
                1,
                vec![DiceModifier::RerollOnce(1), DiceModifier::RerollUntil(1)],
            )),
            2,
        );
    }

    #[test]
    fn initial_dice_count_toward_the_configured_budget() {
        let mut calculator = DiceCalculator::with_roll_limit(2);

        assert_budget_exceeded(calculator.roll_dice(&dice(3, vec![])), 2);
    }

    #[test]
    fn public_rolls_receive_a_fresh_budget() {
        let mut calculator = DiceCalculator::with_roll_limit(1);
        let single_die = dice(1, vec![]);

        assert!(calculator.roll_dice(&single_die).is_ok());
        assert!(calculator.roll_dice(&single_die).is_ok());
    }

    #[test]
    fn expression_terms_share_the_configured_budget() {
        let mut calculator = DiceCalculator::with_roll_limit(2);
        let expression = Expression::Add(
            Box::new(Expression::DiceRoll(dice(2, vec![]))),
            Box::new(Expression::DiceRoll(dice(1, vec![]))),
        );

        assert_budget_exceeded(calculator.evaluate_expression(&expression), 2);
    }
}
