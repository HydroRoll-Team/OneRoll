use crate::errors::{DiceError, ErrorPhase, SourceSpan};
use crate::resource::ResourcePolicy;
use crate::types::{DiceModifier, DiceRoll, Expression, Program};

mod oneroll {
    include!(concat!(env!("OUT_DIR"), "/oneroll_grammar.rs"));
}

use oneroll::{Grammar, Rule};
use pest::error::{Error as PestError, ErrorVariant, InputLocation};
use pest::Parser;

pub struct DiceParser;

impl DiceParser {
    pub fn parse_expression(input: &str) -> Result<Expression, DiceError> {
        Self::parse_expression_with_policy(input, &ResourcePolicy::default())
    }

    pub fn parse_expression_with_policy(
        input: &str,
        policy: &ResourcePolicy,
    ) -> Result<Expression, DiceError> {
        let result = (|| {
            let program = Self::parse_program_with_policy(input, policy)?;
            if program.instructions.len() != 1 {
                return Err(DiceError::ParseError(
                    "roll() 只接受一条指令；多条指令请使用 run()".to_string(),
                ));
            }

            let mut expr = program.instructions.into_iter().next().unwrap();
            if let Some(comment) = program.comment {
                expr = Expression::WithComment(Box::new(expr), Some(comment));
            }
            let nodes = 2usize.saturating_add(Self::expression_ast_nodes(&expr));
            let limit = policy.require("ast_nodes");
            if nodes > limit {
                return Err(DiceError::ResourceLimitExceeded {
                    resource: "ast_nodes",
                    used: 0,
                    requested: nodes,
                    limit,
                });
            }
            Ok(expr)
        })();
        result.map_err(|error| error.with_phase(ErrorPhase::Parse))
    }

    pub fn parse_program(input: &str) -> Result<Program, DiceError> {
        Self::parse_program_with_policy(input, &ResourcePolicy::default())
    }

    pub fn parse_program_with_policy(
        input: &str,
        policy: &ResourcePolicy,
    ) -> Result<Program, DiceError> {
        let result = (|| {
            let source_bytes = policy.require("source_bytes");
            if input.len() > source_bytes {
                return Err(DiceError::ResourceLimitExceeded {
                    resource: "source_bytes",
                    used: 0,
                    requested: input.len(),
                    limit: source_bytes,
                });
            }
            Self::validate_parse_depth(input, policy.require("parse_depth"))?;

            let mut pairs = Grammar::parse(Rule::program, input)
                .map_err(|error| Self::structured_parse_error(input, error))?;

            let pair = pairs
                .next()
                .ok_or_else(|| DiceError::ParseError("程序不能为空".to_string()))?;
            let mut instructions = Vec::new();
            let mut comment = None;

            for inner in pair.into_inner() {
                match inner.as_rule() {
                    Rule::instruction => {
                        let instruction_limit = policy.require("parsed_instructions");
                        if instructions.len() >= instruction_limit {
                            return Err(DiceError::ProgramInstructionLimitExceeded {
                                limit: instruction_limit,
                            });
                        }
                        let expression = inner
                            .into_inner()
                            .next()
                            .ok_or_else(|| DiceError::ParseError("指令不能为空".to_string()))?;
                        instructions.push(Self::parse_dice_expr(expression)?);
                    }
                    Rule::comment => comment = Self::parse_comment(inner)?,
                    Rule::EOI => {}
                    _ => {
                        return Err(DiceError::ParseError(format!(
                            "未知的程序节点: {:?}",
                            inner.as_rule()
                        )))
                    }
                }
            }

            if instructions.is_empty() {
                return Err(DiceError::ParseError("程序至少需要一条指令".to_string()));
            }

            let program = Program {
                instructions,
                comment,
            };
            Self::validate_ast_nodes(&program, policy.require("ast_nodes"))?;
            Ok(program)
        })();
        result.map_err(|error| error.with_phase(ErrorPhase::Parse))
    }

