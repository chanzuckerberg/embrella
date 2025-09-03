import React from 'react';
import { InputSlider } from '@czi-sds/components';
import { Icon } from '@czi-sds/components';

interface SliderControlsProps {
  contrast: [number, number];
  onContrastChange: (value: [number, number]) => void;
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
  contrastRange?: [number, number]; // Dynamic range for the slider
  // Z-navigation props
  currentZIndex?: number;
  zAxisMetadata?: { min: number; max: number; count: number };
  onZIndexChange?: (zIndex: number) => void;
}

export const SliderControls = ({ contrast, onContrastChange, open, setOpen, contrastRange, currentZIndex, zAxisMetadata, onZIndexChange }: SliderControlsProps) => {
  // Calculate dynamic min/max based on contrast limits with some padding
  const [min, max] = contrastRange || [-0.1, 0.1];
  const sliderPadding = (max - min) * 2.0; // 200% padding for much wider range
  const sliderMin = min - sliderPadding;
  const sliderMax = max + sliderPadding;
  const step = Math.max(0.00001, (sliderMax - sliderMin) / 2000); // Smaller step for smoother movement
  return (
    <div className="flex flex-col gap-4 w-full min-w-[300px] max-w-[450px]">
      <div className="flex items-center justify-between cursor-pointer w-full" onClick={() => setOpen((v) => !v)}>
        <h3 className="font-bold text-lg">View Controls</h3>
        <span className="ml-2">
          {open ? <Icon sdsIcon="ChevronUp" sdsSize="s" /> : <Icon sdsIcon="ChevronDown" sdsSize="s" />}
        </span>
      </div>
      {open && (
        <div className="flex flex-col gap-4 w-full">
          <div>
            <label className="block mb-2 font-semibold">Tomogram Contrast</label>
            <InputSlider
              min={sliderMin}
              max={sliderMax}
              step={step}
              value={contrast}
              onChange={(_, value) => {
                const limits = value as [number, number];
                // Prevent updating if the limits are invalid (equal or decreasing)
                if (limits[0] >= limits[1]) {
                  return;
                }
                onContrastChange(limits);
              }}
              className="my-2 w-full"
            />
            <div className="text-xs text-gray-500 mt-1">
              Range: {sliderMin.toFixed(4)} to {sliderMax.toFixed(4)}
            </div>
          </div>
          
          {/* Z-Slice Navigation */}
          {zAxisMetadata && onZIndexChange && currentZIndex !== undefined && (
            <div>
              <label className="block mb-2 font-semibold">Z-Slice Navigation</label>
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
          )}
        </div>
      )}
    </div>
  );
};
