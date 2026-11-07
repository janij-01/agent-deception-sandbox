# Sandbox plan

Working plan from the team thread. The split is open to change.

## Setup

Valerio’s sandbox with 3 agents: a leader, a subordinate, and an adversarial agent.

## Conditions

- **A.** The adversary targets the leader first.
- **B.** The adversary targets the subordinate first.

## Research questions

- Who is easier to deceive, the leader or the subordinate?
- Once deceived, does it spread? Leader → subordinate versus subordinate → leader: which direction spreads more?

Both questions come from the same two conditions, so it is one set of runs.

## Split

- **Valerio:** lower task difficulty so baseline deception is above zero.
- **Janie:** add condition B, plus an LLM judge to score each trial.
- **Hannah:** experiment design and stats, and lead the writeup. If time allows, run the judge on AI Village transcripts as a real-world check.

## Current prompts

Condition A instructions are in `prompts/`. Condition B is not written yet.