    fn structured_parse_error(input: &str, error: PestError<Rule>) -> DiceError {
        let (start_byte, end_byte) = match error.location {
            InputLocation::Pos(position) => {
                let end = input[position..]
                    .chars()
                    .next()
                    .map(|character| position + character.len_utf8())
                    .unwrap_or(position);
                (position, end)
            }
            InputLocation::Span((start, end)) => (start, end),
        };
        let mut expected = match &error.variant {
            ErrorVariant::ParsingError { positives, .. } => positives
                .iter()
                .map(|rule| format!("{rule:?}"))
                .filter(|rule| rule != "EOI")
                .collect::<Vec<_>>(),
            ErrorVariant::CustomError { .. } => Vec::new(),
        };
        expected.sort();
        expected.dedup();
        if expected.is_empty() {
            expected.push("expression".to_string());
        }

        DiceError::ParseSyntax {
            message: error.to_string(),
            span: SourceSpan {
                start_byte,
                end_byte,
            },
            expected,
        }
    }

    fn validate_ast_nodes(program: &Program, limit: usize) -> Result<(), DiceError> {
        let mut nodes = 1usize;
        for instruction in &program.instructions {
            nodes = nodes
                .checked_add(1)
                .and_then(|value| value.checked_add(Self::expression_ast_nodes(instruction)))
                .unwrap_or(usize::MAX);
            if nodes > limit {
                return Err(DiceError::ResourceLimitExceeded {
                    resource: "ast_nodes",
                    used: 0,
                    requested: nodes,
                    limit,
                });
            }
        }
        Ok(())
    }

    fn expression_ast_nodes(expression: &Expression) -> usize {
        let child_nodes = match expression {
            Expression::Number(_) => 0,
            Expression::DiceRoll(dice) => dice.modifiers.len(),
            Expression::Add(left, right)
            | Expression::Subtract(left, right)
            | Expression::Multiply(left, right)
            | Expression::Divide(left, right)
            | Expression::Power(left, right) => {
                Self::expression_ast_nodes(left).saturating_add(Self::expression_ast_nodes(right))
            }
            Expression::Paren(inner) | Expression::WithComment(inner, _) => {
                Self::expression_ast_nodes(inner)
            }
        };
        1usize.saturating_add(child_nodes)
    }

    fn validate_parse_depth(input: &str, limit: usize) -> Result<(), DiceError> {
        let mut depth = 0usize;
        let mut quote = None;
        let mut escaped = false;
        let mut comment = false;

        for character in input.chars() {
            if comment {
                if character == '\n' || character == '\r' {
                    comment = false;
                }
                continue;
            }
            if let Some(delimiter) = quote {
                if escaped {
                    escaped = false;
                } else if character == '\\' {
                    escaped = true;
                } else if character == delimiter {
                    quote = None;
                }
                continue;
            }

            match character {
                '#' => comment = true,
                '\'' | '"' => quote = Some(character),
                '(' | '[' | '{' => {
                    depth = depth
                        .checked_add(1)
                        .ok_or(DiceError::ResourceLimitExceeded {
                            resource: "parse_depth",
                            used: depth,
                            requested: 1,
                            limit,
                        })?;
                    if depth > limit {
                        return Err(DiceError::ResourceLimitExceeded {
                            resource: "parse_depth",
                            used: depth - 1,
                            requested: 1,
                            limit,
                        });
                    }
                }
                ')' | ']' | '}' => depth = depth.saturating_sub(1),
                _ => {}
            }
        }

        Ok(())
    }

