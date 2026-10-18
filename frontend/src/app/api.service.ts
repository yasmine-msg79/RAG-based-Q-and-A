
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, switchMap } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private readonly baseUrl = 'http://127.0.0.1:8000/api/v1';

  constructor(private readonly http: HttpClient) {}

  // ---------- Subjects ----------

  getSubjects(): Observable<any> {
    return this.http.get(`${this.baseUrl}/subjects`);
  }

  createSubject(name: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/subjects`, { name });
  }

  // ---------- Documents ----------

  getDocuments(subjectId: string | number): Observable<any> {
    const params = new HttpParams().set('subject_id', String(subjectId));

    return this.http.get(`${this.baseUrl}/subjects/documents`, { params });
  }

  uploadDocument(
    file: File,
    subjectId: string | number,
    documentName: string
  ): Observable<any> {
    const form = new FormData();

    form.append('file', file);
    form.append('subject_id', String(subjectId));
    form.append('name', documentName);

    return this.http.post<any>(`${this.baseUrl}/data/upload`, form).pipe(
      switchMap((uploadResponse: any) => {
        const documentId =
          uploadResponse?.document?.id ??
          uploadResponse?.document_id ??
          uploadResponse?.id;

        if (documentId == null) {
          throw new Error(
            'Upload succeeded, but the response did not include the document ID needed for processing.'
          );
        }

        return this.processDocument(documentId).pipe(
          // Preserve the upload response for the component.
          switchMap((processResponse: any) => [
            {
              upload: uploadResponse,
              processing: processResponse
            }
          ])
        );
      })
    );
  }

  processDocument(id: string | number): Observable<any> {
    return this.http.post(
      `${this.baseUrl}/data/documents/${encodeURIComponent(String(id))}/process`,
      {}
    );
  }

  deleteDocument(id: string | number): Observable<any> {
    return this.http.delete(
      `${this.baseUrl}/data/documents/${encodeURIComponent(String(id))}`
    );
  }

  // ---------- Questions ----------

  getDocumentQuestions(id: string | number): Observable<any> {
    return this.http.get(
      `${this.baseUrl}/data/documents/${encodeURIComponent(String(id))}/questions`
    );
  }

  // ---------- Optional query helpers ----------

  getDocumentDetails(id: string | number): Observable<any> {
    return this.http.get(
      `${this.baseUrl}/documents/${encodeURIComponent(String(id))}`
    );
  }

  getSubjectQuestions(subjectId: string | number): Observable<any> {
    return this.http.get(
      `${this.baseUrl}/data/questions/subject/${encodeURIComponent(String(subjectId))}`
    );
  }

  
  generateMCQs(
    documentId: string | number,
    numQuestions: number,
    topK: number = 3
  ): Observable<any> {
    return this.http.post(
      `${this.baseUrl}/data/documents/${encodeURIComponent(String(documentId))}/generate_mcqs`,
      {
        num_questions: numQuestions,
        top_k: topK
      }
    );
  }

  generateTrueFalse(
    documentId: string | number,
    numQuestions: number,
    topK: number = 3
  ): Observable<any> {
    return this.http.post(
      `${this.baseUrl}/data/documents/${encodeURIComponent(String(documentId))}/generate_true_false`,
      {
        num_questions: numQuestions,
        top_k: topK
      }
    );
  }

}
