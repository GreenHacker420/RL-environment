import argparse
import json
import random
import numpy as np
import os
import sys

# Ensure the parent directory is in the path so we can import code_review_env
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from trl_env import CodeReviewGRPOEnv
except (ImportError, ModuleNotFoundError):
    from code_review_env.trl_env import CodeReviewGRPOEnv

def run_inference(url, episodes, seed):
    random.seed(seed)
    np.random.seed(seed)
    os.environ["ENV_URL"] = url
    
    env = CodeReviewGRPOEnv()
    results = []
    
    for i in range(episodes):
        difficulty = random.choice(["easy", "medium", "hard"])
        obs = env.reset(difficulty=difficulty)
        
        print(f"Episode {i+1}/{episodes} ({difficulty})")
        
        # Simulated interaction
        # 1. Identify a bug
        try:
            feedback_identify = env.identify_bug(bug_line=1, bug_type="logic", description="Mock identification")
            
            # 2. Submit a fix
            feedback_submit = env.submit_fix(fixed_code="# Mock fixed code\npass")
            
            results.append({
                "episode": i,
                "difficulty": difficulty,
                "reward": env.reward,
                "feedback": feedback_submit
            })
        except Exception as e:
            print(f"Error in episode {i}: {e}")
            results.append({
                "episode": i,
                "difficulty": difficulty,
                "error": str(e)
            })
        
    with open("results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    rewards = [r.get('reward', 0) for r in results if 'reward' in r]
    mean_reward = np.mean(rewards) if rewards else 0
    print(f"Results saved to results.json. Mean reward: {mean_reward}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", type=str, default="http://localhost:7860")
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    
    run_inference(args.url, args.episodes, args.seed)