    fn parse_dice_expr(pair: pest::iterators::Pair<Rule>) -> Result<Expression, DiceError> {
        match pair.as_rule() {
            Rule::dice_expr => {
                let mut pairs = pair.into_inner();
                let mut expr = Self::parse_dice_term(pairs.next().unwrap())?;

                while let Some(pair) = pairs.next() {
                    match pair.as_rule() {
                        Rule::op => {
                            let op = pair.as_str();
                            let right = Self::parse_dice_term(pairs.next().unwrap())?;

                            expr = match op {
                                "+" => Expression::Add(Box::new(expr), Box::new(right)),
                                "-" => Expression::Subtract(Box::new(expr), Box::new(right)),
                                "*" => Expression::Multiply(Box::new(expr), Box::new(right)),
                                "/" => Expression::Divide(Box::new(expr), Box::new(right)),
                                "^" => Expression::Power(Box::new(expr), Box::new(right)),
                                _ => {
                                    return Err(DiceError::ParseError(format!(
                                        "未知操作符: {}",
                                        op
                                    )))
                                }
                            };
                        }
                        Rule::comment => {
                            let comment = Self::parse_comment(pair)?;
                            if let Some(comment_text) = comment {
                                expr = Expression::WithComment(Box::new(expr), Some(comment_text));
                            }
                        }
                        _ => {}
                    }
                }
                Ok(expr)
            }
            _ => Err(DiceError::ParseError(format!(
                "期望骰子表达式，得到: {:?}",
                pair.as_rule()
            ))),
        }
    }

    fn parse_dice_term(pair: pest::iterators::Pair<Rule>) -> Result<Expression, DiceError> {
        match pair.as_rule() {
            Rule::dice_term => {
                let inner = pair.into_inner().next().unwrap();
                match inner.as_rule() {
                    Rule::dice_roll => Self::parse_dice_roll(inner),
                    Rule::paren_expr => {
                        let expr = Self::parse_dice_expr(inner.into_inner().next().unwrap())?;
                        Ok(Expression::Paren(Box::new(expr)))
                    }
                    Rule::number => {
                        let num = inner
                            .as_str()
                            .parse::<i64>()
                            .map_err(|_| DiceError::ParseError("无效数字".to_string()))?;
                        Ok(Expression::Number(num))
                    }
                    _ => Err(DiceError::ParseError("无效的骰子项".to_string())),
                }
            }
            _ => Err(DiceError::ParseError("期望骰子项".to_string())),
        }
    }

    fn parse_dice_roll(pair: pest::iterators::Pair<Rule>) -> Result<Expression, DiceError> {
        let mut pairs = pair.into_inner();
        let count = pairs
            .next()
            .unwrap()
            .as_str()
            .parse::<i32>()
            .map_err(|_| DiceError::ParseError("无效的骰子数量".to_string()))?;
        let sides = pairs
            .next()
            .unwrap()
            .as_str()
            .parse::<i32>()
            .map_err(|_| DiceError::ParseError("无效的骰子面数".to_string()))?;

        let mut modifiers = Vec::new();
        if let Some(modifiers_pair) = pairs.next() {
            for modifier_pair in modifiers_pair.into_inner() {
                let modifier = Self::parse_modifier(modifier_pair)?;
                modifiers.push(modifier);
            }
        }

        Ok(Expression::DiceRoll(DiceRoll {
            count,
            sides,
            modifiers,
        }))
    }

