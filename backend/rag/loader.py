from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader


def load_pdf(pdf_path: str):
    """
    Loads a PDF and returns documents with page metadata.
    """
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()
    pdf_name = Path(pdf_path).name
    for index, document in enumerate(documents, start=1):
        document.metadata["pdf_name"] = pdf_name
        document.metadata["source_path"] = str(pdf_path)
        document.metadata["page_number"] = document.metadata.get("page_label") or document.metadata.get("page") or index
    return documents
