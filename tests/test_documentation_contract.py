import copy
import hashlib
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


REPOSITORY_ROOT = Path(__file__).parents[1]
LANGUAGE_GUIDE = REPOSITORY_ROOT / "docs" / "source" / "language.rst"
GRAMMAR = REPOSITORY_ROOT / "src" / "oneroll" / "grammar.pest"
V2_RFC = REPOSITORY_ROOT / "docs" / "rfcs" / "0001-dice-program-language-v2.rst"
V2_TARGET_GRAMMAR = REPOSITORY_ROOT / "docs" / "rfcs" / "0001-v2-target.pest"
RESULT_RFC = REPOSITORY_ROOT / "docs" / "rfcs" / "0003-typed-results-traces-errors.rst"
RESULT_SCHEMA = REPOSITORY_ROOT / "docs" / "rfcs" / "0003-result.schema.json"
RESULT_EXAMPLES = REPOSITORY_ROOT / "docs" / "rfcs" / "0003-examples.json"
SPHINX_SOURCE = REPOSITORY_ROOT / "docs" / "source"
PUBLIC_TEXT_FILES = (
    REPOSITORY_ROOT / "README.md",
    REPOSITORY_ROOT / "Cargo.toml",
    REPOSITORY_ROOT / "pyproject.toml",
    REPOSITORY_ROOT / "docs" / "source" / "conf.py",
    *(REPOSITORY_ROOT / "docs").rglob("*.rst"),
    *(REPOSITORY_ROOT / "docs").rglob("*.md"),
)


