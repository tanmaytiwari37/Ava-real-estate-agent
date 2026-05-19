FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt
RUN python -m livekit.agents download-files

COPY . .

CMD ["python", "agent.py", "start"]