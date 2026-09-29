'use client';

import { useMemo, useState } from 'react';
import { Callout, Icon } from '@czi-sds/components';
import {
  alpha,
  Box,
  Divider,
  FormControl,
  MenuItem,
  Radio,
  Select,
  Snackbar,
  Tab,
  Tabs,
  TextField,
  Typography,
} from '@mui/material';

import { BaseFormDialog } from '@app/common/components/Forms/BaseFormDialog';
import { useSubmissions } from '../../hooks/useSubmissions';
import type { Deposition } from '../../types';
import { DatasetChoiceField } from './reservation/DatasetChoiceField';
import { useReserve } from './reservation/useReserve';
import {
  OPTIONS,
  datasetLabel,
  depositionLabel,
  type DatasetChoice,
  type ExistingTab,
  type Mode,
} from './reservation/types';

function OptionCards({ mode, onSelect }: { mode: Mode; onSelect: (mode: Mode) => void }) {
  return (
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(3, 1fr)' }, gap: 4 }}>
      {OPTIONS.map((opt) => {
        const selected = mode === opt.mode;
        return (
          <Box
            key={opt.mode}
            role="button"
            tabIndex={0}
            onClick={() => onSelect(opt.mode)}
            onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onSelect(opt.mode)}
            sx={{
              p: 2,
              borderRadius: 2,
              border: '2px solid',
              borderColor: selected ? 'primary.main' : 'divider',
              bgcolor: selected ? (theme) => alpha(theme.palette.primary.main, 0.06) : 'background.paper',
              cursor: 'pointer',
              transition: 'border-color 120ms, background-color 120ms',
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, pt: 4, pb: 3 }}>
              <Radio
                checked={selected}
                size="small"
                sx={{
                  p: 0,
                  mt: -6,
                  flexShrink: 0,
                  color: 'action.disabled',
                  '&.Mui-checked': { color: 'primary.main' },
                }}
              />
              <Box>
                <Typography variant="body2" sx={{ fontWeight: 700, color: selected ? 'primary.main' : 'text.primary' }}>
                  {opt.label}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  {opt.desc}
                </Typography>
              </Box>
            </Box>
          </Box>
        );
      })}
    </Box>
  );
}

function ExistingDepositionPicker({
  tab,
  onTabChange,
  depositions,
  depositionId,
  onDepositionIdChange,
  manualId,
  onManualIdChange,
}: {
  tab: ExistingTab;
  onTabChange: (tab: ExistingTab) => void;
  depositions: Deposition[];
  depositionId: string;
  onDepositionIdChange: (id: string) => void;
  manualId: string;
  onManualIdChange: (id: string) => void;
}) {
  return (
    <>
      <Tabs
        value={tab}
        onChange={(_, v: ExistingTab) => onTabChange(v)}
        sx={{ mb: 2.5, borderBottom: 1, borderColor: 'divider' }}
      >
        <Tab value="pick" label="Pick from your depositions" sx={{ textTransform: 'none', fontWeight: 600 }} />
        <Tab value="manual" label="Enter ID manually" sx={{ textTransform: 'none', fontWeight: 600 }} />
      </Tabs>

      {tab === 'pick' ? (
        <Box>
          <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.75 }}>
            Select deposition ID
          </Typography>
          <FormControl fullWidth size="small">
            <Select displayEmpty value={depositionId} onChange={(e) => onDepositionIdChange(String(e.target.value))}>
              <MenuItem value="" disabled>
                Select a deposition…
              </MenuItem>
              {depositions.map((d) => (
                <MenuItem key={d.id} value={String(d.id)}>
                  {depositionLabel(d.deposition_id)} - {d.title || '(untitled)'}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
      ) : (
        <Box>
          <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.75 }}>
            Enter deposition ID
          </Typography>
          <TextField
            fullWidth
            size="small"
            placeholder="Deposition ID"
            value={manualId}
            onChange={(e) => onManualIdChange(e.target.value)}
          />
          <Box sx={{ mt: 1.5 }}>
            <Callout
              intent="notice"
              sdsStyle="persistent"
              body="Manual ID lookup is coming soon - pick from your depositions for now."
            />
          </Box>
        </Box>
      )}

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 1 }}>
        <Icon sdsIcon="InfoCircle" sdsSize="s" color="gray" />
        <Typography variant="caption" color="text.secondary">
          Live preview via lambda lookup
        </Typography>
      </Box>

      <Divider sx={{ my: 2.5 }} />
    </>
  );
}

