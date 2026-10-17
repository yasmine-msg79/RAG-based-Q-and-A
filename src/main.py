from fastapi import FastAPI
from routes import base, data, doc, subjects
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(base.base_router)
app.include_router(data.data_router)
app.include_router(doc.doc_router)
app.include_router(subjects.subjects_router)
