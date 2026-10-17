
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from './api.service';

interface DocumentItem {
  id: number | string;
  name: string;
  filename?: string;
  status?: string;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App implements OnInit {
  searchTerm = '';
  uploadOpen = false;
  subjectName = '';
  documentName = '';
  selectedFile: File | null = null;

  documents: DocumentItem[] = [];
  loading = false;
  uploading = false;
  processingId: number | string | null = null;
  errorMessage = '';
  successMessage = '';

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    // Enter a subject name to load its documents.
  }

  get filteredDocuments(): DocumentItem[] {
    const term = this.searchTerm.trim().toLowerCase();

    if (!term) return this.documents;

    return this.documents.filter((doc) =>
      `${doc.name} ${doc.filename ?? ''}`.toLowerCase().includes(term),
    );
  }

  openUpload(): void {
    this.errorMessage = '';
    this.successMessage = '';
    this.uploadOpen = true;
  }

  closeUpload(): void {
    this.uploadOpen = false;
  }

  selectFile(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;

    if (file && !file.name.toLowerCase().endsWith('.pdf')) {
      this.errorMessage = 'Please select a PDF file.';
      this.selectedFile = null;
      input.value = '';
      return;
    }

    this.errorMessage = '';
    this.selectedFile = file;

    if (file && !this.documentName.trim()) {
      this.documentName = file.name.replace(/\.pdf$/i, '');
    }
  }

  loadDocuments(): void {
    const subject = this.subjectName.trim();

    if (!subject) {
      this.errorMessage = 'Enter a subject name to load its documents.';
      return;
    }

    this.loading = true;
    this.errorMessage = '';
    this.successMessage = '';

    this.api.getDocuments(subject).subscribe({
      next: (response) => {
        const rows = Array.isArray(response)
          ? response
          : response?.documents ?? response?.data ?? [];

        this.documents = rows.map((item: any) => ({
          id: item.id ?? item.ID ?? item.document_id ?? item.DOC_ID,
          name: item.name ?? item.NAME ?? item.document_name ?? item.FILENAME ?? item.filename ?? 'Unnamed document',
          filename: item.filename ?? item.FILENAME,
          status: item.status ?? item.STATUS ?? 'Uploaded',
        }));

        this.loading = false;
      },
      error: (error) => {
        this.loading = false;
        this.errorMessage =
          error.error?.message ??
          'Could not load documents. Check the subject name and backend.';
      },
    });
  }

  uploadDocument(): void {
    if (!this.subjectName.trim() || !this.documentName.trim() || !this.selectedFile) {
      this.errorMessage = 'Enter a subject and document name, then choose a PDF.';
      return;
    }

    this.uploading = true;
    this.errorMessage = '';
    this.successMessage = '';

    this.api
      .uploadDocument(
        this.selectedFile,
        this.subjectName.trim(),
        this.documentName.trim(),
      )
      .subscribe({
        next: () => {
          this.uploading = false;
          this.successMessage = 'PDF uploaded successfully.';
          this.closeUpload();
          this.loadDocuments();
          this.selectedFile = null;
          this.documentName = '';
        },
        error: (error) => {
          this.uploading = false;
          this.errorMessage =
            error.error?.message ?? 'Upload failed. Check the backend logs.';
        },
      });
  }

  processDocument(document: DocumentItem): void {
    this.processingId = document.id;
    this.errorMessage = '';
    this.successMessage = '';

    this.api.processDocument(document.id).subscribe({
      next: () => {
        this.processingId = null;
        this.successMessage = `Processing started or completed for "${document.name}".`;
        this.loadDocuments();
      },
      error: (error) => {
        this.processingId = null;
        this.errorMessage =
          error.error?.message ?? `Could not process "${document.name}".`;
      },
    });
  }
}
