from fastapi import FastAPI
from routes import base, data, doc, subjects
app = FastAPI()

app.include_router(base.base_router)
app.include_router(data.data_router)
app.include_router(doc.doc_router)
app.include_router(subjects.subjects_router)
