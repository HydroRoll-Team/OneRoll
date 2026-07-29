use serde::Deserialize;

use crate::{DiceCalculator, DiceError, DiceParser};

#[derive(pest_derive::Parser)]
#[grammar = "docs/rfcs/0001-v2-target.pest"]
struct V2TargetParser;

#[test]
fn v2_target_grammar_parses_normative_syntax_shapes() {
    use pest::Parser;

    let valid_sources = [
        "1d6; 2d6 # encounter",
        r#""say \"yes\"\nnow""#,
        "true",
        "${bonus} + 2",
        "[-1..1]",
        "[]",
        "2du[1..6]",
        r#"1L["common"[80%], "rare"[20%]]"#,
        "4d6e[=max]k3",
        "(1 + 2)i:[>2]{10}",
        "4d6d1f[>=2]sl",
        "4d6c[%2=0]",
        "4d6r[=1]R[<=2]a[=1]e[=max]",
        "[1,2]m([3,4])",
        "1d6; 1d8b",
        "10d10o",
        "10d10o(2,7)",
        "10d10o(2,[<6])",
        "[1,1,2]u",
        "4d6p[red:2,#00ff00:1]",
        "4d6i[<3]{${0}+1}",
        r#"4d6i.[=max]{"critical"}{"ordinary"}"#,
        "4d6yg2",
        r#"repeat(3; 1d6; 1L["yes", "no"])"#,
    ];
    let invalid_sources = [
        "",
        "1d6;",
        "1d6;;2d6",
        r#""unfinished"#,
        "1L[]",
        "4d6c[]",
        "1d6m",
        "@",
        "help",
    ];

    for source in valid_sources {
        assert!(
            V2TargetParser::parse(Rule::program, source).is_ok(),
            "RFC-0001 target grammar rejected normative source {source:?}"
        );
    }
    for source in invalid_sources {
        assert!(
            V2TargetParser::parse(Rule::program, source).is_err(),
            "RFC-0001 target grammar accepted invalid source {source:?}"
        );
    }
}

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
        total: i64,
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
        totals: Vec<i64>,
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

#[test]
fn checked_i64_arithmetic_contract() {
    fn evaluate(source: &str) -> Result<i64, DiceError> {
        let expression = DiceParser::parse_expression(source)?;
        DiceCalculator::new()
            .evaluate_expression(&expression)
            .map(|result| result.total)
    }

    for (source, expected) in [
        ("9223372036854775807", i64::MAX),
        ("-9223372036854775808", i64::MIN),
        ("5 / 2", 2),
        ("-5 / 2", -2),
        ("5 / -2", -2),
        ("-5 / -2", 2),
        ("0 ^ 0", 1),
    ] {
        assert_eq!(evaluate(source).unwrap(), expected, "source={source:?}");
    }

    for source in [
        "9223372036854775807 + 1",
        "-9223372036854775808 - 1",
        "3037000500 * 3037000500",
        "-9223372036854775808 / -1",
        "2 ^ 63",
    ] {
        assert!(
            matches!(evaluate(source), Err(DiceError::ArithmeticOverflow { .. })),
            "source={source:?}"
        );
    }

    assert!(matches!(
        evaluate("1 / 0"),
        Err(DiceError::ArithmeticDivideByZero)
    ));
    for source in ["2 ^ -1", "2 ^ 4294967296"] {
        assert!(
            matches!(
                evaluate(source),
                Err(DiceError::ArithmeticInvalidExponent { .. })
            ),
            "source={source:?}"
        );
    }
}

#[test]
fn checked_i64_binary_operations_match_i128_boundary_properties() {
    fn evaluate(source: &str) -> Result<i64, DiceError> {
        let expression = DiceParser::parse_expression(source)?;
        DiceCalculator::new()
            .evaluate_expression(&expression)
            .map(|result| result.total)
    }

    let values = [
        i64::MIN,
        i64::MIN + 1,
        -3_037_000_500,
        -2,
        -1,
        0,
        1,
        2,
        3_037_000_499,
        i64::MAX - 1,
        i64::MAX,
    ];

    for left in values {
        for right in values {
            for (operator, expected) in [
                ("+", i128::from(left) + i128::from(right)),
                ("-", i128::from(left) - i128::from(right)),
                ("*", i128::from(left) * i128::from(right)),
            ] {
                let source = format!("{left} {operator} {right}");
                match i64::try_from(expected) {
                    Ok(expected) => assert_eq!(evaluate(&source).unwrap(), expected),
                    Err(_) => assert!(matches!(
                        evaluate(&source),
                        Err(DiceError::ArithmeticOverflow { .. })
                    )),
                }
            }

            let source = format!("{left} / {right}");
            if right == 0 {
                assert!(matches!(
                    evaluate(&source),
                    Err(DiceError::ArithmeticDivideByZero)
                ));
            } else if left == i64::MIN && right == -1 {
                assert!(matches!(
                    evaluate(&source),
                    Err(DiceError::ArithmeticOverflow { .. })
                ));
            } else {
                assert_eq!(evaluate(&source).unwrap(), left / right);
            }
        }
    }
}
