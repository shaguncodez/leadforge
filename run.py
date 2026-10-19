"""LeadForge quick launcher script."""
import uvicorn

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Starting LeadForge — AI Lead Management & Scoring Platform")
    print("🌐 Web Dashboard: http://localhost:8000")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("=" * 60)
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
