from pathlib import Path

from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter


class AdmissionDataLoader:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""],
        )

    def load_data(self, file_path: str) -> list[Document]:
        """Load and process admission data from file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, encoding="utf-8") as f:
            text = f.read()

        # Split text into chunks
        documents = self.text_splitter.create_documents([text])

        # Add metadata
        for doc in documents:
            doc.metadata["source"] = file_path
            doc.metadata["type"] = "admission_data"

        return documents
