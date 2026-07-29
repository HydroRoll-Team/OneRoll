#![no_main]

use libfuzzer_sys::fuzz_target;
use oneroll_core::{DiceCalculator, DiceParser, RandomSeed, ResourcePolicy};

const SEED_BYTES: usize = 8;
const SETTINGS_BYTES: usize = 5;
const HEADER_BYTES: usize = SEED_BYTES + SETTINGS_BYTES;
const MAX_INPUT_BYTES: usize = HEADER_BYTES + 4_096;

fuzz_target!(|data: &[u8]| {
    if data.len() < HEADER_BYTES || data.len() > MAX_INPUT_BYTES {
        return;
    }

    let mut seed = [0; 32];
    seed[..SEED_BYTES].copy_from_slice(&data[..SEED_BYTES]);
    let settings = &data[SEED_BYTES..HEADER_BYTES];
    let Ok(source) = std::str::from_utf8(&data[HEADER_BYTES..]) else {
        return;
    };

    let policy = ResourcePolicy::default()
        .with_limit("source_bytes", 4_096)
        .expect("fixed fuzz source limit is valid")
        .with_limit("generated_values", usize::from(settings[0]))
        .expect("byte-sized generation limit is valid")
        .with_limit("rng_words", usize::from(settings[1]) * 2)
        .expect("fuzz RNG limit is valid")
        .with_limit("collection_items", usize::from(settings[2]) * 2)
        .expect("fuzz collection limit is valid")
        .with_limit("work_units", usize::from(settings[3]) * 256)
        .expect("fuzz work limit is valid")
        .with_limit("output_bytes", usize::from(settings[4]) * 1_024)
        .expect("fuzz output limit is valid");

    if let Ok(program) = DiceParser::parse_program_with_policy(source, &policy) {
        let mut calculator =
            DiceCalculator::with_policy_and_seed(policy, RandomSeed::from_bytes(seed));
        let _ = calculator.evaluate_program(&program);
    }
});
