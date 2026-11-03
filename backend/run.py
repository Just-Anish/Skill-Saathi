import sys
import os
from dotenv import load_dotenv

# Explicitly point to the backend/.env file since you run the server from the root directory
load_dotenv("backend/.env")
# Ensure project root is in python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "127.0.0.1")
    uvicorn.run("backend.app.main:app", host=host, port=port, reload=True)

