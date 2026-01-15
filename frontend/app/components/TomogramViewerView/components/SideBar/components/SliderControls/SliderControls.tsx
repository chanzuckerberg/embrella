import React from 'react';
import { InputSlider } from '@czi-sds/components';
import { Icon } from '@czi-sds/components';

interface SliderControlsProps {
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
  // Z-navigation props
  currentZIndex?: number;
  zAxisMetadata?: { min: number; max: number; count: number };
  onZIndexChange?: (zIndex: number) => void;
}

export const SliderControls = ({
  open,
  setOpen,
  currentZIndex,
  zAxisMetadata,
  onZIndexChange,
}: SliderControlsProps) => {
  return (
    <div className="flex flex-col gap-4 w-full min-w-[300px] max-w-[450px]">
      <div className="flex items-center justify-between cursor-pointer w-full" onClick={() => setOpen((v) => !v)}>
        <h3 className="font-bold text-lg">Z-Slice Navigation</h3>
        <span className="ml-2">
          {open ? <Icon sdsIcon="ChevronUp" sdsSize="s" /> : <Icon sdsIcon="ChevronDown" sdsSize="s" />}
        </span>
      </div>
      {open && (
        <div className="flex flex-col gap-4 w-full">
          {zAxisMetadata && onZIndexChange && currentZIndex !== undefined ? (
            <div>
              <InputSlider
                min={zAxisMetadata.min}
                max={zAxisMetadata.max}
                step={1}
                value={currentZIndex}
                onChange={(_, value) => {
                  const zIndex = Array.isArray(value) ? value[0] : value;
                  onZIndexChange(Math.round(zIndex));
                }}
                className="my-2 w-full"
              />
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
