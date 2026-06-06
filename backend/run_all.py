import subprocess
import os
import sys
import time

def main():
    # Change working directory to the script's folder to ensure relative paths work
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # 1. Start the FastAPI backend server
    port = os.environ.get("PORT", "8000")
    
    # Dynamically inject the correct local backend URL with the correct port
    os.environ["BACKEND_URL"] = f"http://127.0.0.1:{port}"
    print(f"Set BACKEND_URL to http://127.0.0.1:{port} for agent worker")
    
    print(f"[START] Starting FastAPI backend on port {port}...")
    
    # Run uvicorn as a subprocess
    backend_process = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "main:app",
        "--host", "0.0.0.0",
        "--port", port
    ])

    # Give the backend 2 seconds to start up
    time.sleep(2)

    # 2. Start the LiveKit voice agent worker
    print("[WORKER] Starting LiveKit voice agent worker...")
    agent_path = os.path.join("..", "voice_agent", "agent.py")
    
    agent_process = subprocess.Popen([
        sys.executable, agent_path, "start"
    ])

    try:
        # Keep running and monitor both processes
        while True:
            if backend_process.poll() is not None:
                print("[ERROR] Backend process exited unexpectedly. Shutting down...")
                agent_process.terminate()
                sys.exit(backend_process.returncode)
                
            if agent_process.poll() is not None:
                print("[ERROR] Agent worker process exited unexpectedly. Shutting down...")
                backend_process.terminate()
                sys.exit(agent_process.returncode)
                
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("Stopping both processes...")
        backend_process.terminate()
        agent_process.terminate()

if __name__ == "__main__":
    main()
