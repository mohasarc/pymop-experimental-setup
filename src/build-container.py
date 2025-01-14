import subprocess

with open('./.env', 'r') as file:
    GITHUB_TOKEN = file.read().strip().split('=')[1]

try:
    subprocess.run(["docker", "build", "-t", "denini/pymop-experiment", ".", "--build-arg", f"GITHUB_TOKEN={GITHUB_TOKEN}"], check=True)
except subprocess.CalledProcessError as e:
    print(f"Error building Docker image: {e}")
