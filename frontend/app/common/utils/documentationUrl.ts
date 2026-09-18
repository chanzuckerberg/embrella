export enum DocSystem {
  Confluence = 'Confluence',
  Benchling = 'Benchling',
  GoogleDocs = 'Google Docs',
  GoogleDrive = 'Google Drive',
  Other = 'Other',
}

// Hostname suffix -> system. Matched against the parsed hostname only
const HOST_TO_SYSTEM: [string, DocSystem][] = [
  ['atlassian.net', DocSystem.Confluence],
  ['benchling.com', DocSystem.Benchling],
  ['docs.google.com', DocSystem.GoogleDocs],
  ['drive.google.com', DocSystem.GoogleDrive],
];

// Self-hosted Confluence has no fixed domain; fall back to a hostname keyword.
const CONFLUENCE_HOST_KEYWORD = 'confluence';

function hostMatches(hostname: string, domain: string): boolean {
  return hostname === domain || hostname.endsWith(`.${domain}`);
}

export function detectDocumentationSystemFromUrl(url: string): DocSystem {
  let hostname: string;
  try {
    hostname = new URL(url).hostname.toLowerCase();
  } catch {
    return DocSystem.Other;
  }

  const match = HOST_TO_SYSTEM.find(([domain]) => hostMatches(hostname, domain));
  if (match) {
    return match[1];
  }

  if (hostname.includes(CONFLUENCE_HOST_KEYWORD)) {
    return DocSystem.Confluence;
  }

  return DocSystem.Other;
}
