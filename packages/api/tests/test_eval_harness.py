"""Tests for the LLM evaluation harness (schema, checks, judge, runner, golden)."""

from __future__ import annotations

import pytest

from evals import (
    DummyJudge,
    EvalCase,
    LLMJudge,
    golden_cases,
    produce_output,
    run_eval,
)
from evals.checks import run_checks
from evals.schema import CaseResult, CheckResult, EvalReport
from slate.infrastructure.llm.dummy import DummyLLMClient


class _JudgeLLM(DummyLLMClient):
    """A DummyLLMClient whose ``complete`` returns a scripted judge payload."""

    def __init__(self, payload: str) -> None:
        self._payload = payload

    async def complete(self, prompt: str, *, role: str = "fast", json: bool = False) -> str:  # type: ignore[override]
        return self._payload


# =====================================================================
# Golden dataset — well-formed + the pipeline runs (quality is judged
# against a real model, not the dummy, so we don't assert pass-rate here)
# =====================================================================


class TestGoldenDataset:
    def test_dataset_is_well_formed(self) -> None:
        cases = golden_cases()
        assert len(cases) == 12
        assert {c.task for c in cases} == {"recap"}
        assert len({c.id for c in cases}) == 12  # unique ids
        for c in cases:
            assert "context" in c.reference
            assert c.checks == ["non_empty", "grounding", "spoiler_free", "mentions"]

    async def test_pipeline_runs_over_the_dataset(self) -> None:
        report = await run_eval(DummyLLMClient(), golden_cases(), DummyJudge())
        assert len(report.results) == 12
        assert set(report.scores_by_task()) == {"recap"}
        # Every case produced a non-empty recap and a numeric score.
        assert all(r.output for r in report.results)
        assert all(0.0 <= r.score <= 1.0 for r in report.results)


# =====================================================================
# Deterministic checks
# =====================================================================


class TestChecks:
    def test_grounding_flags_ungrounded_output(self) -> None:
        case = EvalCase(
            id="x",
            task="recap",
            inputs={},
            reference={"context": "Hollow Knight Greenpath"},
            checks=["grounding"],
        )
        [result] = run_checks("Completely Different Imaginary Zelda Castle Dragon", case)
        assert result.name == "grounding"
        assert not result.passed

    def test_spoiler_free_catches_forbidden_term(self) -> None:
        case = EvalCase(
            id="x", task="recap", inputs={}, reference={"forbidden": ["final boss"]}, checks=[]
        )
        [result] = run_checks(
            "then you reach the FINAL BOSS",
            EvalCase(**{**case.__dict__, "checks": ["spoiler_free"]}),
        )
        assert not result.passed

    def test_mentions_scores_recall(self) -> None:
        case = EvalCase(
            id="x",
            task="recap",
            inputs={},
            reference={"mentions": ["Watson", "Regina"]},
            checks=["mentions"],
        )
        [hit] = run_checks("you are in Watson doing Regina's gigs", case)
        assert hit.passed and hit.score == pytest.approx(1.0)
        [partial] = run_checks("you are in Watson", case)
        assert not partial.passed and partial.score == pytest.approx(0.5)

    def test_mentions_passes_when_none_required(self) -> None:
        case = EvalCase(id="x", task="recap", inputs={}, reference={}, checks=["mentions"])
        [result] = run_checks("anything", case)
        assert result.passed and result.score == 1.0

    def test_json_valid_rejects_non_json(self) -> None:
        case = EvalCase(id="x", task="capture", inputs={}, checks=["json_valid"])
        [result] = run_checks("not json", case)
        assert not result.passed

    def test_uuid_in_candidates_rejects_unknown(self) -> None:
        case = EvalCase(
            id="x",
            task="pick",
            inputs={},
            reference={"candidate_ids": ["abc"]},
            checks=["uuid_in_candidates"],
        )
        [result] = run_checks('{"library_entry_public_id": "zzz"}', case)
        assert not result.passed

    def test_unknown_check_name_is_skipped(self) -> None:
        case = EvalCase(id="x", task="recap", inputs={}, checks=["does_not_exist"])
        assert run_checks("anything", case) == []

    def test_uuid_in_candidates_rejects_non_object_json(self) -> None:
        case = EvalCase(
            id="x",
            task="pick",
            inputs={},
            reference={"candidate_ids": ["abc"]},
            checks=["uuid_in_candidates"],
        )
        [result] = run_checks('["abc"]', case)  # valid JSON, but a list, not an object
        assert not result.passed


