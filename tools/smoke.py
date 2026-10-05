# voices/tools/smoke.py
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.character import create_character
from sim.world import create_world
from sim.loop import simulation_tick
from sim.traces import active_traces


def run(ticks: int, seed=None) -> None:
    if seed is not None:
        import random
        random.seed(seed)

    character = create_character("smoke")
    world = create_world(0)

    actions = {}
    crises = 0
    trace_events = 0

    for _ in range(ticks):
        result = simulation_tick(character, world)
        actions[result.action_id] = actions.get(result.action_id, 0) + 1
        if result.crisis:
            crises += 1
        trace_events += len(result.mutations)

    print(f"ticks={ticks}")
    print(f"crises={crises}")
    print(f"trace_events={trace_events}")
    print(f"active_traces={len(active_traces(character.traces))}")

    voices_line = " ".join(
        f"{name}={round(v.weight, 3)}"
        for name, v in character.voices.items()
    )
    print(f"voices= {voices_line}")

    top = sorted(actions.items(), key=lambda kv: kv[1], reverse=True)[:5]
    top_line = " ".join(f"{aid}={cnt}" for aid, cnt in top)
    print(f"top_actions= {top_line}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticks", type=int, default=200)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    run(args.ticks, args.seed)


if __name__ == "__main__":
    main()
