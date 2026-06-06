import subprocess
import os
import sys
import time

def main():
    # 1. Start the FastAPI backend server
    port = os.environ.get("PORT", "8000")
    print(f"🚀 Starting FastAPI backend on port {port}...")
    
    # Run uvicorn as a subprocess
    backend_process = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "main:app",
        "--host", "0.0.0.0",
        "--port", port
    ])

    # Give the backend 2 seconds to start up
    time.sleep(2)

    # 2. Start the LiveKit voice agent worker
    print("🎙️ Starting LiveKit voice agent worker...")
    agent_path = os.path.join("..", "voice_agent", "agent.py")
    
    agent_process = subprocess.Popen([
        sys.executable, agent_path, "start"
    ])

    try:
        # Keep running and monitor both processes
        while True:
            if backend_process.poll() is not None:
                print("❌ Backend process exited unexpectedly. Shutting down...")
                agent_process.terminate()
                sys.exit(backend_process.returncode)
                
            if agent_process.poll() is not None:
                print("❌ Agent worker process exited unexpectedly. Shutting down...")
                backend_process.terminate()
                sys.exit(agent_process.returncode)
                
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("Stopping both processes...")
        backend_process.terminate()
        agent_process.terminate()

if __name__ == "__main__":
    main()
