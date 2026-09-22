import uvicorn
import os
import sys

# Ensure backend root is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

if __name__ == "__main__":
    print("=" * 65)
    print(" Legal Metrology Compliance Verification Backend (SIH26034)")
    print(" Starting FastAPI on http://localhost:8088")
    print("=" * 65)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8088, reload=False)