export function ReservationModal({
  open,
  onClose,
  initialMode = 'new',
  lockedDeposition = null,
}: {
  open: boolean;
  onClose: () => void;
  initialMode?: Mode;
  lockedDeposition?: Deposition | null;
}) {
  const { data } = useSubmissions();
  const depositions = useMemo(() => data?.submissions ?? [], [data]);

  const [mode, setMode] = useState<Mode>(initialMode);
  const [tab, setTab] = useState<ExistingTab>('pick');
  const [depositionId, setDepositionId] = useState<string>(lockedDeposition ? String(lockedDeposition.id) : '');
  const [manualId, setManualId] = useState('');
  const [datasetChoice, setDatasetChoice] = useState<DatasetChoice>('new');
  const [existingDatasetId, setExistingDatasetId] = useState<string>('');
  const [notice, setNotice] = useState(false);

  const selectedDeposition = useMemo(
    () => depositions.find((d) => String(d.id) === depositionId) ?? null,
    [depositions, depositionId]
  );
  const datasetsInSelected = selectedDeposition?.datasets ?? [];
  const allDatasets = useMemo(() => depositions.flatMap((d) => d.datasets ?? []), [depositions]);

  const reserve = useReserve(onClose);

  const isAddDataset = lockedDeposition != null;

  const canContinue = (() => {
    if (mode === 'new') return true;
    if (mode === 'reuse_dataset') return existingDatasetId !== '';
    if (tab === 'manual') return false;
    if (depositionId === '') return false;
    return datasetChoice === 'new' || existingDatasetId !== '';
  })();

  const subtitle = isAddDataset ? 'Add dataset' : 'New submission';
  const title = isAddDataset
    ? `Add a dataset to ${depositionLabel(lockedDeposition?.deposition_id)}`
    : 'Reserve or select IDs';

  const willReserve = mode === 'new' || (mode === 'existing_deposition' && datasetChoice === 'new');

  const handleContinue = () => {
    if (willReserve) {
      setNotice(true);
      return;
    }
    reserve.mutate({ mode, datasetChoice, depositionId, existingDatasetId });
  };

  return (
    <>
      <BaseFormDialog
        open={open}
        onClose={onClose}
        sdsSize={isAddDataset ? 'xs' : 's'}
        subtitle={subtitle}
        title={title}
        saveButtonText="Continue"
        isSubmitting={reserve.isPending}
        disabled={!canContinue}
        onSave={handleContinue}
      >
        {!isAddDataset && <OptionCards mode={mode} onSelect={setMode} />}

        {mode === 'existing_deposition' && (
          <Box>
            {!isAddDataset && (
              <ExistingDepositionPicker
                tab={tab}
                onTabChange={setTab}
                depositions={depositions}
                depositionId={depositionId}
                onDepositionIdChange={setDepositionId}
                manualId={manualId}
                onManualIdChange={setManualId}
              />
            )}
            <DatasetChoiceField
              choice={datasetChoice}
              onChoiceChange={setDatasetChoice}
              existingDatasetId={existingDatasetId}
              onExistingDatasetIdChange={setExistingDatasetId}
              datasets={datasetsInSelected}
            />
          </Box>
        )}

        {mode === 'reuse_dataset' && (
          <Box>
            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.75, mt: 5 }}>
              Select dataset
            </Typography>
            <FormControl fullWidth size="small">
              <Select
                displayEmpty
                value={existingDatasetId}
                onChange={(e) => setExistingDatasetId(String(e.target.value))}
              >
                <MenuItem value="" disabled>
                  Select a dataset…
                </MenuItem>
                {allDatasets.map((ds) => (
                  <MenuItem key={ds.id} value={String(ds.id)}>
                    {datasetLabel(ds.dataset_id)} - {ds.title || '(untitled)'}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
        )}

        {reserve.isError && (
          <Callout intent="negative" sdsStyle="persistent" body="Could not reserve IDs. Please try again." />
        )}
      </BaseFormDialog>
      <Snackbar
        open={notice}
        autoHideDuration={3000}
        onClose={() => setNotice(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
        message="Backend reservation will happen here - then you'll continue to the wizard."
      />
    </>
  );
}
