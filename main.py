from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from core.pipeline import Pipeline
import uvicorn
import argparse
from utils.logger import get_logger

# Initialize App
app = FastAPI(title="MP3 to TXT Service")
pipeline = Pipeline()
logger = get_logger("Main")

class ProcessRequest(BaseModel):
    source: str
    skip_download: bool = False

@app.post("/process")
def process_audio(request: ProcessRequest):
    try:
        result = pipeline.run(request.source, request.skip_download)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def run_cli(source):
    try:
        pipeline.run(source)
    except Exception as e:
        logger.error(f"CLI Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MP3 to TXT Service")
    parser.add_argument("source", nargs="?", help="Input source (File Path / URL / BV code)")
    parser.add_argument("--server", action="store_true", help="Run as Web Server")
    
    args = parser.parse_args()
    
    if args.server:
        uvicorn.run(app, host="0.0.0.0", port=8000)
    elif args.source:
        run_cli(args.source)
    else:
        # If no arguments, print help or run server by default? 
        # Better to print help to avoid confusion.
        parser.print_help()
