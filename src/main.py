import uvicorn
from dotenv import load_dotenv

from config import settings

if __name__ == "__main__":
    uvicorn.run(
        "src.controllers.front_controller:app",
        host=settings.app.host,
        port=settings.app.port,
        reload=settings.app.reload
    )