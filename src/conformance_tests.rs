use serde::Deserialize;

use crate::{DiceCalculator, DiceParser};

#[derive(Deserialize)]
struct Corpus {
    cases: Vec<Case>,
    program_cases: Vec<ProgramCase>,
}

#[derive(Deserialize)]
struct Case {
    id: String,
    expression: String,
    classification: String,
    expect: Expectation,
}

#[derive(Deserialize)]
#[serde(tag = "status", rename_all = "snake_case")]
enum Expectation {
    Success {
        total: i32,
        flattened_rolls: usize,
        comment: String,
    },
    Error {
        message_contains: String,
    },
}

#[derive(Deserialize)]
struct ProgramCase {
    id: String,
    expression: String,
    classification: String,
    expect: ProgramExpectation,
}

#[derive(Deserialize)]
#[serde(tag = "status", rename_all = "snake_case")]
enum ProgramExpectation {
    Success {
        totals: Vec<i32>,
        flattened_rolls: usize,
        comment: String,
    },
    Error {
        message_contains: String,
    },
}

#[test]
fn rust_engine_matches_v1_conformance_corpus() {
    let corpus: Corpus = serde_json::from_str(include_str!("../tests/conformance/v1.json"))
        .expect("v1 conformance corpus must be valid JSON");

    for case in corpus.cases {
        let mut calculator = DiceCalculator::new();
        let observed = DiceParser::parse_expression(&case.expression)
            .and_then(|expression| calculator.evaluate_expression(&expression));
        let context = format!(
            "case={} classification={} expression={:?}",
            case.id, case.classification, case.expression
        );

        match (case.expect, observed) {
            (
                Expectation::Success {
                    total,
                    flattened_rolls,
                    comment,
                },
                Ok(result),
            ) => {
                assert_eq!(result.total, total, "{context}: total changed");
                assert_eq!(
                    result.rolls.iter().map(Vec::len).sum::<usize>(),
                    flattened_rolls,
                    "{context}: generated roll shape changed"
                );
                assert_eq!(
                    result.comment.unwrap_or_default(),
                    comment,
                    "{context}: comment changed"
                );
            }
            (Expectation::Error { message_contains }, Err(error)) => assert!(
                error.to_string().contains(&message_contains),
                "{context}: expected error containing {message_contains:?}, got {error}"
            ),
            (Expectation::Success { .. }, Err(error)) => {
                panic!("{context}: expected success, got {error}")
            }
            (Expectation::Error { message_contains }, Ok(result)) => panic!(
                "{context}: expected error containing {message_contains:?}, got total {}",
                result.total
            ),
        }
    }

    for case in corpus.program_cases {
        let mut calculator = DiceCalculator::new();
        let observed = DiceParser::parse_program(&case.expression)
            .and_then(|program| calculator.evaluate_program(&program));
        let context = format!(
            "case={} classification={} program={:?}",
            case.id, case.classification, case.expression
        );

        match (case.expect, observed) {
            (
                ProgramExpectation::Success {
                    totals,
                    flattened_rolls,
                    comment,
                },
                Ok(result),
            ) => {
                assert_eq!(
                    result
                        .results
                        .iter()
                        .map(|instruction| instruction.total)
                        .collect::<Vec<_>>(),
                    totals,
                    "{context}: instruction totals changed"
                );
                assert_eq!(
                    result
                        .results
                        .iter()
                        .flat_map(|instruction| &instruction.rolls)
                        .map(Vec::len)
                        .sum::<usize>(),
                    flattened_rolls,
                    "{context}: generated roll shape changed"
                );
                assert_eq!(
                    result.comment.unwrap_or_default(),
                    comment,
                    "{context}: comment changed"
                );
            }
            (ProgramExpectation::Error { message_contains }, Err(error)) => assert!(
                error.to_string().contains(&message_contains),
                "{context}: expected error containing {message_contains:?}, got {error}"
            ),
            (ProgramExpectation::Success { .. }, Err(error)) => {
                panic!("{context}: expected success, got {error}")
            }
            (ProgramExpectation::Error { message_contains }, Ok(result)) => panic!(
                "{context}: expected error containing {message_contains:?}, got {} results",
                result.results.len()
            ),
        }
    }
}
