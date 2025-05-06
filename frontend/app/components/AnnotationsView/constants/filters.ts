import { AnnotationFilterConfig, AnnotationFilterId } from '../types';

export const ANNOTATION_FILTER_CONFIGS: AnnotationFilterConfig[][] = [
  [
    {
      filterCategory: 'project',
      filterId: AnnotationFilterId.PROJECT,
      label: 'Project',
    },
    {
      filterCategory: 'sample',
      filterId: AnnotationFilterId.SAMPLE,
      label: 'Sample',
    },
    {
      filterCategory: 'user',
      filterId: AnnotationFilterId.USER,
      label: 'User',
    },
    {
      filterCategory: 'date',
      filterId: AnnotationFilterId.DATE,
      label: 'Date',
    },
    {
      filterCategory: 'screeningSession',
      filterId: AnnotationFilterId.SCREENING_SESSION,
      label: 'Screening Session',
    },
    {
      filterCategory: 'msiSession',
      filterId: AnnotationFilterId.MSI_SESSION,
      label: 'MSI Session',
    },
    {
      filterCategory: 'procPlan',
      filterId: AnnotationFilterId.PROC_PLAN,
      label: 'Proc Plan',
    },
  ],
];
