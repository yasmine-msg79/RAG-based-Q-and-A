
import { CommonModule } from '@angular/common';
import {
  ChangeDetectorRef,
  Component,
  inject,
  OnDestroy,
  OnInit
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { forkJoin, of, Subscription } from 'rxjs';
import { catchError, finalize, timeout } from 'rxjs/operators';
import { ApiService } from '../api.service';
import { Router } from '@angular/router';

interface SubjectItem {
  id: string | number;
  name: string;
}

interface DocumentItem {
  id: string | number;
  name: string;
  filename?: string;
  status?: string;
}

interface AnswerItem {
  [key: string]: any;
}

interface QuestionItem {
  id: string | number;
  question: string;
  question_type: string;
  answers: AnswerItem[];
  correct_answer?: any;
  explanation?: string;
  selectedAnswer: string;
  submitted: boolean;
}

@Component({
  selector: 'app-documents',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './documents.html',
  styleUrl: './documents.css'
})
export class DocumentsComponent implements OnInit, OnDestroy {
  subjects: SubjectItem[] = [];
  documents: DocumentItem[] = [];
  questions: QuestionItem[] = [];

  selectedSubject: SubjectItem | null = null;

  loadingSubjects = false;
  loadingDocuments = false;
  loadingQuestions = false;
  creatingSubject = false;
  uploading = false;
  generatingQuestions = false;
  numQuestions = 5;

  processingDocumentId: string | null = null;
  deletingId: string | null = null;

  showCreateSubject = false;
  showUploadModal = false;
  showQuestionBank = false;

  newSubjectName = '';
  documentName = '';
  selectedFile: File | null = null;
  searchTerm = '';

  errorMessage = '';
  successMessage = '';

  documentDropdownOpen = false;
  typeDropdownOpen = false;

  selectedDocumentIds: string[] = [];
  selectedTypes: string[] = ['MCQ', 'TRUE_FALSE'];

  questionTypes = [
    { label: 'Multiple choice', value: 'MCQ' },
    { label: 'True / False', value: 'TRUE_FALSE' }
  ];

  private documentsSub?: Subscription;
  private questionsSub?: Subscription;
  private messageTimer?: ReturnType<typeof setTimeout>;

  private readonly cdr = inject(ChangeDetectorRef);

  constructor(private readonly api: ApiService, private readonly router: Router) {}

  ngOnInit(): void {
    this.loadSubjects();
  }

  ngOnDestroy(): void {
    this.documentsSub?.unsubscribe();
    this.questionsSub?.unsubscribe();
    clearTimeout(this.messageTimer);
  }

  // ---------- General helpers ----------

  private refresh(): void {
    this.cdr.markForCheck();
  }

  private showError(message: string): void {
    clearTimeout(this.messageTimer);
    this.successMessage = '';
    this.errorMessage = message;
  }

  private showSuccess(message: string): void {
    clearTimeout(this.messageTimer);
    this.errorMessage = '';
    this.successMessage = message;

    this.messageTimer = setTimeout(() => {
      this.successMessage = '';
      this.refresh();
    }, 5000);
  }

  private getArray(response: any, keys: string[] = []): any[] {
    if (Array.isArray(response)) {
      return response;
    }

    if (!response || typeof response !== 'object') {
      return [];
    }

    for (const key of keys) {
      if (Array.isArray(response[key])) {
        return response[key];
      }
    }

    for (const key of ['data', 'result', 'results', 'items']) {
      if (response[key] !== undefined) {
        const result = this.getArray(response[key], keys);

        if (result.length || Array.isArray(response[key])) {
          return result;
        }
      }
    }

    return [];
  }

  private firstValue(obj: any, keys: string[]): any {
    for (const key of keys) {
      if (obj?.[key] !== undefined && obj[key] !== null) {
        return obj[key];
      }
    }

    return undefined;
  }

  private errorDetail(error: any, fallback: string): string {
    const detail = error?.error?.detail ?? error?.error?.message;

    if (typeof detail === 'string') {
      return detail;
    }

    if (Array.isArray(detail)) {
      return detail.map(item => item.msg ?? String(item)).join(', ');
    }

    return fallback;
  }

  idString(id: string | number): string {
    return String(id);
  }

  get filteredDocuments(): DocumentItem[] {
    const term = this.searchTerm.trim().toLowerCase();

    if (!term) {
      return this.documents;
    }

    return this.documents.filter(document =>
      document.name.toLowerCase().includes(term) ||
      (document.filename || '').toLowerCase().includes(term)
    );
  }

  // ---------- Subjects ----------

  loadSubjects(preferredName?: string): void {
    this.loadingSubjects = true;
    this.errorMessage = '';

    this.api.getSubjects().pipe(
      timeout(15000),
      finalize(() => {
        this.loadingSubjects = false;
        this.refresh();
      })
    ).subscribe({
      next: (response: any) => {
        console.log('GET SUBJECTS response:', response);

        const items = this.getArray(response, ['subjects']);

        this.subjects = items
          .map((item: any): SubjectItem | null => {
            if (!item || typeof item !== 'object') {
              return null;
            }

            const name = item.name ?? item.subject_name ?? item.title;
            const id = item.id ?? item.subject_id;

            if (
              name === undefined ||
              name === null ||
              String(name).trim() === '' ||
              id === undefined ||
              id === null
            ) {
              console.warn('Skipping subject without an ID or name:', item);
              return null;
            }

            return {
              id: String(id),
              name: String(name)
            };
          })
          .filter(
            (item: SubjectItem | null): item is SubjectItem => item !== null
          )
          .filter((item, index, list) =>
            list.findIndex(other => String(other.id) === String(item.id)) === index
          );

        let nextSubject = preferredName
          ? this.subjects.find(subject => subject.name === preferredName)
          : undefined;

        if (!nextSubject && this.selectedSubject) {
          nextSubject = this.subjects.find(
            subject => String(subject.id) === String(this.selectedSubject!.id)
          );
        }

        if (!nextSubject && this.subjects.length > 0) {
          nextSubject = this.subjects[0];
        }

        if (nextSubject) {
          this.selectSubject(nextSubject);
        } else {
          this.documentsSub?.unsubscribe();
          this.questionsSub?.unsubscribe();
          this.selectedSubject = null;
          this.documents = [];
          this.questions = [];
        }
      },
      error: (error: any) => {
        console.error('GET SUBJECTS failed:', error);

        this.showError(
          `Could not load subjects (HTTP ${error.status || 'unknown'}). Check the backend and API URL.`
        );
      }
    });
  }

  createSubject(): void {
    const name = this.newSubjectName.trim();

    if (!name || this.creatingSubject) {
      return;
    }

    this.creatingSubject = true;
    this.errorMessage = '';
    this.successMessage = '';

    this.api.createSubject(name).pipe(
      timeout(15000),
      finalize(() => {
        this.creatingSubject = false;
        this.refresh();
      })
    ).subscribe({
      next: () => {
        this.newSubjectName = '';
        this.showCreateSubject = false;
        this.showSuccess(`Subject "${name}" created.`);
        this.loadSubjects(name);
      },
      error: (error: any) => {
        console.error('Failed to create subject:', error);

        this.showError(
          error?.status === 409
            ? 'A subject with that name already exists.'
            : this.errorDetail(error, 'Could not create the subject.')
        );
      }
    });
  }

  selectSubject(subject: SubjectItem): void {
    this.documentsSub?.unsubscribe();
    this.questionsSub?.unsubscribe();

    this.selectedSubject = subject;
    this.documents = [];
    this.questions = [];
    this.selectedDocumentIds = [];
    this.searchTerm = '';
    this.showQuestionBank = false;
    this.documentDropdownOpen = false;
    this.typeDropdownOpen = false;

    this.loadDocuments();
  }

  // ---------- Documents ----------

  loadDocuments(): void {
    if (!this.selectedSubject) {
      this.documents = [];
      this.loadingDocuments = false;
      return;
    }

    const subjectId = String(this.selectedSubject.id);

    this.documentsSub?.unsubscribe();
    this.loadingDocuments = true;
    this.errorMessage = '';

    this.documentsSub = this.api.getDocuments(subjectId).pipe(
      timeout(20000),
      finalize(() => {
        this.loadingDocuments = false;
        this.refresh();
      })
    ).subscribe({
      next: (response: any) => {
        console.log('GET DOCUMENTS response:', response);

        const items = this.getArray(response, ['documents']);

        this.documents = items
          .filter((item: any) => item && typeof item === 'object')
          .map((item: any): DocumentItem => ({
            id: item.id ?? item.document_id,
            name: String(
              item.name ??
              item.document_name ??
              item.filename ??
              ''
            ),
            filename: item.filename ?? item.file_name ?? item.name,
            status: item.status ?? item.processing_status ?? 'Uploaded'
          }))
          .filter(document =>
            document.id !== undefined &&
            document.id !== null &&
            document.name.length > 0
          );

        const validIds = new Set(
          this.documents.map(document => String(document.id))
        );

        this.selectedDocumentIds = this.selectedDocumentIds.filter(
          id => validIds.has(id)
        );

        console.log('Normalized documents:', this.documents);
      },
      error: (error: any) => {
        console.error('GET DOCUMENTS failed:', error);
        this.documents = [];

        this.showError(
          error.status === 0
            ? 'Cannot connect to the backend. Check that FastAPI is running.'
            : this.errorDetail(
                error,
                `Could not load documents (HTTP ${error.status || 'unknown'}).`
              )
        );
      }
    });
  }

  openUploadModal(): void {
    if (!this.selectedSubject) {
      this.showError('Create or select a subject first.');
      return;
    }

    this.documentName = '';
    this.selectedFile = null;
    this.showUploadModal = true;
  }

  closeUploadModal(): void {
    if (this.uploading) {
      return;
    }

    this.showUploadModal = false;
    this.selectedFile = null;
    this.documentName = '';
  }

  chooseFile(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;

    if (!file) {
      return;
    }

    if (
      file.type !== 'application/pdf' &&
      !file.name.toLowerCase().endsWith('.pdf')
    ) {
      this.showError('Please select a PDF file.');
      input.value = '';
      this.selectedFile = null;
      return;
    }

    this.errorMessage = '';
    this.selectedFile = file;

    if (!this.documentName.trim()) {
      this.documentName = file.name.replace(/\.pdf$/i, '');
    }
  }

  uploadDocument(): void {
    if (
      !this.selectedSubject ||
      !this.selectedFile ||
      !this.documentName.trim() ||
      this.uploading
    ) {
      return;
    }

    this.uploading = true;
    this.errorMessage = '';
    this.successMessage = '';

    const subjectId = String(this.selectedSubject.id);
    const name = this.documentName.trim();

    this.api.uploadDocument(
      this.selectedFile,
      subjectId,
      name
    ).pipe(
      timeout(120000),
      finalize(() => {
        this.uploading = false;
        this.refresh();
      })
    ).subscribe({
      next: (response: any) => {
        console.log('Upload API response:', response);

        this.showUploadModal = false;
        this.selectedFile = null;
        this.documentName = '';

        this.showSuccess('Document uploaded successfully.');
        this.loadDocuments();
      },
      error: (error: any) => {
        console.error('Failed to upload document:', error);

        this.showError(
          this.errorDetail(error, 'Could not upload the PDF. Check the backend logs.')
        );
      }
    });
  }

  processDocument(document: DocumentItem): void {
    const id = this.idString(document.id);

    if (this.processingDocumentId !== null) {
      return;
    }

    this.processingDocumentId = id;
    this.errorMessage = '';
    this.successMessage = '';

    this.api.processDocument(document.id).pipe(
      timeout(120000),
      finalize(() => {
        this.processingDocumentId = null;
        this.loadDocuments();
        this.refresh();
      })
    ).subscribe({
      next: (response: any) => {
        console.log('Upload and processing response:', response);

        this.showUploadModal = false;
        this.selectedFile = null;
        this.documentName = '';

        this.showSuccess('Document uploaded and processed successfully.');
        this.loadDocuments();
        },
      error: (error: any) => {
        console.error('Failed to process document:', error);

        this.showError(
          this.errorDetail(error, 'Document processing failed. Check the backend logs.')
        );
      }
    });
  }

  deleteDocument(document: DocumentItem): void {
    const id = this.idString(document.id);

    if (this.deletingId !== null) {
      return;
    }

    if (!window.confirm(`Delete "${document.name}"?`)) {
      return;
    }

    this.deletingId = id;
    this.errorMessage = '';

    this.api.deleteDocument(document.id).pipe(
      timeout(15000),
      finalize(() => {
        this.deletingId = null;
        this.refresh();
      })
    ).subscribe({
      next: () => {
        this.documents = this.documents.filter(
          item => String(item.id) !== id
        );

        this.selectedDocumentIds = this.selectedDocumentIds.filter(
          itemId => itemId !== id
        );

        this.questionsSub?.unsubscribe();
        this.questions = [];
        this.showQuestionBank = false;
        this.showSuccess('Document deleted.');
      },
      error: (error: any) => {
        console.error('Failed to delete document:', error);

        this.showError(
          this.errorDetail(
            error,
            'Could not delete this document. Verify the backend deletion route.'
          )
        );
      }
    });
  }

  // ---------- Question filters ----------

  get allDocumentsSelected(): boolean {
    return this.documents.length > 0 &&
      this.documents.every(document =>
        this.selectedDocumentIds.includes(String(document.id))
      );
  }

  get selectedDocumentLabel(): string {
    if (this.selectedDocumentIds.length === 0) {
      return 'Select documents';
    }

    if (this.allDocumentsSelected) {
      return 'All documents';
    }

    return `${this.selectedDocumentIds.length} selected`;
  }

  get allTypesSelected(): boolean {
    return this.questionTypes.every(type =>
      this.selectedTypes.includes(type.value)
    );
  }

  get selectedTypeLabel(): string {
    if (this.selectedTypes.length === 0) {
      return 'Select question types';
    }

    if (this.allTypesSelected) {
      return 'All question types';
    }

    return this.questionTypes
      .filter(type => this.selectedTypes.includes(type.value))
      .map(type => type.label)
      .join(', ');
  }

  toggleAllDocuments(checked: boolean): void {
    this.selectedDocumentIds = checked
      ? this.documents.map(document => String(document.id))
      : [];
  }

  toggleDocument(id: string | number, checked: boolean): void {
    const value = String(id);

    if (checked && !this.selectedDocumentIds.includes(value)) {
      this.selectedDocumentIds = [...this.selectedDocumentIds, value];
    } else if (!checked) {
      this.selectedDocumentIds =
        this.selectedDocumentIds.filter(item => item !== value);
    }
  }

  toggleAllTypes(checked: boolean): void {
    this.selectedTypes = checked
      ? this.questionTypes.map(type => type.value)
      : [];
  }

  toggleType(type: string, checked: boolean): void {
    if (checked && !this.selectedTypes.includes(type)) {
      this.selectedTypes = [...this.selectedTypes, type];
    } else if (!checked) {
      this.selectedTypes = this.selectedTypes.filter(item => item !== type);
    }
  }

  // ---------- Questions and quiz ----------

  private questionCategory(
    rawType: string
  ): 'MCQ' | 'TRUE_FALSE' | null {
    const type = rawType.toUpperCase().replace(/[^A-Z]+/g, '_');

    if ([
      'MCQ',
      'MULTIPLE_CHOICE',
      'MULTIPLE_CHOICE_QUESTION'
    ].includes(type)) {
      return 'MCQ';
    }

    if (['TRUE_FALSE', 'TRUEFALSE', 'TF'].includes(type)) {
      return 'TRUE_FALSE';
    }

    return null;
  }

  openQuestionBank(): void {
    if (!this.selectedSubject) {
        return;
    }

    this.router.navigate([
        '/subjects',
        this.selectedSubject.id,
        'question-bank'
    ]);
    }

  loadQuestions(): void {
    if (!this.selectedSubject) {
      return;
    }

    if (
      this.selectedDocumentIds.length === 0 ||
      this.selectedTypes.length === 0
    ) {
      this.showError('Select at least one document and one question type.');
      return;
    }

    const selectedDocuments = this.documents.filter(document =>
      this.selectedDocumentIds.includes(String(document.id))
    );

    if (selectedDocuments.length === 0) {
      this.showError('No selected documents are available.');
      return;
    }

    this.questionsSub?.unsubscribe();

    this.loadingQuestions = true;
    this.showQuestionBank = true;
    this.questions = [];
    this.errorMessage = '';
    this.successMessage = '';

    const requests = selectedDocuments.map(document =>
      this.api.getDocumentQuestions(document.id).pipe(
        timeout(30000),
        catchError(error => {
          console.error(
            `Failed to load questions for ${document.name}:`,
            error
          );
          return of(null);
        })
      )
    );

    this.questionsSub = forkJoin(requests).pipe(
      finalize(() => {
        this.loadingQuestions = false;
        this.refresh();
      })
    ).subscribe({
      next: responses => {
        const allQuestions: QuestionItem[] = [];

        responses.forEach((response, docIndex) => {
          const sourceDocument = selectedDocuments[docIndex];
          const items = this.getArray(response, ['questions']);

          items.forEach((item: any, itemIndex: number) => {
            const questionText = this.firstValue(item, [
              'question',
              'question_text',
              'text',
              'content'
            ]);

            if (!questionText) {
              return;
            }

            const questionType = String(
              this.firstValue(item, [
                'question_type',
                'type',
                'questionType'
              ]) ?? 'MCQ'
            ).toUpperCase();

            const category = this.questionCategory(questionType);

            const rawAnswers = this.getArray(item, [
              'answers',
              'options',
              'choices'
            ]);

            let answers: AnswerItem[] = rawAnswers.map(
              (answer: any, index: number) => {
                if (typeof answer === 'string') {
                  return { text: answer, value: answer };
                }

                return {
                  ...answer,
                  text: this.firstValue(answer, [
                    'text',
                    'answer_text',
                    'label',
                    'option_text',
                    'value'
                  ]) ?? `Option ${index + 1}`
                };
              }
            );

            if (category === 'TRUE_FALSE' && answers.length === 0) {
              answers = [
                { text: 'True', value: 'True' },
                { text: 'False', value: 'False' }
              ];
            }

            const rawId = this.firstValue(item, ['id', 'question_id']);

            allQuestions.push({
              id: `${sourceDocument.id}:${rawId ?? itemIndex}`,
              question: String(questionText),
              question_type: questionType,
              answers,
              correct_answer: this.firstValue(item, [
                'correct_answer',
                'correctAnswer',
                'answer_key',
                'correct_option',
                'answer'
              ]),
              explanation: this.firstValue(item, [
                'explanation',
                'reason'
              ]),
              selectedAnswer: '',
              submitted: false
            });
          });
        });

        this.questions = allQuestions.filter(question => {
          const category = this.questionCategory(question.question_type);
          return category !== null && this.selectedTypes.includes(category);
        });

        if (responses.every(response => response === null)) {
          this.showError(
            'Could not load questions. Check the backend endpoint and logs.'
          );
        } else if (this.questions.length === 0) {
          this.showSuccess(
            'No matching questions were returned. Process the documents first.'
          );
        }
      },
      error: error => {
        console.error('Failed to load questions:', error);
        this.showError('Could not load questions. Please try again.');
      }
    });
  }
  
  generateQuestions(): void {
    if (this.generatingQuestions || this.loadingQuestions) {
      return;
    }

    if (this.selectedDocumentIds.length === 0) {
      this.showError('Select at least one document.');
      return;
    }

    if (this.selectedTypes.length === 0) {
      this.showError('Select at least one question type.');
      return;
    }

    if (
      !Number.isInteger(this.numQuestions) ||
      this.numQuestions < 1 ||
      this.numQuestions > 50
    ) {
      this.showError('Choose between 1 and 50 questions per type, per document.');
      return;
    }

    const selectedDocuments = this.documents.filter(document =>
      this.selectedDocumentIds.includes(String(document.id))
    );

    const requests = selectedDocuments.flatMap(document =>
      this.selectedTypes.map(type => {
        if (type === 'MCQ') {
          return this.api.generateMCQs(
            document.id,
            this.numQuestions
          );
        }

        return this.api.generateTrueFalse(
          document.id,
          this.numQuestions
        );
      })
    );

    this.generatingQuestions = true;
    this.errorMessage = '';
    this.successMessage = '';

    forkJoin(requests).pipe(
      timeout(180000),
      finalize(() => {
        this.generatingQuestions = false;
        this.refresh();
      })
    ).subscribe({
      next: () => {
        this.showSuccess('Questions generated successfully. Refreshing question bank...');
        this.loadQuestions();
      },
      error: error => {
        console.error('Question generation failed:', error);

        this.showError(
          this.errorDetail(
            error,
            'Question generation failed. Check the FastAPI terminal for details.'
          )
        );
      }
    });
  }

  answerValue(answer: AnswerItem): string {
    return String(
      this.firstValue(answer, [
        'option_code',
        'code',
        'value',
        'id',
        'text'
      ]) ?? ''
    );
  }

  answerText(answer: AnswerItem): string {
    return String(
      this.firstValue(answer, [
        'text',
        'answer_text',
        'label',
        'option_text',
        'value'
      ]) ?? ''
    );
  }

  selectAnswer(question: QuestionItem, answer: AnswerItem): void {
    if (!question.submitted) {
      question.selectedAnswer = this.answerValue(answer);
    }
  }

  private normalizedAnswer(value: any): string {
    if (value === null || value === undefined) {
      return '';
    }

    return String(value).trim().toLowerCase();
  }

  private isFlagged(value: any): boolean {
    return value === true ||
      value === 1 ||
      ['true', '1', 'yes'].includes(this.normalizedAnswer(value));
  }

  private findCorrectOption(
    question: QuestionItem
  ): AnswerItem | undefined {
    const flagged = question.answers.find(answer =>
      this.isFlagged(
        this.firstValue(answer, ['is_correct', 'isCorrect', 'correct'])
      )
    );

    if (flagged) {
      return flagged;
    }

    const correct = this.normalizedAnswer(question.correct_answer);

    if (!correct) {
      return undefined;
    }

    const byCode = question.answers.find(answer =>
      ['option_code', 'code', 'id', 'value'].some(
        key => this.normalizedAnswer(answer[key]) === correct
      )
    );

    if (byCode) {
      return byCode;
    }

    const byText = question.answers.find(answer =>
      this.normalizedAnswer(this.answerText(answer)) === correct
    );

    if (byText) {
      return byText;
    }

    if (/^[a-z]$/.test(correct)) {
      return question.answers[correct.charCodeAt(0) - 97];
    }

    return undefined;
  }

  isCorrect(question: QuestionItem, answer: AnswerItem): boolean {
    const correctOption = this.findCorrectOption(question);
    return correctOption !== undefined && correctOption === answer;
  }

  isQuestionCorrect(question: QuestionItem): boolean {
    if (!question.selectedAnswer) {
      return false;
    }

    const correctOption = this.findCorrectOption(question);

    if (!correctOption) {
      return false;
    }

    return this.normalizedAnswer(question.selectedAnswer) ===
      this.normalizedAnswer(this.answerValue(correctOption));
  }

  submitAnswer(question: QuestionItem): void {
    if (!question.selectedAnswer || question.submitted) {
      return;
    }

    question.submitted = true;
  }

  resetQuestion(question: QuestionItem): void {
    question.selectedAnswer = '';
    question.submitted = false;
  }

  resetQuiz(): void {
    this.questions = this.questions.map(question => ({
      ...question,
      selectedAnswer: '',
      submitted: false
    }));
  }

  // ---------- TrackBy helpers ----------

  trackSubject(_: number, subject: SubjectItem): string {
    return String(subject.id);
  }

  trackDocument(_: number, document: DocumentItem): string {
    return String(document.id);
  }

  trackQuestion(_: number, question: QuestionItem): string {
    return String(question.id);
  }
}
