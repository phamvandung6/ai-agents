import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from src.agents.admission_agent import AdmissionDataLoader, AdmissionVectorStore

router = APIRouter()


@router.post("/upload-admission-data")
async def upload_admission_data(file: UploadFile):
    """Upload and process admission data file."""
    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are allowed")

    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        # Initialize components
        data_loader = AdmissionDataLoader()
        vector_store = AdmissionVectorStore()

        # Load and process documents
        documents = data_loader.load_data(temp_path)

        # Clear existing collection and add new documents
        await vector_store.delete_collection()
        await vector_store.add_documents(documents)

        # Clean up temporary file
        Path(temp_path).unlink()

        return JSONResponse(
            content={
                "message": "Admission data uploaded and processed successfully",
                "num_documents": len(documents),
            },
            status_code=200,
        )

    except Exception as e:
        # Clean up temporary file in case of error
        if "temp_path" in locals():
            Path(temp_path).unlink()
        raise HTTPException(status_code=500, detail=str(e))
