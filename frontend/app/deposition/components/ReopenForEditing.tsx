import { Button } from '@czi-sds/components';

import { ConfirmDialog } from '@app/common/components/Forms/ConfirmDialog';
import type { Dataset } from '../types';
import type { usePreparationEditing } from '../hooks/usePreparationEditing';
import { ReadOnlyNotice } from './ReadOnlyNotice';

export function ReopenForEditing({
  editing,
  dataset,
}: {
  editing: ReturnType<typeof usePreparationEditing>;
  dataset: Dataset;
}) {
  return (
    <>
      {editing.canReopen && (
        <Button
          sdsType="secondary"
          sdsStyle="solid"
          onClick={editing.requestEdit}
          sx={{ mb: '16px', alignSelf: 'flex-start' }}
        >
          Edit metadata
        </Button>
      )}
      {editing.readOnly && !editing.canReopen && <ReadOnlyNotice dataset={dataset} />}
      <ConfirmDialog
        open={editing.dialogOpen}
        onClose={editing.cancelEdit}
        onConfirm={editing.confirmEdit}
        title="Edit dataset metadata?"
        heading="Run preparation again after editing"
        body="Your metadata is kept, but preparation and validation results are cleared. Return to Finalize & Submit to run them again before upload."
        intent="warning"
        confirmText="Edit metadata"
        submittingText="Reopening…"
        cancelText="Keep read-only"
        isSubmitting={editing.preparing}
        error={editing.error?.message}
      />
    </>
  );
}
