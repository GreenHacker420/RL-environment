from openenv.core.env_server import create_fastapi_app

from models import DrugAction, DrugObservation
from .environment import DrugInteractionEnv


app = create_fastapi_app(
    env=DrugInteractionEnv,
    action_cls=DrugAction,
    observation_cls=DrugObservation,
    max_concurrent_envs=2,
)
