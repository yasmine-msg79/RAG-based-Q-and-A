# RAG-Based Q&A

A document-based question-and-answer application that uses Retrieval-Augmented Generation (RAG) to help users explore PDF documents and generate practice questions from their content.

Users can upload learning materials, retrieve relevant information through semantic search, and generate questions to support studying and revision.

## Features

- **PDF Upload:** Upload and manage PDF documents.
- **Text Extraction:** Extract text from PDFs, with OCR support for scanned documents.
- **Text Chunking:** Split document content into smaller, overlapping chunks.
- **Semantic Embeddings:** Represent document chunks as vectors for similarity-based retrieval.
- **Vector Database:** Store and retrieve document embeddings using ChromaDB.
- **Semantic Search:** Retrieve relevant document passages based on query similarity.
- **Question Generation:** Generate multiple-choice (MCQ) and true/false questions from document content.
- **Question Management:** Store and retrieve generated questions.
- **Web Interface:** Interact with documents and generated questions through an Angular frontend.
- **Local LLM Integration:** Support question generation using a locally hosted language model.

## Tech Stack

- **Backend:** Python, FastAPI
- **Frontend:** Angular, TypeScript, HTML, CSS
- **Database:** MySQL
- **Vector Database:** ChromaDB
- **Embeddings:** Sentence Transformers
- **Language Model Runtime:** Ollama
- **OCR:** Tesseract

## How It Works

1. **Upload:** Users upload PDF documents through the web interface.
2. **Extract:** The application extracts document text and supports OCR for scanned content.
3. **Chunk:** Extracted text is divided into smaller, overlapping chunks.
4. **Embed:** Text chunks are converted into vector embeddings.
5. **Store:** Embeddings and associated document content are stored in ChromaDB.
6. **Retrieve:** Semantic search identifies relevant passages for a user's query.
7. **Generate:** Retrieved context is used to generate document-grounded questions.
8. **Review:** Users can access and review generated questions.

## Getting Started

### Prerequisites

- Python 3.11 or compatible version
- Node.js and npm
- MySQL
- Tesseract OCR
- Ollama with a compatible language model

### Backend Setup

Clone the repository:

```bash
git clone https://github.com/yasmine-msg79/mini-rag.git
cd mini-rag
```

Install the backend dependencies from the project's requirements file:

```bash
pip install -r requirements.txt
```

Configure the required environment variables, database connection, and local language-model service.

Start the FastAPI server using the application's configured module path:

```bash
uvicorn <application_module>:app --reload
```

Replace `<application_module>` with the module containing the FastAPI application instance.

API documentation is available at:

`http://127.0.0.1:8000/docs`

### Frontend Setup

In a separate terminal, navigate to the frontend directory and install dependencies:

```bash
npm install
```

Start the Angular development server:

```bash
ng serve
```

Open `http://localhost:4200` in your browser.

## Future Improvements

- Enhance retrieval accuracy and context selection.
- Expand question-generation options and customization.
- Improve automated testing and deployment.
- Add further controls for reviewing and managing generated questions.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.