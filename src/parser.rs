use crate::errors::DiceError;
use crate::types::{DiceModifier, DiceRoll, Expression};

mod oneroll {
    include!(concat!(env!("OUT_DIR"), "/oneroll_grammar.rs"));
}

use oneroll::{Grammar, Rule};
use pest::Parser;

pub struct DiceParser;

impl DiceParser {
    pub fn parse_expression(input: &str) -> Result<Expression, DiceError> {
        let pairs = Grammar::parse(Rule::main, input)
            .map_err(|e| DiceError::ParseError(e.to_string()))?;
        
        let pair = pairs.peek().unwrap();
        Self::parse_instruction_list(pair)
    }

    fn parse_dice_expr(pair: pest::iterators::Pair<Rule>) -> Result<Expression, DiceError> {
        match pair.as_rule() {
            Rule::main => {
                let inner = pair.into_inner().next().unwrap();
                Self::parse_instruction_list(inner)
            }
            Rule::instruction_list => Self::parse_instruction_list(pair),
            Rule::instruction => {
                let inner = pair.into_inner().next().unwrap();
                match inner.as_rule() {
                    Rule::var_ref => {
                        let mut pairs = inner.into_inner();
                        let n = pairs.next().unwrap().as_str().trim_start_matches('$').parse::<i32>()
                            .map_err(|_| DiceError::ParseError("无效的变量引用".to_string()))?;
                        if n <= 0 { return Err(DiceError::ParseError("变量引用必须>=1".to_string())); }
                        
                        let mut modifiers = Vec::new();
                        if let Some(modifiers_pair) = pairs.next() {
                            for modifier_pair in modifiers_pair.into_inner() {
                                let modifier = Self::parse_modifier(modifier_pair)?;
                                modifiers.push(modifier);
                            }
                        }
                        
                        // Store variable reference with modifiers for special handling
                        Ok(Expression::VariableRefWithModifiers(n as usize, modifiers))
                    }
                    _ => Self::parse_dice_expr(inner),
                }
            }
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
                                _ => return Err(DiceError::ParseError(format!("未知操作符: {}", op))),
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
            _ => Err(DiceError::ParseError(format!("期望骰子表达式，得到: {:?}", pair.as_rule()))),
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
                        let num = inner.as_str().parse::<i32>()
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
        let count = pairs.next().unwrap().as_str().parse::<i32>()
            .map_err(|_| DiceError::ParseError("无效的骰子数量".to_string()))?;
        let sides = pairs.next().unwrap().as_str().parse::<i32>()
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
                        let num = inner.into_inner().next().unwrap().as_str().parse::<i32>()
                            .map_err(|_| DiceError::ParseError("无效的ExplodeKeepHigh数值".to_string()))?;
                        Ok(DiceModifier::ExplodeKeepHigh(num))
                    }
                    Rule::reroll => {
                        let num = inner.into_inner().next().unwrap().as_str().parse::<i32>()
                            .map_err(|_| DiceError::ParseError("无效的重投数值".to_string()))?;
                        Ok(DiceModifier::Reroll(num))
                    }
                    Rule::reroll_once => {
                        let num = inner.into_inner().next().unwrap().as_str().parse::<i32>()
                            .map_err(|_| DiceError::ParseError("无效的条件重投数值".to_string()))?;
                        Ok(DiceModifier::RerollOnce(num))
                    }
                    Rule::reroll_until => {
                        let num = inner.into_inner().next().unwrap().as_str().parse::<i32>()
                            .map_err(|_| DiceError::ParseError("无效的直到重投数值".to_string()))?;
                        Ok(DiceModifier::RerollUntil(num))
                    }
                    Rule::reroll_add => {
                        let num = inner.into_inner().next().unwrap().as_str().parse::<i32>()
                            .map_err(|_| DiceError::ParseError("无效的重投并相加数值".to_string()))?;
                        Ok(DiceModifier::RerollAndAdd(num))
                    }
                    Rule::keep_alias => {
                        let num = inner.into_inner().next().unwrap().as_str().parse::<i32>()
                            .map_err(|_| DiceError::ParseError("无效的取高数值".to_string()))?;
                        Ok(DiceModifier::KeepAlias(num))
                    }
                    Rule::keep_high => {
                        let num = inner.into_inner().next().unwrap().as_str().parse::<i32>()
                            .map_err(|_| DiceError::ParseError("无效的取高数值".to_string()))?;
                        Ok(DiceModifier::KeepHigh(num))
                    }
                    Rule::keep_low => {
                        let num = inner.into_inner().next().unwrap().as_str().parse::<i32>()
                            .map_err(|_| DiceError::ParseError("无效的取低数值".to_string()))?;
                        Ok(DiceModifier::KeepLow(num))
                    }
                    Rule::drop_high => {
                        let num = inner.into_inner().next().unwrap().as_str().parse::<i32>()
                            .map_err(|_| DiceError::ParseError("无效的丢弃高数值".to_string()))?;
                        Ok(DiceModifier::DropHigh(num))
                    }
                    Rule::drop_low => {
                        let num = inner.into_inner().next().unwrap().as_str().parse::<i32>()
                            .map_err(|_| DiceError::ParseError("无效的丢弃低数值".to_string()))?;
                        Ok(DiceModifier::DropLow(num))
                    }
                    Rule::unique => Ok(DiceModifier::Unique),
                    Rule::sort => Ok(DiceModifier::Sort),
                    Rule::count => {
                        let num = inner.into_inner().next().unwrap().as_str().parse::<i32>()
                            .map_err(|_| DiceError::ParseError("无效的计数数值".to_string()))?;
                        Ok(DiceModifier::Count(num))
                    }
                    Rule::merge => Ok(DiceModifier::Merge),
                    Rule::group => {
                        let s = inner.as_str();
                        let show_structure = s.starts_with("gs");
                        let inn = inner.into_inner();
                        // last number
                        let num = inn.last().unwrap().as_str().parse::<i32>()
                            .map_err(|_| DiceError::ParseError("无效的分组阈值".to_string()))?;
                        Ok(DiceModifier::Group { threshold: num, show_structure })
                    }
                    _ => Err(DiceError::ParseError("未知的修饰符".to_string())),
                }
            }
            _ => Err(DiceError::ParseError("期望修饰符".to_string())),
        }
    }

    fn parse_instruction_list(pair: pest::iterators::Pair<Rule>) -> Result<Expression, DiceError> {
        match pair.as_rule() {
            Rule::instruction_list => {
                let mut exprs = Vec::new();
                for p in pair.into_inner() {
                    if p.as_rule() == Rule::instruction {
                        let e = Self::parse_dice_expr(p)?;
                        exprs.push(e);
                    }
                }
                if exprs.len() == 1 {
                    Ok(exprs.into_iter().next().unwrap())
                } else {
                    Ok(Expression::Sequence(exprs))
                }
            }
            _ => Self::parse_dice_expr(pair),
        }
    }

    fn parse_comment(pair: pest::iterators::Pair<Rule>) -> Result<Option<String>, DiceError> {
        match pair.as_rule() {
            Rule::comment => {
                let comment = pair.as_str().trim_start_matches('#').trim();
                Ok(if comment.is_empty() { None } else { Some(comment.to_string()) })
            }
            _ => Ok(None),
        }
    }


}
