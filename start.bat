@echo off

echo Starting backend...
start "Backend" cmd /k "cd backend && uvicorn main:app --reload"

echo Starting frontend...
start "Frontend" cmd /k "cd frontend && npm start"

echo Both servers started in separate windows
echo Close those windows to stop the servers
