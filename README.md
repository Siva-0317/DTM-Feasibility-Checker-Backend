# DTM Feasibility Checker Backend

Backend service for the Body-in-White (BIW) Door DTM Feasibility Checker. 
Parses STEP files using OpenCASCADE (pythonocc-core), runs DTM compliance rules, 
converts geometry to GLB for the frontend, and utilizes LLMs for remediation advice.

## Installation

This project requires a Conda environment because `pythonocc-core` is best installed via `conda-forge`.

1. **Create and activate a Conda environment:**
   ```bash
   conda create -n dtm_env python=3.11
   conda activate dtm_env
   ```

2. **Install pythonocc-core:**
   ```bash
   conda install -c conda-forge pythonocc-core -y
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Setup:**
   ```bash
   cp .env.example .env
   ```
   Open `.env` and fill in `HF_API_TOKEN` with your HuggingFace Inference API token.

## Running the Server

Start the FastAPI server:
```bash
uvicorn app.main:app --reload --port 8000
```

## API Usage Examples

**Upload a CAD file:**
```bash
curl -X POST "http://localhost:8000/api/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your_door_model.stp" \
  -F "door_type=front"
```

**Get Job Status & Analysis Results:**
```bash
curl -X GET "http://localhost:8000/api/analysis/<JOB_ID>" -H "accept: application/json"
```

**Get the Generated GLB Mesh:**
```bash
curl -X GET "http://localhost:8000/api/analysis/<JOB_ID>/mesh" --output model.glb
```

**Request AI Remediation Advice:**
```bash
curl -X POST "http://localhost:8000/api/remediation" \
  -H "Content-Type: application/json" \
  -d '{"job_id": "<JOB_ID>"}'
```
