import React from 'react';
import { InputSlider } from '@czi-sds/components';
import { Icon } from '@czi-sds/components';

interface SliderControlsProps {
  /** Collapsed state of the accordion. Unused when `compact` is set. */
  open?: boolean;
  setOpen?: React.Dispatch<React.SetStateAction<boolean>>;
  compact?: boolean;
  // Z-navigation props
  currentZIndex?: number;
  zAxisMetadata?: { min: number; max: number; count: number };
  onZIndexChange?: (zIndex: number) => void;
}

export const SliderControls = ({
  open,
  setOpen,
  compact = false,
  currentZIndex,
  zAxisMetadata,
  onZIndexChange,
}: SliderControlsProps) => {
  const hasSlices = zAxisMetadata && onZIndexChange && currentZIndex !== undefined;

  const slider = hasSlices ? (
    <InputSlider
      min={zAxisMetadata.min}
      max={zAxisMetadata.max}
      step={1}
      value={currentZIndex}
      onChange={(_, value) => {
        const zIndex = Array.isArray(value) ? value[0] : value;
        onZIndexChange(Math.round(zIndex));
      }}
      className={compact ? 'w-full' : 'my-2 w-full'}
    />
  ) : null;

  if (compact) {
    return (
      <div className="flex items-center gap-4 w-full">
        <span className="shrink-0 font-bold text-sm">Z-Slice</span>
        <div className="flex-auto min-w-0 flex items-center">
          {slider ?? <span className="text-gray-500 text-sm">Loading...</span>}
        </div>
        {hasSlices && (
          <span className="shrink-0 text-xs text-gray-500 tabular-nums">
            {currentZIndex + 1} / {zAxisMetadata.count}
          </span>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 w-full min-w-[300px] max-lg:!min-w-0 max-w-[450px]">
      <div className="flex items-center justify-between cursor-pointer w-full" onClick={() => setOpen?.((v) => !v)}>
        <h3 className="font-bold text-lg">Z-Slice Navigation</h3>
        <span className="ml-2">
          {open ? <Icon sdsIcon="ChevronUp" sdsSize="s" /> : <Icon sdsIcon="ChevronDown" sdsSize="s" />}
        </span>
      </div>
      {open && (
        <div className="flex flex-col gap-4 w-full">
          {hasSlices ? (
            <div>
              {slider}
              <div className="text-xs text-gray-500 mt-1">
                Slice {currentZIndex + 1} of {zAxisMetadata.count}
              </div>
            </div>
          ) : (
            <div className="text-gray-500 text-sm">Loading...</div>
          )}
        </div>
      )}
    </div>
  );
};
