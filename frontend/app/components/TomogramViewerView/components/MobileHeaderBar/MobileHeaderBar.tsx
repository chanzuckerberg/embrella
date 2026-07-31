import { Button, Icon } from '@czi-sds/components';

interface MobileHeaderBarProps {
  reviewName: string;
  tomogramName?: string;
  currentIndex: number;
  totalTomograms: number;
  onOpenMenu: () => void;
}

/**
 * Narrow-screen context bar, displaying
 * which review you are in, which tomogram you are looking at,
 * and entry point back to the controls.
 */
export const MobileHeaderBar = ({
  reviewName,
  tomogramName,
  currentIndex,
  totalTomograms,
  onOpenMenu,
}: MobileHeaderBarProps) => {
  return (
    <div className="flex flex-row items-center gap-3 shrink-0 border-t-[2px] border-gray-300 bg-gray-50 !px-[12px] !py-[8px]">
      <Button
        sdsStyle="outline"
        sdsType="primary"
        className="shrink-0 !text-[13px] whitespace-nowrap"
        aria-label="Open review controls"
        startIcon={<Icon sdsIcon="LinesHorizontal3" sdsSize="xs" />}
        onClick={onOpenMenu}
      >
        Controls
      </Button>
      <div className="flex-auto min-w-0 flex flex-col">
        <div className="font-bold text-sm truncate" title={reviewName}>
          {reviewName}
        </div>
        <div className="text-xs text-[#767676] truncate" title={tomogramName}>
          {tomogramName ?? 'Loading tomogram...'}
        </div>
      </div>
      {totalTomograms > 0 && (
        <div className="shrink-0 text-xs text-[#767676] tabular-nums">
          {currentIndex + 1} / {totalTomograms}
        </div>
      )}
    </div>
  );
};
