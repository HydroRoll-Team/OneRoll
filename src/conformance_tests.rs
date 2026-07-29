use serde::Deserialize;

use crate::resource::ExecutionBudget;
use crate::{DiceCalculator, DiceError, DiceParser, RandomSeed, ResourcePolicy};

#[derive(pest_derive::Parser)]
#[grammar = "docs/rfcs/0001-v2-target.pest"]
struct V2TargetParser;

#[test]
fn rfc_0002_chacha12_all_zero_seed_matches_raw_words() {
    let mut budget = ExecutionBudget::new(ResourcePolicy::default());
    let mut random = crate::random::RequestRandom::from_seed(RandomSeed::from_bytes([0; 32]));

    let observed = (0..4)
        .map(|_| random.next_u64(&mut budget).unwrap())
        .collect::<Vec<_>>();

    assert_eq!(
        observed,
        [
            0x53f9_5507_6a9a_f49b,
            0xd583_265f_12ce_1f81,
            0x1474_e049_bbc3_2904,
            0x5f15_ae2e_a589_007e,
        ]
    );
}

#[test]
fn rfc_0002_chacha12_bounded_sampling_matches_vectors() {
    use std::num::NonZeroU64;

    fn sample(bound: u64) -> Vec<u64> {
        let mut budget = ExecutionBudget::new(ResourcePolicy::default());
        let mut random = crate::random::RequestRandom::from_seed(RandomSeed::from_bytes([0; 32]));
        let bound = NonZeroU64::new(bound).unwrap();
        (0..4)
            .map(|_| random.uniform_below(bound, &mut budget).unwrap() + 1)
            .collect()
    }

    assert_eq!(sample(6), [4, 4, 3, 3]);
    assert_eq!(sample(20), [4, 2, 1, 15]);

    let mut budget = ExecutionBudget::new(ResourcePolicy::default());
    let mut weighted = crate::random::RequestRandom::from_seed(RandomSeed::from_bytes([0; 32]));
    let weighted_index = weighted
        .uniform_below(NonZeroU64::new(100).unwrap(), &mut budget)
        .unwrap();
    assert!(
        weighted_index < 80,
        "all-zero weighted vector must select common"
    );
}

#[test]
fn rfc_0002_seed_forms_normalize_to_canonical_bytes_and_hex() {
    let integer = RandomSeed::from_u64(0x0807_0605_0403_0201);
    assert_eq!(
        integer.to_hex(),
        "0102030405060708000000000000000000000000000000000000000000000000"
    );

    let uppercase =
        RandomSeed::from_hex("0x000102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F")
            .unwrap();
    assert_eq!(
        uppercase.to_hex(),
        "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"
    );

    for invalid in [
        "",
        "0x",
        "00",
        "g000000000000000000000000000000000000000000000000000000000000000",
        "00000000000000000000000000000000000000000000000000000000000000000",
    ] {
        assert!(matches!(
            RandomSeed::from_hex(invalid),
            Err(DiceError::RandomInvalidSeed)
        ));
    }
}

#[test]
fn rfc_0002_seeded_calculator_uses_one_metered_request_stream() {
    let expression = DiceParser::parse_expression("4d6").unwrap();
    let seed = RandomSeed::from_bytes([0; 32]);

    let mut first = DiceCalculator::with_seed(seed);
    let first_result = first.evaluate_expression(&expression).unwrap();
    let first_random = first.random_descriptor().unwrap();

    let mut second = DiceCalculator::with_seed(seed);
    let second_result = second.evaluate_expression(&expression).unwrap();
    let second_random = second.random_descriptor().unwrap();

    assert_eq!(first_result.rolls, vec![vec![4], vec![4], vec![3], vec![3]]);
    assert_eq!(second_result.rolls, first_result.rolls);
    assert_eq!(first_random, second_random);
    assert_eq!(first_random.algorithm, "oneroll-chacha12-v1");
    assert_eq!(first_random.seed, "0".repeat(64));
    assert_eq!(first_random.rng_words, 4);

    let replayed = first.evaluate_expression(&expression).unwrap();
    assert_eq!(replayed.rolls, first_result.rolls);
    assert_eq!(first.random_descriptor().unwrap().rng_words, 4);
}

#[test]
fn rfc_0002_rejected_words_are_charged_before_retrying() {
    use std::num::NonZeroU64;

    let policy = ResourcePolicy::default()
        .with_limit("rng_words", 2)
        .unwrap();
    let mut budget = ExecutionBudget::new(policy);
    let mut random = crate::random::RequestRandom::from_seed(RandomSeed::from_bytes([0; 32]));
    let bound = NonZeroU64::new((1u64 << 63) + 1).unwrap();

    assert!(random.uniform_below(bound, &mut budget).is_ok());
    assert!(matches!(
        random.uniform_below(bound, &mut budget),
        Err(DiceError::ResourceLimitExceeded {
            resource: "rng_words",
            used: 2,
            requested: 1,
            limit: 2,
        })
    ));
    assert_eq!(random.descriptor().rng_words, 2);
}

#[test]
fn rfc_0002_random_descriptor_appears_only_after_initialization() {
    let seed = RandomSeed::from_bytes([0; 32]);

    let mut static_failure = DiceCalculator::with_seed(seed);
    let expression = DiceParser::parse_expression("1 / 0").unwrap();
    assert!(matches!(
        static_failure.evaluate_expression(&expression),
        Err(DiceError::ArithmeticDivideByZero)
    ));
    assert_eq!(static_failure.random_descriptor(), None);

    let scalar = DiceParser::parse_expression("42").unwrap();
    assert_eq!(
        static_failure.evaluate_expression(&scalar).unwrap().total,
        42
    );
    assert_eq!(static_failure.random_descriptor().unwrap().rng_words, 0);

    let mut failure_after_draw = DiceCalculator::with_seed(seed);
    let expression = DiceParser::parse_expression("1d6 / 0").unwrap();
    assert!(matches!(
        failure_after_draw.evaluate_expression(&expression),
        Err(DiceError::ArithmeticDivideByZero)
    ));
    assert_eq!(failure_after_draw.random_descriptor().unwrap().rng_words, 1);
}

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
