import { Button, Icon } from '@czi-sds/components';
import { useRouter } from 'next/navigation';
import { SaveState } from '../../types';

interface TopBarProps {
  saveState?: SaveState;
}

const SAVE_STATE_LABELS: Record<Exclude<SaveState, 'idle'>, string> = {
  saving: 'Saving...',
  saved: 'All changes saved',
  failed: 'Failed to save changes',
};

export const TopBar = ({ saveState }: TopBarProps) => {
  const router = useRouter();
  const saveLabel = saveState && saveState !== 'idle' ? SAVE_STATE_LABELS[saveState] : undefined;

  return (
    <div className="flex flex-row justify-between items-center basis-[50px] shrink-0 w-full !px-[20px] max-lg:!px-[12px] !py-[10px] gap-2">
      <Button
        sdsStyle="outline"
        sdsType="secondary"
        className="!text-[14px] whitespace-nowrap"
        startIcon={<Icon sdsIcon="ChevronLeft" sdsSize="xs" />}
        onClick={() => router.push('/processing/tomograms/reviews')}
      >
        Exit review session
      </Button>
      {saveLabel && (
        <div className="flex flex-row items-center shrink-0" title={saveLabel} aria-label={saveLabel}>
          {saveState === 'saving' && <Icon sdsIcon={'Loading'} sdsSize={'xs'} className="!mr-[5px]" />}
          {saveState === 'saved' && <Icon sdsIcon={'Check'} sdsSize={'xs'} className="!mr-[5px]" />}
          {saveState === 'failed' && <Icon sdsIcon={'XMark'} sdsSize={'xs'} className="!mr-[5px]" />}
          <span className="max-lg:hidden">{saveLabel}</span>
        </div>
      )}
    </div>
  );
};
