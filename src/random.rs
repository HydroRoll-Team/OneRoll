use rand_chacha::ChaCha12Rng;
use rand_core::{RngCore, SeedableRng};
use std::num::NonZeroU64;

use crate::errors::DiceError;
use crate::resource::ExecutionBudget;
use serde::{Deserialize, Serialize};

pub const RANDOM_PROTOCOL_ID: &str = "oneroll-chacha12-v1";

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct RandomDescriptor {
    pub algorithm: String,
    pub seed: String,
    pub rng_words: usize,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct RandomSeed([u8; 32]);

impl RandomSeed {
    pub const fn from_bytes(bytes: [u8; 32]) -> Self {
        Self(bytes)
    }

    pub const fn as_bytes(&self) -> &[u8; 32] {
        &self.0
    }

    pub fn from_u64(value: u64) -> Self {
        let mut bytes = [0; 32];
        bytes[..8].copy_from_slice(&value.to_le_bytes());
        Self(bytes)
    }

    pub fn from_hex(value: &str) -> Result<Self, DiceError> {
        let digits = value.strip_prefix("0x").unwrap_or(value);
        if digits.len() != 64 || !digits.bytes().all(|byte| byte.is_ascii_hexdigit()) {
            return Err(DiceError::RandomInvalidSeed);
        }

        let mut bytes = [0; 32];
        for (index, pair) in digits.as_bytes().chunks_exact(2).enumerate() {
            let high = Self::hex_value(pair[0]);
            let low = Self::hex_value(pair[1]);
            bytes[index] = (high << 4) | low;
        }
        Ok(Self(bytes))
    }

    pub fn to_hex(self) -> String {
        const HEX: &[u8; 16] = b"0123456789abcdef";
        let mut output = String::with_capacity(64);
        for byte in self.0 {
            output.push(HEX[usize::from(byte >> 4)] as char);
            output.push(HEX[usize::from(byte & 0x0f)] as char);
        }
        output
    }

    fn hex_value(byte: u8) -> u8 {
        match byte {
            b'0'..=b'9' => byte - b'0',
            b'a'..=b'f' => byte - b'a' + 10,
            b'A'..=b'F' => byte - b'A' + 10,
            _ => unreachable!("seed characters are validated before decoding"),
        }
    }
}

pub(crate) struct RequestRandom {
    rng: ChaCha12Rng,
    seed: RandomSeed,
    rng_words: usize,
}

impl RequestRandom {
    pub(crate) fn from_seed(seed: RandomSeed) -> Self {
        Self {
            rng: ChaCha12Rng::from_seed(*seed.as_bytes()),
            seed,
            rng_words: 0,
        }
    }

    pub(crate) fn from_os_entropy() -> Result<Self, DiceError> {
        Self::from_entropy_with(|bytes| getrandom::fill(bytes))
    }

    fn from_entropy_with<E, F>(fill: F) -> Result<Self, DiceError>
    where
        E: std::fmt::Display,
        F: FnOnce(&mut [u8; 32]) -> Result<(), E>,
    {
        let mut bytes = [0; 32];
        fill(&mut bytes).map_err(|error| DiceError::RandomEntropyUnavailable {
            reason: error.to_string(),
        })?;
        Ok(Self::from_seed(RandomSeed::from_bytes(bytes)))
    }

    pub(crate) fn descriptor(&self) -> RandomDescriptor {
        RandomDescriptor {
            algorithm: RANDOM_PROTOCOL_ID.to_string(),
            seed: self.seed.to_hex(),
            rng_words: self.rng_words,
        }
    }

    pub(crate) fn next_u64(&mut self, budget: &mut ExecutionBudget) -> Result<u64, DiceError> {
        budget.charge("rng_words", 1)?;
        self.rng_words += 1;
        Ok(self.rng.next_u64())
    }

    pub(crate) fn uniform_below(
        &mut self,
        bound: NonZeroU64,
        budget: &mut ExecutionBudget,
    ) -> Result<u64, DiceError> {
        let two_to_64 = u128::from(u64::MAX) + 1;

        loop {
            let word = self.next_u64(budget)?;
            if let Some(value) = accepted_uniform_value(word, two_to_64, bound) {
                return Ok(value);
            }
        }
    }
}

fn accepted_uniform_value(word: u64, word_space: u128, bound: NonZeroU64) -> Option<u64> {
    let bound = u128::from(bound.get());
    let zone = (word_space / bound) * bound;
    (u128::from(word) < zone).then(|| (u128::from(word) % bound) as u64)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rfc_0002_reduced_width_sampler_has_equal_preimages_for_every_bound() {
        let word_space = 16u128;

        for bound in 1..=16 {
            let bound = NonZeroU64::new(bound).unwrap();
            let mut counts = vec![0usize; bound.get() as usize];
            let mut rejected = 0usize;

            for word in 0..16 {
                match accepted_uniform_value(word, word_space, bound) {
                    Some(value) => counts[value as usize] += 1,
                    None => rejected += 1,
                }
            }

            assert!(counts.windows(2).all(|pair| pair[0] == pair[1]));
            assert_eq!(rejected as u64, 16 % bound.get());
        }
    }

    #[test]
    fn rfc_0002_entropy_failure_never_creates_a_fallback_seed() {
        let result = RequestRandom::from_entropy_with(|_| Err::<(), _>("entropy offline"));

        assert!(matches!(
            result,
            Err(DiceError::RandomEntropyUnavailable { reason })
                if reason == "entropy offline"
        ));
    }
}
