@echo off
echo ========================================================
echo   Starting LeadForge - AI Lead Management Platform
echo ========================================================
echo   Web Dashboard:  http://localhost:8000
echo   API Docs:       http://localhost:8000/docs
echo ========================================================
python -m uvicorn app.main:app --reload --port 8000
pause
