# phani-flask-backend

# setup
python -m venv .venv
.venv/Scripts/activate

# install dependenices 
pip install -r requirements.txt

# start application
- python app.py
we will see Running on http://127.0.0.1:5000/

1. Test health checks (open new terminal)
curl http://localhost:5001/health
Expected: healthy

2. Readiness Probe
curl http://localhost:5001/readiness
Expected: {"status": "ready"}

3. Liveness Probe
curl http://localhost:5001/liveness
Expected: {"status": "alive"}

4. Test Query endpoint
curl -X POST http://localhost:5001/query \
    -H "Content-Type: application/json" \
    -d "{"query": "What benefits do I get with Club Lloyds?"}"
Expected: 
{
    "answer": "Echo: What benefits do I get with Club Lloyds?",
    "citations": [],
    "id":"test-123"
}