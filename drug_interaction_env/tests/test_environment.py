from dataclasses import asdict

from models import DrugAction
from server.environment import DrugInteractionEnv


def test_reset_returns_observation_defaults() -> None:
    env = DrugInteractionEnv()
    observation = env.reset()
    assert observation.done is False
    assert observation.reward == 0.0


def test_step_returns_done_true_and_float_reward() -> None:
    env = DrugInteractionEnv()
    env.reset()
    observation = env.step(DrugAction(severity="moderate", explanation="Possible interaction."))
    assert observation.done is True
    assert isinstance(observation.reward, float)


def test_state_property_is_pure() -> None:
    env = DrugInteractionEnv()
    env.reset()
    first = asdict(env.state)
    second = asdict(env.state)
    assert first == second


def test_reset_generates_new_episode_ids() -> None:
    env = DrugInteractionEnv()
    first = env.reset()
    second = env.reset()
    assert first.metadata["episode_id"] != second.metadata["episode_id"]


def test_safety_violation_counter_increments() -> None:
    env = DrugInteractionEnv()
    while True:
        observation = env.reset()
        if observation.task_type == "easy" and observation.metadata["input_data"]["drug1"] == "warfarin" and observation.metadata["input_data"]["drug2"] == "aspirin":
            break
    env.step(DrugAction(severity="none", explanation="No interaction."))
    assert env.state.safety_violations == 1
