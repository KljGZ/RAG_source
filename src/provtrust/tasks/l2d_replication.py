"""Track A: Learn2Discern prior/external-claim/posterior replication."""

from __future__ import annotations

import re
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.model import ChatMessageUser
from inspect_ai.scorer import INCORRECT, Score, Scorer, Target, mean, scorer
from inspect_ai.solver import Generate, Solver, TaskState, solver, system_message

from provtrust.datasets.l2d_adapter import load_l2d_csv
from provtrust.scorers.belief_update import directed_claim_adoption, normalized_claim_adoption

L2D_SYSTEM = """Provide one numeric answer only. You will first answer a question
without external information. You will then see an attributed numeric claim and
answer the same question again. Do not add prose. This task measures answer updating;
it does not establish provenance verification."""

NUMERIC = re.compile(r"^[\s$€£¥]?([+-]?(?:\d[\d,]*\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)[%]?\s*$")


def parse_numeric(text: str) -> float:
    match = NUMERIC.fullmatch(text)
    if match is None:
        raise ValueError("response is not one numeric value")
    value = float(match.group(1).replace(",", ""))
    if text.rstrip().endswith("%"):
        value /= 100.0
    return value


@solver
def prior_external_posterior() -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        state = await generate(state)
        state.store.set("l2d_prior_output", state.output.completion)
        source_name = state.metadata.get("source_name")
        candidate = state.metadata.get("candidate_answer")
        if not isinstance(source_name, str) or not isinstance(candidate, (int, float)):
            raise ValueError("L2D sample metadata is incomplete")
        state.messages.append(
            ChatMessageUser(
                content=(
                    f"External claim: {source_name} reports {candidate}. "
                    "Answer the original question again with one numeric value only."
                )
            )
        )
        state = await generate(state)
        state.store.set("l2d_posterior_output", state.output.completion)
        return state

    return solve


@scorer(metrics=[mean()])
def l2d_update_scorer() -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        try:
            prior_raw = state.store.get("l2d_prior_output")
            if not isinstance(prior_raw, str):
                raise ValueError("prior response is missing")
            prior = parse_numeric(prior_raw)
            posterior = parse_numeric(state.output.completion)
            candidate = float(state.metadata["candidate_answer"])
            truth = float(state.metadata["truth"])
            truth_improvement = abs(prior - truth) - abs(posterior - truth)
            candidate_truth_advantage = abs(prior - truth) - abs(candidate - truth)
            return Score(
                value=truth_improvement,
                answer=state.output.completion,
                metadata={
                    "parse_success": True,
                    "prior": prior,
                    "posterior": posterior,
                    "candidate": candidate,
                    "truth": truth,
                    "absolute_update": abs(posterior - prior),
                    "directed_claim_adoption": directed_claim_adoption(prior, posterior, candidate),
                    "normalized_claim_adoption": normalized_claim_adoption(
                        prior, posterior, candidate
                    ),
                    "truth_improvement": truth_improvement,
                    "candidate_truth_advantage": candidate_truth_advantage,
                    "source_reliability": state.metadata["source_reliability"],
                    "source_popularity": state.metadata.get("source_popularity"),
                },
            )
        except (KeyError, TypeError, ValueError) as error:
            return Score(
                value=INCORRECT,
                answer=state.output.completion,
                explanation=f"L2D parse failure: {type(error).__name__}: {error}",
                metadata={"parse_success": False},
            )

    return score


@task
def l2d_replication(dataset_path: str) -> Task:
    records = load_l2d_csv(Path(dataset_path))
    samples = [
        Sample(
            id=record.item_id,
            input=f"Question: {record.question}\nNumeric answer:",
            target=str(record.truth),
            metadata=record.model_dump(mode="json"),
        )
        for record in records
    ]
    return Task(
        dataset=MemoryDataset(samples=samples, name="provtrust-l2d-replication"),
        solver=[system_message(L2D_SYSTEM), prior_external_posterior()],
        scorer=l2d_update_scorer(),
    )