# =====================================================================
# Judge
# =====================================================================


class TestJudge:
    async def test_llm_judge_parses_score(self) -> None:
        judge = LLMJudge(_JudgeLLM('{"score": 0.8, "reason": "good"}'))
        score, reason = await judge.score(golden_cases()[0], "out")
        assert score == pytest.approx(0.8)
        assert reason == "good"

    async def test_llm_judge_clamps_out_of_range(self) -> None:
        judge = LLMJudge(_JudgeLLM('{"score": 5, "reason": "x"}'))
        score, _ = await judge.score(golden_cases()[0], "out")
        assert score == 1.0

    async def test_llm_judge_survives_bad_json(self) -> None:
        judge = LLMJudge(_JudgeLLM("not json at all"))
        score, reason = await judge.score(golden_cases()[0], "out")
        assert score == 0.0
        assert reason.startswith("judge error")

    async def test_dummy_judge_is_fixed(self) -> None:
        score, reason = await DummyJudge(0.7).score(golden_cases()[0], "out")
        assert score == pytest.approx(0.7)
        assert reason == "dummy"

    async def test_llm_judge_clamps_non_numeric_score(self) -> None:
        judge = LLMJudge(_JudgeLLM('{"score": "abc", "reason": "r"}'))
        score, _ = await judge.score(golden_cases()[0], "out")
        assert score == 0.0


# =====================================================================
# Schema aggregation + runner dispatch
# =====================================================================


class TestSchemaAndRunner:
    def test_case_score_without_judge_is_deterministic_mean(self) -> None:
        result = CaseResult(
            case_id="x",
            task="recap",
            output="o",
            checks=[
                CheckResult(name="a", passed=True, score=1.0),
                CheckResult(name="b", passed=True, score=0.5),
            ],
        )
        assert result.deterministic_score == pytest.approx(0.75)
        assert result.score == pytest.approx(0.75)

    def test_case_score_blends_judge(self) -> None:
        result = CaseResult(
            case_id="x",
            task="recap",
            output="o",
            checks=[CheckResult(name="a", passed=True, score=1.0)],
            judge_score=0.0,
        )
        assert result.score == pytest.approx(0.5)

    def test_case_with_no_checks_scores_one(self) -> None:
        result = CaseResult(case_id="x", task="recap", output="o", checks=[])
        assert result.deterministic_score == 1.0
        assert result.passed

    def test_empty_report_defaults(self) -> None:
        report = EvalReport(results=[])
        assert report.overall_score == 1.0
        assert report.pass_rate == 1.0
        assert report.scores_by_task() == {}

    async def test_produce_output_unknown_task_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown eval task"):
            await produce_output(DummyLLMClient(), EvalCase(id="x", task="nope", inputs={}))

    async def test_produce_output_pick_invalid_uuid_fails_check(self) -> None:
        # mood='test_invalid_uuid' makes the dummy return a uuid outside the candidates.
        case = EvalCase(
            id="pick-bad",
            task="pick",
            inputs={
                "candidates": [{"public_id": "abc", "game_title": "Hades"}],
                "mood": "test_invalid_uuid",
                "available_minutes": 30,
                "mental_energy": "low",
            },
            reference={"candidate_ids": ["abc"]},
            checks=["uuid_in_candidates"],
            judge=False,
        )
        report = await run_eval(DummyLLMClient(), [case])
        assert not report.results[0].passed
