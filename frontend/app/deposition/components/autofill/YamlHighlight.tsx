'use client';

import { Box } from '@mui/material';

const C = {
  bg: '#0d1117',
  gutter: '#6e7681',
  text: '#c9d1d9',
  section: '#d2a8ff', // top-level keys (acquisition:, paths:, …)
  key: '#79c0ff', // nested keys
  num: '#79c0ff',
  str: '#a5d6ff',
  comment: '#d29922', // # confirm / # required / # override
};

const KEY_RE = /^(\s*)([A-Za-z0-9_.\-/]+)(:)(.*)$/;

function Value({ raw }: { raw: string }) {
  if (raw.trim() === '') return null;
  const lead = raw.slice(0, raw.length - raw.trimStart().length);
  const body = raw.trimStart();
  const isNum = /^-?\d+(\.\d+)?$/.test(body);
  return (
    <>
      {lead}
      <span style={{ color: isNum ? C.num : C.str }}>{body}</span>
    </>
  );
}

function Line({ text }: { text: string }) {
  const trimmed = text.trimStart();
  if (trimmed.startsWith('#')) return <span style={{ color: C.comment }}>{text}</span>;

  // Split a trailing "  # comment" off the code part.
  let code = text;
  let comment = '';
  const ci = text.indexOf(' #');
  if (ci >= 0) {
    code = text.slice(0, ci);
    comment = text.slice(ci);
  }

  const m = KEY_RE.exec(code);
  if (m) {
    const [, indent, key, colon, rest] = m;
    const keyColor = indent === '' ? C.section : C.key;
    return (
      <>
        {indent}
        <span style={{ color: keyColor }}>{key}</span>
        <span style={{ color: C.text }}>{colon}</span>
        <Value raw={rest} />
        {comment && <span style={{ color: C.comment }}>{comment}</span>}
      </>
    );
  }

  return (
    <>
      <span style={{ color: C.text }}>{code}</span>
      {comment && <span style={{ color: C.comment }}>{comment}</span>}
    </>
  );
}

export function YamlHighlight({ yaml }: { yaml: string }) {
  const lines = yaml.split('\n');
  const width = String(lines.length).length;
  return (
    <Box
      component="pre"
      sx={{
        m: 0,
        p: 2,
        bgcolor: C.bg,
        color: C.text,
        fontSize: '0.8rem',
        lineHeight: 1.7,
        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
        minHeight: '100%',
        whiteSpace: 'pre',
      }}
    >
      {lines.map((line, i) => (
        <div key={i} style={{ display: 'flex' }}>
          <span
            style={{ color: C.gutter, userSelect: 'none', textAlign: 'right', width: `${width}ch`, marginRight: 16 }}
          >
            {i + 1}
          </span>
          <span style={{ flex: 1 }}>
            <Line text={line} />
          </span>
        </div>
      ))}
    </Box>
  );
}
