export function detectDocumentationSystemFromUrl(url: string): string {
  const lower = url.toLowerCase();
  if (url.includes('atlassian.net') || lower.includes('confluence')) {
    return 'Confluence';
  }
  if (url.includes('benchling.com')) {
    return 'Benchling';
  }
  if (url.includes('docs.google.com')) {
    return 'Google Docs';
  }
  if (url.includes('drive.google.com')) {
    return 'Google Drive';
  }
  return 'Other';
}
