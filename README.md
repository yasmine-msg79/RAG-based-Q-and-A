# RAG-Based Q&A

A document-based question-and-answer application that uses Retrieval-Augmented Generation (RAG) to help users explore PDF documents and generate practice questions from their content.

## Features

- **PDF Document Management:** Upload and manage PDF documents.
- **Text Extraction:** Extract text from PDFs, including support for OCR on scanned documents.
- **Text Chunking:** Split extracted content into smaller, overlapping chunks.
- **Semantic Embeddings:** Convert document chunks into vector representations.
- **Vector Storage:** Store and retrieve embeddings using ChromaDB.
- **Semantic Search:** Retrieve relevant document passages based on query similarity.
- **Question Generation:** Generate multiple-choice (MCQ) and true/false questions grounded in document content.
- **Question Management:** Store and retrieve generated questions.
- **Web Interface:** Access document and question-management functionality through an Angular frontend.
- **Local LLM Integration:** Use a locally hosted language model for question generation.

## Tech Stack

- **Backend:** Python, FastAPI
- **Frontend:** Angular, TypeScript, HTML, CSS
- **Database:** MySQL
- **Vector Database:** ChromaDB
- **Embeddings:** Sentence Transformers
- **LLM Runtime:** Ollama
- **OCR:** Tesseract

## How It Works

1. **Document Upload:** Users upload PDF learning materials.
2. **Text Extraction:** Document text is extracted, with OCR support for scanned pages.
3. **Chunking:** Extracted text is divided into overlapping chunks.
4. **Embedding:** Each chunk is converted into a vector embedding.
5. **Vector Storage:** Embeddings and associated content are stored in ChromaDB.
6. **Retrieval:** Semantic search retrieves passages relevant to the user's query.
7. **Question Generation:** Retrieved context is used to generate document-grounded practice questions.
8. **Review:** Users can access and review generated questions.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
