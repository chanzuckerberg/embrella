'use client';

import { Prism as SyntaxHighlighterBase } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

// Workaround for TypeScript compatibility issue with react-syntax-highlighter
const SyntaxHighlighter = SyntaxHighlighterBase as typeof SyntaxHighlighterBase & React.FC;

export const EDITOR_BG = '#0d1117';

export function YamlHighlight({ yaml }: { yaml: string }) {
  return (
    <SyntaxHighlighter
      language="yaml"
      style={vscDarkPlus}
      showLineNumbers
      wrapLines={false}
      customStyle={{
        margin: 0,
        minHeight: '100%',
        background: EDITOR_BG,
        fontSize: '0.8rem',
        lineHeight: 1.7,
      }}
    >
      {yaml}
    </SyntaxHighlighter>
  );
}
