'use client';

import { DJANGO_URL, POST_API } from '@app/common/constants/api';
import { patchResource } from '@app/common/queries/fetchResource';
import { LabelChip, LabelData } from '@app/components/GridsView/components/LabelEditor/LabelChip';
import { useScreeningLabels } from '@app/components/Screening/context/ScreeningLabelsContext';
import { ScreeningGridData } from '@app/components/Screening/types';

interface AllLabelsCellProps {
  row: ScreeningGridData;
}

export const AllLabelsCell = ({ row }: AllLabelsCellProps) => {
  const { getLabels, setLabels } = useScreeningLabels();
  const labels = getLabels(row.grid.id, row.labels);

  const handleSave = async (next: LabelData[]) => {
    setLabels(row.grid.id, next);
    const url = `${DJANGO_URL}${POST_API.UPDATE_GRID_LABELS.replace('grid_id', String(row.grid.id))}`;
    try {
      const res = await patchResource(url, { label_ids: next.map((l) => l.id) });
      if (!res.ok) {
        console.error('Failed to update labels:', res.status, await res.text());
      }
    } catch (e) {
      console.error('Failed to update labels:', e);
    }
  };

  return <LabelChip gridId={row.grid.id} labels={labels} controlledLabels={labels} onSave={handleSave} />;
};
