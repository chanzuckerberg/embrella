import { Button, Icon } from '@czi-sds/components';
import { useRouter } from 'next/navigation';

interface TopBarProps {
  saveState?: 'saving' | 'saved' | 'failed';
}

export const TopBar = ({ saveState }: TopBarProps) => {
  const router = useRouter();

  return (
    <div className="flex flex-row justify-between items-center basis-[50px] shrink-0 w-full !px-[25px] !py-[10px]]">
      <Button
        sdsStyle="square"
        sdsType="secondary"
        className="!text-[14px]"
        startIcon={<Icon sdsIcon="ChevronLeft" sdsSize="xs" />}
        onClick={() => router.push('/reviews')}
      >
        Exit review session
      </Button>
      <div>
        {saveState === 'saving' && (
          <>
            <Icon sdsIcon={'Loading'} sdsSize={'xs'} className="!mr-[5px]" />
            Saving...
          </>
        )}
        {saveState === 'saved' && (
          <>
            <Icon sdsIcon={'Check'} sdsSize={'xs'} className="!mr-[5px]" />
            All changes saved
          </>
        )}
      </div>
    </div>
  );
};
