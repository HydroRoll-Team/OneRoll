#![no_main]

use libfuzzer_sys::fuzz_target;
use oneroll_core::{DiceParser, ResourcePolicy};

const SETTINGS_BYTES: usize = 4;
const MAX_INPUT_BYTES: usize = 4_100;

fuzz_target!(|data: &[u8]| {
    if data.len() > MAX_INPUT_BYTES {
        return;
    }

    let split = data.len().min(SETTINGS_BYTES);
    let (settings, source) = data.split_at(split);
    let Ok(source) = std::str::from_utf8(source) else {
        return;
    };

    let setting = |index: usize| usize::from(settings.get(index).copied().unwrap_or(0));
    let policy = ResourcePolicy::default()
        .with_limit("source_bytes", setting(0) * 16)
        .expect("fuzz source limit stays below the hard maximum")
        .with_limit("parse_depth", setting(1).min(64))
        .expect("fuzz depth limit stays below the hard maximum")
        .with_limit("ast_nodes", setting(2) * 16)
        .expect("fuzz AST limit stays below the hard maximum")
        .with_limit("parsed_instructions", setting(3) * 4)
        .expect("fuzz instruction limit stays below the hard maximum");

    let _ = DiceParser::parse_program_with_policy(source, &policy);
});
