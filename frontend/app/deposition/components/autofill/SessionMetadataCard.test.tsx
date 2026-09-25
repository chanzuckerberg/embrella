import '@testing-library/jest-dom';
import { useState } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { SessionMetadataCard, type SessionMeta } from './SessionMetadataCard';

function makeSession(over: Partial<SessionMeta> = {}): SessionMeta {
  return {
    key: 's1',
    id: 1,
    sessionName: '25nov13a',
    aretomoRun: 'run001',
    tiltseries: {},
    tomograms: {
      denoised: { flavor: 'denoised' },
      filtered: { flavor: 'filtered' },
    },
    lastAutofillAt: null,
    ...over,
  } as SessionMeta;
}

const noop = () => undefined;

it('keeps restored manual work unlocked after clearing its last value', async () => {
  const onAutoFill = jest.fn();
  function Harness() {
    const [manualEntered, setManualEntered] = useState(false);
    const [session, setSession] = useState(makeSession({ tiltseries: { pixel_spacing: 1.5 } }));
    return (
      <>
        <button onClick={() => setSession(makeSession())}>Clear saved value</button>
        <SessionMetadataCard
          session={session}
          readOnly={false}
          autoFilling={false}
          onAutoFill={onAutoFill}
          onFieldChange={noop}
          manualEntered={manualEntered}
          onManualEntry={() => setManualEntered(true)}
        />
      </>
    );
  }
  render(<Harness />);
  await userEvent.click(screen.getByRole('button', { name: 'Clear saved value' }));
  expect(screen.queryByText(/start with auto-fill/i)).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: /^auto-fill$/i }));
  expect(onAutoFill).not.toHaveBeenCalled();
  expect(screen.getByText(/auto-fill this session\?/i)).toBeInTheDocument();
});

it('keeps a saved filtered visualization choice unlocked and confirms replacement', async () => {
  const onAutoFill = jest.fn();
  renderCard({
    onAutoFill,
    session: makeSession({
      tomograms: {
        denoised: { flavor: 'denoised', is_visualization_default: false },
        filtered: { flavor: 'filtered', is_visualization_default: true },
      },
    }),
  });
  expect(screen.queryByText(/start with auto-fill/i)).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: /^auto-fill$/i }));
  expect(onAutoFill).not.toHaveBeenCalled();
  expect(screen.getByText(/auto-fill this session\?/i)).toBeInTheDocument();
});

function renderCard(props: Partial<React.ComponentProps<typeof SessionMetadataCard>> = {}) {
  return render(
    <SessionMetadataCard
      session={makeSession()}
      readOnly={false}
      autoFilling={false}
      onAutoFill={noop}
      onFieldChange={noop}
      manualEntered={false}
      onManualEntry={noop}
      {...props}
    />
  );
}

it('gates a session that has not been auto-filled behind the Start-with-auto-fill card', () => {
  renderCard();
  expect(screen.getByText(/start with auto-fill/i)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /^auto-fill$/i })).toBeInTheDocument();
});

it('treats applied/seeded defaults as not-edited, so a fresh session still gates', () => {
  renderCard({
    session: makeSession({
      tiltseries: { tilt_axis: -96, tilting_scheme: 'dose-symmetric' },
      tomograms: {
        denoised: {
          flavor: 'denoised',
          reconstruction_method: 'WBP',
          ctf_corrected: true,
          is_visualization_default: true,
        },
        filtered: {
          flavor: 'filtered',
          reconstruction_method: 'WBP',
          ctf_corrected: true,
          is_visualization_default: false,
        },
      },
    }),
  });
  expect(screen.getByText(/start with auto-fill/i)).toBeInTheDocument();
});

it('offers no manual escape until auto-fill has actually failed', () => {
  renderCard();
  expect(screen.queryByRole('button', { name: /fill manually/i })).not.toBeInTheDocument();
});

it('runs auto-fill straight from the gate button', async () => {
  const onAutoFill = jest.fn();
  renderCard({ onAutoFill });
  await userEvent.click(screen.getByRole('button', { name: /^auto-fill$/i }));
  expect(onAutoFill).toHaveBeenCalledTimes(1);
});

it('does not gate a session that already has saved edits, e.g. after a reload', () => {
  // pixel_spacing has no default, so a value means real saved edits, not just applied defaults.
  renderCard({ session: makeSession({ tiltseries: { pixel_spacing: 1.5 } }) });
  expect(screen.queryByText(/start with auto-fill/i)).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: /^auto-fill$/i })).toBeInTheDocument();
});

it('confirms before auto-fill overwrites saved edits (from the header, gate is already down)', async () => {
  const onAutoFill = jest.fn();
  renderCard({ session: makeSession({ tiltseries: { pixel_spacing: 1.5 } }), onAutoFill });
  await userEvent.click(screen.getByRole('button', { name: /^auto-fill$/i }));
  expect(onAutoFill).not.toHaveBeenCalled(); // routed through the confirm dialog, not fired directly
  expect(screen.getByText(/auto-fill this session\?/i)).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: /replace values/i }));
  expect(onAutoFill).toHaveBeenCalledTimes(1);
});

it('recognizes saved tomogram-only edits (not just tilt-series) and keeps the form open', () => {
  // voxel_spacing has no default; a value on either flavor means real saved tomogram edits.
  renderCard({
    session: makeSession({
      tomograms: { denoised: { flavor: 'denoised', voxel_spacing: 10 }, filtered: { flavor: 'filtered' } },
    }),
  });
  expect(screen.queryByText(/start with auto-fill/i)).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: /^auto-fill$/i })).toBeInTheDocument();
});

it('drops the gate and shows re-run once the session is auto-filled', () => {
  renderCard({ session: makeSession({ lastAutofillAt: '2026-09-24T10:00:00Z' }) });
  expect(screen.queryByText(/start with auto-fill/i)).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: /re-run auto-fill/i })).toBeInTheDocument();
});

it('on failure offers both a retry and a manual escape', () => {
  renderCard({ autoFillError: 'No .mdoc found' });
  expect(screen.getByText(/no \.mdoc found/i)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /fill manually/i })).toBeInTheDocument();
});

it('Fill manually delegates the choice to the parent', async () => {
  const onManualEntry = jest.fn();
  renderCard({ autoFillError: 'Cluster unavailable', onManualEntry });
  await userEvent.click(screen.getByRole('button', { name: /fill manually/i }));
  expect(onManualEntry).toHaveBeenCalledTimes(1);
});

it('once manual entry is chosen the gate stays down and a retry remains available', () => {
  // No lastAutofillAt, but the parent recorded a manual-entry choice for this session.
  renderCard({ manualEntered: true });
  expect(screen.queryByText(/start with auto-fill/i)).not.toBeInTheDocument();
  // #1233: a failed-then-manual session still gets an auto-fill action (not just "re-run").
  expect(screen.getByRole('button', { name: /^auto-fill$/i })).toBeInTheDocument();
});

it('does not gate when there is no AreTomo run (shows the Sources hint instead)', () => {
  renderCard({ session: makeSession({ aretomoRun: '' }) });
  expect(screen.queryByText(/start with auto-fill/i)).not.toBeInTheDocument();
  expect(screen.getByText(/pick an aretomo run/i)).toBeInTheDocument();
});

it('does not gate in read-only mode', () => {
  renderCard({ readOnly: true });
  expect(screen.queryByText(/start with auto-fill/i)).not.toBeInTheDocument();
});
