import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    redirectTo: 'subjects',
    pathMatch: 'full'
  },
  {
    path: 'subjects',
    loadComponent: () =>
      import('./documents/documents').then(
        m => m.DocumentsComponent
      )
  },
  {
    path: 'subjects/:subjectId/question-bank',
    loadComponent: () =>
      import('./question-bank/question-bank').then(
        m => m.QuestionBankComponent
      )
  },
  {
    path: 'subjects/:subjectId/quiz',
    loadComponent: () =>
      import('./quiz/quiz').then(
        m => m.QuizComponent
      )
  },
  {
    path: '**',
    redirectTo: 'subjects'
  }
];