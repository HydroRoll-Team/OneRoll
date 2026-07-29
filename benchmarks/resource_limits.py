"""Small, dependency-free benchmark for OneRoll's default safety policy."""

import json
from time import perf_counter

import oneroll


def measure(name, operation):
    started = perf_counter()
    outcome = "ok"
    try:
        operation()
    except ValueError as error:
        outcome = str(error).split("]", 1)[0] + "]"
    return {
        "case": name,
        "elapsed_ms": round((perf_counter() - started) * 1_000, 3),
        "outcome": outcome,
    }


def main():
    roller = oneroll.OneRoll()
    cases = [
        (
            "parsed_instructions_at_default",
            lambda: roller.run(";".join(["1"] * 1_000)),
        ),
        (
            "generated_values_at_default",
            lambda: roller.roll_simple(10_000, 1),
        ),
        ("bounded_infinite_explosion", lambda: roller.roll("1d1!")),
        ("shared_batch_1000", lambda: roller.roll_multiple("1d1", 1_000)),
    ]
    report = {
        "limits": oneroll.ResourcePolicy().limits(),
        "measurements": [measure(name, operation) for name, operation in cases],
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
