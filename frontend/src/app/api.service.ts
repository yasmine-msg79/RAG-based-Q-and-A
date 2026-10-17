
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  private readonly baseUrl = 'http://127.0.0.1:8000/api/v1';

  constructor(private http: HttpClient) {}

  uploadDocument(
    file: File,
    subjectName: string,
    documentName: string,
  ): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('subject_name', subjectName);
    formData.append('name', documentName);

    return this.http.post(
      `${this.baseUrl}/data/upload`,
      formData,
    );
  }

  getDocuments(subjectName: string): Observable<any> {
    const params = new HttpParams().set('subject_name', subjectName);

    return this.http.get(
      `${this.baseUrl}/subjects/documents`,
      { params },
    );
  }

  processDocument(documentId: number | string): Observable<any> {
    return this.http.post(
      `${this.baseUrl}/data/documents/${documentId}/process`,
      {},
    );
  }
}
