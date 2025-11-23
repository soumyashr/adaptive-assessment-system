#!/bin/bash

# Start backend
echo "Starting backend..."
cd backend
uvicorn main:app --reload &
BACKEND_PID=$!

# Start frontend
echo "Starting frontend..."
cd ../frontend
npm start &
FRONTEND_PID=$!

# Function to cleanup on exit
cleanup() {
    echo "Stopping servers..."
    kill $BACKEND_PID
    kill $FRONTEND_PID
    exit
}

# Trap CTRL+C
trap cleanup INT

# Wait for both processes
wait