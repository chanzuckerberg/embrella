import { COLS } from '../constants';

export function ColGroup() {
  return (
    <colgroup>
      {COLS.map((c) => (
        <col key={c.key} style={{ width: c.width }} />
      ))}
    </colgroup>
  );
}
