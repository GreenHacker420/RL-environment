from core.env_server import create_fastapi_app

from .environment import DrugInteractionEnv


env = DrugInteractionEnv()
app = create_fastapi_app(env)
