# mini-rag

## Subjects and documents

Create a subject with `POST /api/v1/subjects` and a JSON body such as
`{"name": "Biology"}`. The server trims the name, generates an internal
subject ID, and rejects duplicate names without regard to case. Subject
records are persisted in `src/assets/subjects.json`; IDs are not exposed by the
API. Use `GET /api/v1/subjects` with no parameters or body to list subjects.

Upload a document with `POST /api/v1/data/upload`. Send `subject_name`, `name`,
and `file` as multipart fields (for example, `subject_name=Biology`,
`name=Lecture Notes`, and `file=@lecture-notes.pdf`); the server generates an
internal document ID that is not exposed by the API.
Document names must be unique within a subject, ignoring case. The uploaded
document file is stored directly under
`src/assets/files/{subject_name}/` (there is no extra document folder).
Document IDs, names, and filenames are currently persisted as one record per
line in `src/assets/documents.jsonl`. Existing records in
`src/assets/documents.json` are still read during this transition.

Use `GET /api/v1/subjects/documents` with a JSON body to list documents under a
subject:

```json
{"subject_name": "Biology"}
```

Add `document_name` to the body to retrieve one document. Answer and question
generation requests identify both the subject and document by name in the
JSON body. For example, `POST /api/v1/data/generate_answer`:

```json
{
  "subject_name": "Biology",
  "document_name": "Lecture Notes",
  "query": "Explain photosynthesis.",
  "top_k": 3
}
```

The question-generation endpoints also require `document_name` and accept
`subject_name`, `top_k`, and `num_questions`, for example:

```json
{
  "subject_name": "Biology",
  "document_name": "Lecture Notes",
  "top_k": 3,
  "num_questions": 5
}
```