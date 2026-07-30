use crate::errors::DiceError;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ResourceLimitDefinition {
    pub name: &'static str,
    pub default: usize,
    pub hard_max: usize,
}

pub const RESOURCE_LIMITS: [ResourceLimitDefinition; 17] = [
    ResourceLimitDefinition {
        name: "source_bytes",
        default: 65_536,
        hard_max: 1_048_576,
    },
    ResourceLimitDefinition {
        name: "environment_items",
        default: 1_024,
        hard_max: 16_384,
    },
    ResourceLimitDefinition {
        name: "environment_bytes",
        default: 1_048_576,
        hard_max: 16_777_216,
    },
    ResourceLimitDefinition {
        name: "parse_depth",
        default: 64,
        hard_max: 256,
    },
    ResourceLimitDefinition {
        name: "ast_nodes",
        default: 4_096,
        hard_max: 65_536,
    },
    ResourceLimitDefinition {
        name: "parsed_instructions",
        default: 1_000,
        hard_max: 10_000,
    },
    ResourceLimitDefinition {
        name: "executed_instructions",
        default: 10_000,
        hard_max: 1_000_000,
    },
    ResourceLimitDefinition {
        name: "nesting_depth",
        default: 32,
        hard_max: 128,
    },
    ResourceLimitDefinition {
        name: "source_items",
        default: 10_000,
        hard_max: 100_000,
    },
    ResourceLimitDefinition {
        name: "generated_values",
        default: 10_000,
        hard_max: 1_000_000,
    },
    ResourceLimitDefinition {
        name: "rng_words",
        default: 20_000,
        hard_max: 2_000_000,
    },
    ResourceLimitDefinition {
        name: "collection_items",
        default: 10_000,
        hard_max: 100_000,
    },
    ResourceLimitDefinition {
        name: "trace_nodes",
        default: 20_000,
        hard_max: 200_000,
    },
    ResourceLimitDefinition {
        name: "output_items",
        default: 10_000,
        hard_max: 100_000,
    },
    ResourceLimitDefinition {
        name: "output_bytes",
        default: 8_388_608,
        hard_max: 67_108_864,
    },
    ResourceLimitDefinition {
        name: "work_units",
        default: 1_000_000,
        hard_max: 50_000_000,
    },
    ResourceLimitDefinition {
        name: "batch_samples",
        default: 10_000,
        hard_max: 1_000_000,
    },
];

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ResourcePolicy {
    values: [usize; RESOURCE_LIMITS.len()],
}

impl Default for ResourcePolicy {
    fn default() -> Self {
        Self {
            values: RESOURCE_LIMITS.map(|definition| definition.default),
        }
    }
}

impl ResourcePolicy {
    pub fn limit(&self, name: &str) -> Option<usize> {
        RESOURCE_LIMITS
            .iter()
            .position(|definition| definition.name == name)
            .map(|index| self.values[index])
    }

    pub fn hard_limit(name: &str) -> Option<usize> {
        RESOURCE_LIMITS
            .iter()
            .find(|definition| definition.name == name)
            .map(|definition| definition.hard_max)
    }

    pub fn with_limit(&self, name: &str, limit: usize) -> Result<Self, DiceError> {
        let index = RESOURCE_LIMITS
            .iter()
            .position(|definition| definition.name == name)
            .ok_or_else(|| DiceError::UnknownResourceLimit(name.to_string()))?;
        let hard_max = RESOURCE_LIMITS[index].hard_max;
        if limit > hard_max {
            return Err(DiceError::PolicyLimitExceedsHardMaximum {
                resource: RESOURCE_LIMITS[index].name,
                requested: limit,
                hard_max,
            });
        }

        let mut policy = self.clone();
        policy.values[index] = limit;
        Ok(policy)
    }

    pub(crate) fn require(&self, name: &'static str) -> usize {
        self.limit(name)
            .expect("internal resource names must be registered")
    }
}

#[derive(Clone, Debug)]
pub struct ExecutionBudget {
    policy: ResourcePolicy,
    used: [usize; RESOURCE_LIMITS.len()],
    nesting_depth: usize,
}

impl ExecutionBudget {
    pub fn new(policy: ResourcePolicy) -> Self {
        Self {
            policy,
            used: [0; RESOURCE_LIMITS.len()],
            nesting_depth: 0,
        }
    }

    pub fn charge(&mut self, resource: &'static str, requested: usize) -> Result<(), DiceError> {
        let index = Self::index(resource);
        let used = self.used[index];
        let limit = self.policy.values[index];
        let next = used
            .checked_add(requested)
            .ok_or_else(|| Self::limit_error(resource, used, requested, limit))?;
        if next > limit {
            return Err(Self::limit_error(resource, used, requested, limit));
        }
        self.used[index] = next;
        Ok(())
    }

    pub fn ensure(&self, resource: &'static str, requested: usize) -> Result<(), DiceError> {
        let limit = self.policy.require(resource);
        if requested > limit {
            return Err(DiceError::ResourceLimitExceeded {
                resource,
                used: 0,
                requested,
                limit,
            });
        }
        Ok(())
    }

    pub fn enter_nesting(&mut self) -> Result<(), DiceError> {
        let limit = self.policy.require("nesting_depth");
        let next = self
            .nesting_depth
            .checked_add(1)
            .ok_or(DiceError::ResourceLimitExceeded {
                resource: "nesting_depth",
                used: self.nesting_depth,
                requested: 1,
                limit,
            })?;
        if next > limit {
            return Err(DiceError::ResourceLimitExceeded {
                resource: "nesting_depth",
                used: self.nesting_depth,
                requested: 1,
                limit,
            });
        }
        self.nesting_depth = next;
        Ok(())
    }

    pub fn leave_nesting(&mut self) {
        self.nesting_depth = self.nesting_depth.saturating_sub(1);
    }

    fn index(resource: &'static str) -> usize {
        RESOURCE_LIMITS
            .iter()
            .position(|definition| definition.name == resource)
            .expect("internal resource names must be registered")
    }

    fn limit_error(
        resource: &'static str,
        used: usize,
        requested: usize,
        limit: usize,
    ) -> DiceError {
        if resource == "generated_values" {
            DiceError::GeneratedValueLimitExceeded {
                used,
                requested,
                limit,
            }
        } else {
            DiceError::ResourceLimitExceeded {
                resource,
                used,
                requested,
                limit,
            }
        }
    }
}
