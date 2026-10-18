
import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { forkJoin, of, timeout } from 'rxjs';
import { catchError, finalize } from 'rxjs/operators';
import { ApiService } from '../api.service';

interface DocumentItem {
  id: string | number;
  name: string;
  filename?: string;
}

interface QuestionItem {
  id: string | number;
  question: string;
  question_type: string;
  answers: any[];
  correct_answer?: any;
  explanation?: string;
  document_id?: string | number;
  [key: string]: any;
}

@Component({
  selector: 'app-question-bank',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './question-bank.html',
  styleUrl: './question-bank.css'
})
export class QuestionBankComponent implements OnInit {
  subjectId = '';
  subjectName = 'Subject';
  readonly String = String;

  documents: DocumentItem[] = [];
  questions: QuestionItem[] = [];

  isDocumentDropdownOpen = false;
  isTypeDropdownOpen = false;
  isPracticeDocumentDropdownOpen = false;
  isPracticeTypeDropdownOpen = false;

  selectedDocumentIds: string[] = [];
  selectedTypes: string[] = ['MCQ', 'TRUE_FALSE'];
  practiceDocumentIds: string[] = [];
  practiceTypes: string[] = ['MCQ', 'TRUE_FALSE'];

  questionTypes = [
    { value: 'MCQ', label: 'Multiple choice' },
    { value: 'TRUE_FALSE', label: 'True / False' }
  ];

  numQuestions = 5;
  topK = 3;

  loadingDocuments = false;
  loadingQuestions = false;
  generatingQuestions = false;

  errorMessage = '';
  successMessage = '';

  private documentsRequestInProgress = false;

  constructor(
    private readonly api: ApiService,
    private readonly route: ActivatedRoute,
    private readonly router: Router,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.subjectId = this.route.snapshot.paramMap.get('subjectId') ?? '';

    if (!this.subjectId) {
      this.router.navigate(['/subjects']);
      return;
    }

    this.loadSubjectName();
    this.loadDocuments();
  }

  private getArray(response: any, keys: string[]): any[] {
    if (Array.isArray(response)) return response;

    for (const key of keys) {
      if (Array.isArray(response?.[key])) return response[key];
    }

    return [];
  }

  private loadSubjectName(): void {
    this.api.getSubjects().subscribe({
      next: (response: any) => {
        const subjects = this.getArray(response, [
          'subjects', 'data', 'items', 'results'
        ]);

        const subject = subjects.find(
          (item: any) => String(item.id) === this.subjectId
        );

        if (subject) this.subjectName = subject.name;
      },
      error: (error: any) => {
        console.error('Could not load subject name:', error);
      }
    });
  }

  loadDocuments(): void {
    this.loadingDocuments = true;
    this.errorMessage = '';
    this.cdr.detectChanges();

    this.api.getDocuments(this.subjectId)
      .pipe(
        finalize(() => {
          this.loadingDocuments = false;
          this.cdr.detectChanges();

          console.log(
            '[QuestionBank] Final loading state:',
            this.loadingDocuments
          );
        })
      )
      .subscribe({
        next: (response: any) => {
          const docs = this.getArray(response, [
            'documents', 'data', 'items', 'results'
          ]);

          this.documents = docs.map((doc: any) => ({
            ...doc,
            id: String(doc.id)
          }));

          this.selectedDocumentIds =
            this.documents.map(doc => String(doc.id));

          this.practiceDocumentIds =
            this.documents.map(doc => String(doc.id));

          this.loadSavedQuestions();
        },
        error: (error: any) => {
          console.error('[QuestionBank] Failed to load documents:', error);
          this.errorMessage = this.errorDetail(error);
        }
      });
  }

  private normalizeType(value: any): string {
    const type = String(value ?? '').toUpperCase().replace(/[- ]/g, '_');

    if (type === 'TRUEFALSE' || type === 'TRUE_FALSE') return 'TRUE_FALSE';
    if (type === 'MULTIPLE_CHOICE' || type === 'MULTIPLECHOICE') return 'MCQ';

    return type;
  }

  get visibleQuestions(): QuestionItem[] {
    const documentIds = new Set(this.selectedDocumentIds);
    const types = new Set(this.selectedTypes);

    return this.questions.filter(question =>
      documentIds.has(String(question.document_id)) &&
      types.has(this.normalizeType(question.question_type))
    );
  }

  get allDocumentsSelected(): boolean {
    return this.documents.length > 0 &&
      this.selectedDocumentIds.length === this.documents.length;
  }

  get allPracticeDocumentsSelected(): boolean {
    return this.documents.length > 0 &&
      this.practiceDocumentIds.length === this.documents.length;
  }

  get selectedDocumentLabel(): string {
    if (this.allDocumentsSelected) return 'All documents';
    if (!this.selectedDocumentIds.length) return 'No documents selected';

    return `${this.selectedDocumentIds.length} document(s) selected`;
  }

  get selectedPracticeDocumentLabel(): string {
    if (this.allPracticeDocumentsSelected) return 'All documents';
    if (!this.practiceDocumentIds.length) return 'No documents selected';

    return `${this.practiceDocumentIds.length} document(s) selected`;
  }

  toggleDocumentSelection(id: string | number, checked: boolean): void {
    const value = String(id);

    this.selectedDocumentIds = checked
      ? [...new Set([...this.selectedDocumentIds, value])]
      : this.selectedDocumentIds.filter(item => item !== value);

    this.loadSavedQuestions();
  }

