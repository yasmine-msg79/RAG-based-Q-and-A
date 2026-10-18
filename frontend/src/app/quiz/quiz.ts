import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { ApiService } from '../api.service';

interface QuizOption {
  [key: string]: any;
}

interface QuizQuestion {
  id: string | number;
  question: string;
  question_type: string;
  answers: QuizOption[];
  correct_answer?: any;
  explanation?: string;
  document_id?: string | number;

  selectedAnswer: string | null;
}

@Component({
  selector: 'app-quiz',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './quiz.html',
  styleUrl: './quiz.css'
})
export class QuizComponent implements OnInit {
  subjectId = '';
  documentIds: string[] = [];
  selectedTypes: string[] = [];

  questions: QuizQuestion[] = [];


  loading = true;
  submitted = false;
  errorMessage = '';

  constructor(
    private readonly api: ApiService,
    private readonly route: ActivatedRoute,
    private readonly router: Router,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.subjectId =
      this.route.snapshot.paramMap.get('subjectId') ?? '';

    const params = this.route.snapshot.queryParamMap;

    this.documentIds = (params.get('documents') ?? '')
      .split(',')
      .filter(Boolean);

    this.selectedTypes = (params.get('types') ?? '')
      .split(',')
      .filter(Boolean)
      .map(type => this.normalizeType(type));

    if (
        !this.subjectId ||
        this.documentIds.length === 0 ||
        this.selectedTypes.length === 0
        ) {
        this.errorMessage =
            'Quiz filters are missing. Return to the Question Bank and start again.';
        this.loading = false;
        this.cdr.detectChanges();
        return;
    }

    this.loadQuestions();
  }

  private normalizeType(value: any): string {
    const type = String(value ?? '')
      .toUpperCase()
      .replace(/[- ]/g, '_');

    if (type === 'TRUEFALSE' || type === 'TRUE_FALSE') {
      return 'TRUE_FALSE';
    }

    if (
      type === 'MULTIPLE_CHOICE' ||
      type === 'MULTIPLECHOICE'
    ) {
      return 'MCQ';
    }

    return type;
  }

  private getArray(response: any): any[] {
    if (Array.isArray(response)) {
      return response;
    }

    for (const key of ['questions', 'data', 'items', 'results']) {
      if (Array.isArray(response?.[key])) {
        return response[key];
      }
    }

    return [];
  }

  private loadQuestions(): void {
    this.loading = true;
    this.errorMessage = '';
    this.cdr.detectChanges();

    const requests = this.documentIds.map(documentId =>
      this.api.getDocumentQuestions(documentId).pipe(
        catchError(() => of(null))
      )
    );

    forkJoin(requests).subscribe({
      next: responses => {
        const loaded: QuizQuestion[] = [];

        responses.forEach((response, index) => {
          if (response === null) {
            return;
          }

          const documentId = this.documentIds[index];
          const items = this.getArray(response);

          items.forEach((item: any) => {
            const type = this.normalizeType(item.question_type);

            if (!this.selectedTypes.includes(type)) {
              return;
            }

            loaded.push({
                ...item,
                question: item.question ?? item.header ?? item.question_text ?? '',
                question_type: type,
                document_id: item.document_id ?? documentId,
                answers: Array.isArray(item.answers)
                    ? item.answers.map((answer: any) => ({
                        ...answer,
                        text: answer.text ?? answer.header ?? answer.option ?? answer.value ?? '',
                        value: answer.value ?? answer.id ?? answer.code
                    }))
                    : [],
                selectedAnswer: null
            });
          });
        });

        // Prevent duplicate records when the same question appears twice.
        const seen = new Set<string>();

        this.questions = loaded.filter(question => {
          const key = `${question.document_id}:${question.id}`;

          if (seen.has(key)) {
            return false;
          }

          seen.add(key);
          return true;
        });

        this.loading = false;
        this.cdr.detectChanges();

        if (this.questions.length === 0) {
          this.errorMessage =
            'No saved questions match your selections. Return to the Question Bank to generate questions or change the filters.';
        }
      },
      error: () => {
        this.loading = false;
        this.cdr.detectChanges();
        this.errorMessage = 'Could not load the saved questions.';
      }
    });
  }

  get answeredCount(): number {
    return this.questions.filter(
      question => question.selectedAnswer !== null
    ).length;
  }

  get score(): number {
    if (!this.submitted || this.questions.length === 0) {
      return 0;
    }

    return this.questions.filter(question =>
      this.isCorrect(question)
    ).length;
  }

  get percentage(): number {
    return this.questions.length === 0
      ? 0
      : Math.round((this.score / this.questions.length) * 100);
  }

  selectAnswer(question: QuizQuestion, value: string): void {
    if (this.submitted) {
      return;
    }

    question.selectedAnswer = value;
  }

  submitQuiz(): void {
    if (this.submitted || this.questions.length === 0) {
      return;
    }

    this.submitted = true;

    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  answerValue(answer: any): string {
    if (typeof answer === 'string' || typeof answer === 'number') {
      return String(answer);
    }

    const value =
      answer?.id ??
      answer?.value ??
      answer?.option ??
      answer?.text ??
      answer?.answer;

    return value == null ? '' : String(value);
  }

  answerText(answer: any): string {
    if (typeof answer === 'string' || typeof answer === 'number') {
        return String(answer);
    }

    return String(
        answer?.text ??
        answer?.header ??
        answer?.option ??
        answer?.value ??
        answer?.answer ??
        ''
    );
    }

  private correctValue(question: QuizQuestion): string {
    const raw = question.correct_answer;

    if (raw && typeof raw === 'object') {
        return this.answerValue(raw);
    }

    if (typeof raw === 'boolean') {
        return String(raw);
    }

    if (raw != null && raw !== '') {
        return String(raw);
    }

    const correctOption = question.answers?.find(
        (answer: any) => answer.is_correct === true
    );

    return correctOption ? this.answerValue(correctOption) : '';
    }
  correctAnswerText(question: QuizQuestion): string {
    const correct = question.correct_answer;

    if (correct === true) return 'True';
    if (correct === false) return 'False';

    if (correct && typeof correct === 'object') {
        return this.answerText(correct);
    }

    const correctOption = question.answers?.find(
        (answer: any) => answer.is_correct === true
    );

    if (correctOption) {
        return this.answerText(correctOption);
    }

    if (correct != null && correct !== '') {
        const matchingOption = question.answers?.find(
        answer => this.answerValue(answer) === String(correct)
        );

        return matchingOption
        ? this.answerText(matchingOption)
        : String(correct);
    }

    return 'Unavailable';
    }
  isCorrect(question: QuizQuestion): boolean {
    if (!this.submitted || question.selectedAnswer === null) {
      return false;
    }

    const selected = question.selectedAnswer.trim().toLowerCase();
    const correct = this.correctValue(question).trim().toLowerCase();

    return selected !== '' && selected === correct;
  }

  isCorrectOption(question: QuizQuestion, answer: any): boolean {
    if (!this.submitted) {
      return false;
    }

    const correct = this.correctValue(question).trim().toLowerCase();
    const value = this.answerValue(answer).trim().toLowerCase();

    return correct !== '' && value === correct;
  }

  questionTypeLabel(type: string): string {
    return this.normalizeType(type) === 'MCQ'
      ? 'Multiple choice'
      : 'True / False';
  }

  backToQuestionBank(): void {
    this.router.navigate([
      '/subjects',
      this.subjectId,
      'question-bank'
    ]);
  }

  backToSubjects(): void {
    this.router.navigate(['/subjects', this.subjectId]);
    }
}