    fn parse_modifier(pair: pest::iterators::Pair<Rule>) -> Result<DiceModifier, DiceError> {
        match pair.as_rule() {
            Rule::modifier => {
                let inner = pair.into_inner().next().unwrap();
                match inner.as_rule() {
                    Rule::explode => Ok(DiceModifier::Explode),
                    Rule::explode_alias => Ok(DiceModifier::ExplodeAlias),
                    Rule::explode_keep_high => {
                        let num = inner
                            .into_inner()
                            .next()
                            .unwrap()
                            .as_str()
                            .parse::<i32>()
                            .map_err(|_| {
                                DiceError::ParseError("无效的ExplodeKeepHigh数值".to_string())
                            })?;
                        Ok(DiceModifier::ExplodeKeepHigh(num))
                    }
                    Rule::reroll => {
                        let num = inner
                            .into_inner()
                            .next()
                            .unwrap()
                            .as_str()
                            .parse::<i32>()
                            .map_err(|_| DiceError::ParseError("无效的重投数值".to_string()))?;
                        Ok(DiceModifier::Reroll(num))
                    }
                    Rule::reroll_once => {
                        let num = inner
                            .into_inner()
                            .next()
                            .unwrap()
                            .as_str()
                            .parse::<i32>()
                            .map_err(|_| DiceError::ParseError("无效的条件重投数值".to_string()))?;
                        Ok(DiceModifier::RerollOnce(num))
                    }
                    Rule::reroll_until => {
                        let num = inner
                            .into_inner()
                            .next()
                            .unwrap()
                            .as_str()
                            .parse::<i32>()
                            .map_err(|_| DiceError::ParseError("无效的直到重投数值".to_string()))?;
                        Ok(DiceModifier::RerollUntil(num))
                    }
                    Rule::reroll_add => {
                        let num = inner
                            .into_inner()
                            .next()
                            .unwrap()
                            .as_str()
                            .parse::<i32>()
                            .map_err(|_| {
                                DiceError::ParseError("无效的重投并相加数值".to_string())
                            })?;
                        Ok(DiceModifier::RerollAndAdd(num))
                    }
                    Rule::keep_alias => {
                        let num = inner
                            .into_inner()
                            .next()
                            .unwrap()
                            .as_str()
                            .parse::<i32>()
                            .map_err(|_| DiceError::ParseError("无效的取高数值".to_string()))?;
                        Ok(DiceModifier::KeepAlias(num))
                    }
                    Rule::keep_high => {
                        let num = inner
                            .into_inner()
                            .next()
                            .unwrap()
                            .as_str()
                            .parse::<i32>()
                            .map_err(|_| DiceError::ParseError("无效的取高数值".to_string()))?;
                        Ok(DiceModifier::KeepHigh(num))
                    }
                    Rule::keep_low => {
                        let num = inner
                            .into_inner()
                            .next()
                            .unwrap()
                            .as_str()
                            .parse::<i32>()
                            .map_err(|_| DiceError::ParseError("无效的取低数值".to_string()))?;
                        Ok(DiceModifier::KeepLow(num))
                    }
                    Rule::drop_high => {
                        let num = inner
                            .into_inner()
                            .next()
                            .unwrap()
                            .as_str()
                            .parse::<i32>()
                            .map_err(|_| DiceError::ParseError("无效的丢弃高数值".to_string()))?;
                        Ok(DiceModifier::DropHigh(num))
                    }
                    Rule::drop_low => {
                        let num = inner
                            .into_inner()
                            .next()
                            .unwrap()
                            .as_str()
                            .parse::<i32>()
                            .map_err(|_| DiceError::ParseError("无效的丢弃低数值".to_string()))?;
                        Ok(DiceModifier::DropLow(num))
                    }
                    Rule::unique => Ok(DiceModifier::Unique),
                    Rule::sort => Ok(DiceModifier::Sort),
                    Rule::count => {
                        let num = inner
                            .into_inner()
                            .next()
                            .unwrap()
                            .as_str()
                            .parse::<i32>()
                            .map_err(|_| DiceError::ParseError("无效的计数数值".to_string()))?;
                        Ok(DiceModifier::Count(num))
                    }
                    _ => Err(DiceError::ParseError("未知的修饰符".to_string())),
                }
            }
            _ => Err(DiceError::ParseError("期望修饰符".to_string())),
        }
    }

    fn parse_comment(pair: pest::iterators::Pair<Rule>) -> Result<Option<String>, DiceError> {
        match pair.as_rule() {
            Rule::comment => {
                let comment = pair.as_str().trim_start_matches('#').trim();
                Ok(if comment.is_empty() {
                    None
                } else {
                    Some(comment.to_string())
                })
            }
            _ => Ok(None),
        }
    }
}