  toggleAllDocumentSelection(checked: boolean): void {
    this.selectedDocumentIds = checked
      ? this.documents.map(document => String(document.id))
      : [];

    this.loadSavedQuestions();
  }

  toggleTypeSelection(type: string, checked: boolean): void {
    this.selectedTypes = checked
      ? [...new Set([...this.selectedTypes, type])]
      : this.selectedTypes.filter(item => item !== type);
  }

  togglePracticeDocument(id: string | number, checked: boolean): void {
    const value = String(id);

    this.practiceDocumentIds = checked
      ? [...new Set([...this.practiceDocumentIds, value])]
      : this.practiceDocumentIds.filter(item => item !== value);
  }

  toggleAllPracticeDocuments(checked: boolean): void {
    this.practiceDocumentIds = checked
      ? this.documents.map(document => String(document.id))
      : [];
  }

  togglePracticeType(type: string, checked: boolean): void {
    this.practiceTypes = checked
      ? [...new Set([...this.practiceTypes, type])]
      : this.practiceTypes.filter(item => item !== type);
  }

  private loadSavedQuestions(): void {
    const ids = [...this.selectedDocumentIds];

    if (ids.length === 0) {
      this.questions = [];
      this.loadingQuestions = false;
      return;
    }

    this.loadingQuestions = true;

    forkJoin(
      ids.map(id =>
        this.api.getDocumentQuestions(id).pipe(
          catchError(error => {
            console.error(`Could not load questions for document ${id}:`, error);
            return of([]);
          })
        )
      )
    )
      .pipe(finalize(() => {
        this.loadingQuestions = false;
      }))
      .subscribe({
        next: responses => {
          this.questions = [];

          responses.forEach((response: any, index: number) => {
            const items = this.getArray(response, [
              'questions', 'data', 'items', 'results'
            ]);

            items.forEach((question: any) => {
              this.questions.push({
                ...question,
                document_id: question.document_id ?? ids[index]
              });
            });
          });

          console.log('Saved questions loaded:', this.questions.length);
        },
        error: error => {
          console.error('Could not load saved questions:', error);
          this.errorMessage = this.errorDetail(error);
        }
      });
  }


  generateQuestions(): void {
    this.errorMessage = '';
    this.successMessage = '';

    if (!this.selectedDocumentIds.length) {
      this.errorMessage = 'Select at least one document.';
      return;
    }

    if (!this.selectedTypes.length) {
      this.errorMessage = 'Select at least one question type.';
      return;
    }

    if (
      !Number.isInteger(this.numQuestions) ||
      this.numQuestions < 1 ||
      this.numQuestions > 50
    ) {
      this.errorMessage = 'Choose between 1 and 50 questions per type.';
      return;
    }

    const requests = this.selectedDocumentIds.flatMap(documentId =>
      this.selectedTypes.map(type =>
        (
          type === 'MCQ'
            ? this.api.generateMCQs(documentId, this.numQuestions, this.topK)
            : this.api.generateTrueFalse(documentId, this.numQuestions, this.topK)
        ).pipe(
          timeout(120000),
          catchError(error =>
            of({
              generationError: this.errorDetail(error),
              documentId,
              type
            })
          )
        )
      )
    );

    this.generatingQuestions = true;
    this.cdr.detectChanges();

    forkJoin(requests)
      .pipe(
        finalize(() => {
          this.generatingQuestions = false;
          this.cdr.detectChanges();
        })
      )
      .subscribe({
        next: results => {
          const failures = results.filter(
            (result: any) => result?.generationError
          );

          if (failures.length) {
            this.errorMessage =
              `${failures.length} generation request(s) failed. Check the backend logs or try again.`;
          } else {
            this.successMessage = 'Questions generated successfully.';
          }

          this.loadSavedQuestions();
          this.cdr.detectChanges();
        },
        error: error => {
          this.errorMessage = this.errorDetail(error);
          this.cdr.detectChanges();
        }
      });
  }



  startPracticeQuiz(): void {
    if (!this.practiceDocumentIds.length) {
      this.errorMessage = 'Select at least one document.';
      return;
    }

    if (!this.practiceTypes.length) {
      this.errorMessage = 'Select at least one question type.';
      return;
    }

    this.errorMessage = '';
    console.log('Practice documents:', this.practiceDocumentIds);
    console.log('Practice types:', this.practiceTypes);
    console.log('Subject ID:', this.subjectId);
    this.router.navigate(
      ['/subjects', this.subjectId, 'quiz'],
      {
        queryParams: {
          documents: this.practiceDocumentIds.join(','),
          types: this.practiceTypes.join(',')
        }
      }
    ).then(success => {
      console.log('Navigation succeeded:', success);
      console.log('Current URL:', this.router.url);
    }).catch(error => {
      console.error('Navigation failed:', error);
    });
  }

  backToDocuments(): void {
    this.router.navigate(['/subjects']);
  }

  private errorDetail(error: any): string {
    return error?.error?.detail ||
      error?.error?.message ||
      error?.message ||
      'Something went wrong. Please try again.';
  }

  questionTypeLabel(type: string): string {
    return this.normalizeType(type) === 'MCQ'
      ? 'Multiple choice'
      : 'True / False';
  }

  trackDocument(_index: number, document: DocumentItem): string {
    return String(document.id);
  }

  trackQuestion(_index: number, question: QuestionItem): string {
    return String(question.id);
  }
}