class DocumentationContractTests(unittest.TestCase):
    @staticmethod
    def _instruction_results(instructions):
        for instruction in instructions:
            yield instruction
            for execution in instruction["executions"]:
                yield from DocumentationContractTests._instruction_results(
                    execution["instructions"]
                )

    @staticmethod
    def _roll_references(value):
        if value["kind"] == "roll_set":
            yield from (item["node_id"] for item in value["items"])
        elif value["kind"] == "values":
            for item in value["items"]:
                yield from DocumentationContractTests._roll_references(item)

    def _assert_result_graph(self, payload):
        source_length = len(payload["source"].encode("utf-8"))
        instructions = list(self._instruction_results(payload["instructions"]))
        instruction_by_id = {item["id"]: item for item in instructions}
        roll_by_id = {item["id"]: item for item in payload["roll_nodes"]}
        trace_by_id = {item["id"]: item for item in payload["trace_nodes"]}

        self.assertEqual(len(instruction_by_id), len(instructions))
        self.assertEqual(len(roll_by_id), len(payload["roll_nodes"]))
        self.assertEqual(len(trace_by_id), len(payload["trace_nodes"]))
        self.assertEqual(
            [item["id"] for item in instructions],
            [f"i{index}" for index in range(len(instructions))],
        )
        self.assertEqual(
            [item["id"] for item in payload["roll_nodes"]],
            [f"r{index}" for index in range(len(roll_by_id))],
        )
        self.assertEqual(
            [item["id"] for item in payload["trace_nodes"]],
            [f"t{index}" for index in range(len(trace_by_id))],
        )

        def assert_span(span):
            self.assertLessEqual(span["start_byte"], span["end_byte"])
            self.assertLessEqual(span["end_byte"], source_length)

        def assert_frame(frame):
            self.assertEqual([item["index"] for item in frame], list(range(len(frame))))
            for instruction in frame:
                for execution in instruction["executions"]:
                    assert_frame(execution["instructions"])

        assert_frame(payload["instructions"])

        for instruction in instructions:
            assert_span(instruction["span"])
            root = trace_by_id[instruction["trace_root"]]
            self.assertEqual(root["value"], instruction["value"])

            value = instruction["value"]
            if value["kind"] == "scalar":
                expected_scalar = value["value"]
            elif value["kind"] == "values" and all(
                item["kind"] == "scalar" for item in value["items"]
            ):
                expected_scalar = sum(item["value"] for item in value["items"])
            elif value["kind"] == "roll_set" and value["item_kind"] == "scalar":
                expected_scalar = sum(
                    roll_by_id[node_id]["value"]["value"]
                    for node_id in self._roll_references(value)
                )
            else:
                expected_scalar = None
            self.assertEqual(instruction["scalar"], expected_scalar)

        trace_position = {
            item["id"]: index for index, item in enumerate(payload["trace_nodes"])
        }
        reachable_roll_ids = set()
        for trace in payload["trace_nodes"]:
            if trace["span"] is not None:
                assert_span(trace["span"])
            for input_id in trace["inputs"]:
                self.assertLess(trace_position[input_id], trace_position[trace["id"]])

            referenced = set(self._roll_references(trace["value"]))
            referenced.update(trace["related_roll_ids"])
            for field in (
                "selected_roll_ids",
                "discarded_roll_ids",
                "generated_roll_ids",
            ):
                referenced.update(trace["data"].get(field, []))
            referenced.update(
                annotation["node_id"]
                for annotation in trace["data"].get("annotations", [])
            )
            self.assertLessEqual(referenced, roll_by_id.keys())
            reachable_roll_ids.update(referenced)
            self.assertLessEqual(
                set(trace["data"].get("source_instruction_ids", [])),
                instruction_by_id.keys(),
            )

            for value in (trace["value"],):
                if value["kind"] == "roll_set":
                    for reference in value["items"]:
                        self.assertEqual(
                            roll_by_id[reference["node_id"]]["value"]["kind"],
                            value["item_kind"],
                        )

        self.assertEqual(reachable_roll_ids, roll_by_id.keys())
        for index, roll in enumerate(payload["roll_nodes"]):
            assert_span(roll["source"]["span"])
            self.assertIn(roll["source"]["instruction_id"], instruction_by_id)
            self.assertIn(roll["cause_trace_id"], trace_by_id)
            if roll["parent_node_id"] is None:
                self.assertEqual(roll["source"]["generation"], 0)
            else:
                parent_index = int(roll["parent_node_id"][1:])
                self.assertLess(parent_index, index)
                self.assertEqual(
                    roll["source"]["generation"],
                    payload["roll_nodes"][parent_index]["source"]["generation"] + 1,
                )

    def _assert_batch_result(self, payload):
        descriptor = payload["random"]
        self.assertEqual(len(payload["results"]), descriptor["samples"])
        root_seed = bytes.fromhex(descriptor["seed"])

        for index, result in enumerate(payload["results"]):
            self.assertEqual(result["source"], payload["source"])
            self.assertEqual(result["canonical"], payload["canonical"])
            derived_seed = hashlib.sha256(
                b"OneRoll batch seed v1\0"
                + root_seed
                + index.to_bytes(8, byteorder="little")
            ).hexdigest()
            self.assertEqual(result["metadata"]["random"]["seed"], derived_seed)
            self._assert_result_graph(result)

    def test_language_guide_embeds_the_engine_grammar(self):
        guide = LANGUAGE_GUIDE.read_text(encoding="utf-8")
        directive = ".. literalinclude:: ../../src/oneroll/grammar.pest"

        self.assertIn(directive, guide)
        included_path = (
            LANGUAGE_GUIDE.parent / directive.split("::", 1)[1].strip()
        ).resolve()
        self.assertEqual(included_path, GRAMMAR.resolve())
        self.assertTrue(included_path.is_file())
        self.assertIn(":doc:`conformance`", guide)

    def test_v2_rfc_embeds_a_machine_checked_pest_grammar(self):
        rfc = V2_RFC.read_text(encoding="utf-8")
        directive = ".. literalinclude:: ../rfcs/0001-v2-target.pest"

        self.assertIn(directive, rfc)
        included_path = (SPHINX_SOURCE / directive.split("::", 1)[1].strip()).resolve()
        self.assertEqual(included_path, V2_TARGET_GRAMMAR.resolve())
        self.assertTrue(included_path.is_file())

    def test_result_rfc_embeds_a_checked_schema_and_examples(self):
        rfc = RESULT_RFC.read_text(encoding="utf-8")
        schema_directive = ".. literalinclude:: ../rfcs/0003-result.schema.json"
        examples_directive = ".. literalinclude:: ../rfcs/0003-examples.json"

        self.assertIn(schema_directive, rfc)
        self.assertIn(examples_directive, rfc)
        self.assertTrue(RESULT_SCHEMA.is_file())
        self.assertTrue(RESULT_EXAMPLES.is_file())

    def test_result_schema_accepts_normative_examples_and_graphs(self):
        schema = json.loads(RESULT_SCHEMA.read_text(encoding="utf-8"))
        examples = json.loads(RESULT_EXAMPLES.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)

        result_kinds = set()
        for case in examples["result_cases"]:
            with self.subTest(case=case["id"]):
                validator.validate(case["payload"])
                self._assert_result_graph(case["payload"])
                result_kinds.add(case["payload"]["instructions"][0]["value"]["kind"])

        self.assertEqual(
            result_kinds, {"scalar", "text", "values", "roll_set", "boolean"}
        )
        self.assertIn(
            "result.nested_program",
            {case["id"] for case in examples["result_cases"]},
        )
        for case in examples["batch_cases"]:
            with self.subTest(case=case["id"]):
                validator.validate(case["payload"])
                self._assert_batch_result(case["payload"])
        for case in examples["error_cases"]:
            with self.subTest(case=case["id"]):
                validator.validate(case["payload"])

    def test_result_schema_and_graph_checks_reject_contract_drift(self):
        schema = json.loads(RESULT_SCHEMA.read_text(encoding="utf-8"))
        examples = json.loads(RESULT_EXAMPLES.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        scalar = copy.deepcopy(examples["result_cases"][0]["payload"])
        scalar["undocumented"] = True
        with self.assertRaises(ValidationError):
            validator.validate(scalar)

        roll_set = copy.deepcopy(examples["result_cases"][3]["payload"])
        del roll_set["instructions"][0]["value"]["item_kind"]
        with self.assertRaises(ValidationError):
            validator.validate(roll_set)

        budget_error = copy.deepcopy(examples["error_cases"][1]["payload"])
        del budget_error["error"]["requested"]
        with self.assertRaises(ValidationError):
            validator.validate(budget_error)

        dangling = copy.deepcopy(examples["result_cases"][3]["payload"])
        dangling["instructions"][0]["value"]["items"][0]["node_id"] = "r99"
        validator.validate(dangling)
        with self.assertRaises(AssertionError):
            self._assert_result_graph(dangling)

        batch = copy.deepcopy(examples["batch_cases"][0]["payload"])
        batch["random"]["samples"] = 3
        validator.validate(batch)
        with self.assertRaises(AssertionError):
            self._assert_batch_result(batch)

        batch = copy.deepcopy(examples["batch_cases"][0]["payload"])
        batch["results"][1]["metadata"]["random"]["seed"] = "f" * 64
        validator.validate(batch)
        with self.assertRaises(AssertionError):
            self._assert_batch_result(batch)

    def test_public_project_references_do_not_use_legacy_names(self):
        forbidden = (
            "hydro_roll",
            "hydro-roll",
            "HydroRoll-Team/HydroRoll",
            "Pyo3 Project Template For HydroRoll",
            "https://github.com/HydroRoll-Team/oneroll",
            '"hydroroll",',
        )

        for path in PUBLIC_TEXT_FILES:
            content = path.read_text(encoding="utf-8")
            for legacy_reference in forbidden:
                with self.subTest(path=path, reference=legacy_reference):
                    self.assertNotIn(legacy_reference, content)

        for manifest in ("Cargo.toml", "pyproject.toml"):
            content = (REPOSITORY_ROOT / manifest).read_text(encoding="utf-8")
            self.assertIn(
                'repository = "https://github.com/HydroRoll-Team/OneRoll"',
                content,
            )


if __name__ == "__main__":
    unittest.main()
