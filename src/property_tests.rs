use proptest::prelude::*;

use crate::{DiceCalculator, DiceModifier, DiceParser, DiceRoll, RandomSeed, ResourcePolicy};

proptest! {
    #![proptest_config(ProptestConfig::with_cases(256))]

    #[test]
    fn property_numeric_dice_stay_in_range_and_total_their_faces(
        count in 1i32..64,
        sides in 1i32..10_000,
        seed in any::<[u8; 32]>(),
    ) {
        let dice = DiceRoll {
            count,
            sides,
            modifiers: vec![],
        };
        let mut calculator = DiceCalculator::with_policy_and_seed(
            ResourcePolicy::default(),
            RandomSeed::from_bytes(seed),
        );

        let rolls = calculator.roll_dice(&dice).unwrap();
        let faces = rolls.iter().flatten().copied().collect::<Vec<_>>();

        prop_assert_eq!(faces.len(), count as usize);
        prop_assert!(faces.iter().all(|face| (1..=i64::from(sides)).contains(face)));
        prop_assert_eq!(
            faces.iter().sum::<i64>(),
            rolls.iter().flatten().copied().sum::<i64>()
        );
    }


    #[test]
    fn property_equal_seeded_requests_replay_exactly(
        count in 1i32..64,
        sides in 1i32..10_000,
        seed in any::<[u8; 32]>(),
    ) {
        let dice = DiceRoll {
            count,
            sides,
            modifiers: vec![],
        };
        let policy = ResourcePolicy::default();
        let seed = RandomSeed::from_bytes(seed);
        let mut first = DiceCalculator::with_policy_and_seed(policy.clone(), seed);
        let mut second = DiceCalculator::with_policy_and_seed(policy, seed);

        let first_rolls = first.roll_dice(&dice).unwrap();
        let second_rolls = second.roll_dice(&dice).unwrap();

        prop_assert_eq!(first_rolls, second_rolls);
        prop_assert_eq!(first.random_descriptor(), second.random_descriptor());
    }

    #[test]
    fn property_relaxing_generated_value_budget_cannot_break_a_success(
        count in 1i32..256,
        sides in 1i32..1_000,
        low_limit in 0usize..256,
        extra_capacity in 0usize..256,
        seed in any::<[u8; 32]>(),
    ) {
        let high_limit = low_limit + extra_capacity;
        let low_policy = ResourcePolicy::default()
            .with_limit("generated_values", low_limit)
            .unwrap();
        let high_policy = ResourcePolicy::default()
            .with_limit("generated_values", high_limit)
            .unwrap();
        let dice = DiceRoll {
            count,
            sides,
            modifiers: vec![],
        };
        let seed = RandomSeed::from_bytes(seed);
        let mut low = DiceCalculator::with_policy_and_seed(low_policy, seed);
        let mut high = DiceCalculator::with_policy_and_seed(high_policy, seed);

        let low_result = low.roll_dice(&dice);
        let high_result = high.roll_dice(&dice);

        match (&low_result, &high_result) {
            (Ok(low_rolls), Ok(high_rolls)) => prop_assert_eq!(low_rolls, high_rolls),
            (Ok(_), Err(error)) => {
                prop_assert!(false, "relaxed budget rejected a prior success: {error}")
            }
            _ => {}
        }
        if high_result.is_err() {
            prop_assert!(low_result.is_err());
        }
    }

    #[test]
    fn property_bounded_utf8_programs_never_panic_the_parser(
        characters in proptest::collection::vec(any::<char>(), 0..512),
    ) {
        let source = characters.into_iter().collect::<String>();
        let policy = ResourcePolicy::default()
            .with_limit("source_bytes", 2_048)
            .unwrap();

        let _ = DiceParser::parse_program_with_policy(&source, &policy);
    }

    #[test]
    fn property_modifier_combinations_terminate_under_shared_limits(
        count in 1i32..8,
        sides in 1i32..20,
        modifier_codes in proptest::collection::vec(0u8..12, 0..8),
        seed in any::<[u8; 32]>(),
    ) {
        let modifiers = modifier_codes
            .into_iter()
            .map(|code| match code {
                0 => DiceModifier::Explode,
                1 => DiceModifier::ExplodeAlias,
                2 => DiceModifier::KeepHigh(1),
                3 => DiceModifier::KeepLow(1),
                4 => DiceModifier::DropHigh(1),
                5 => DiceModifier::DropLow(1),
                6 => DiceModifier::Reroll(sides),
                7 => DiceModifier::RerollOnce(sides),
                8 => DiceModifier::RerollUntil(sides),
                9 => DiceModifier::RerollAndAdd(sides),
                10 => DiceModifier::Count(1),
                _ => DiceModifier::Unique,
            })
            .collect();
        let dice = DiceRoll {
            count,
            sides,
            modifiers,
        };
        let policy = ResourcePolicy::default()
            .with_limit("generated_values", 128)
            .unwrap()
            .with_limit("rng_words", 256)
            .unwrap()
            .with_limit("work_units", 4_096)
            .unwrap();
        let mut calculator =
            DiceCalculator::with_policy_and_seed(policy, RandomSeed::from_bytes(seed));

        let _ = calculator.roll_dice(&dice);
    }
}
