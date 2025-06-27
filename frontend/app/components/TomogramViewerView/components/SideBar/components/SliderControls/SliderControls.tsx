import React from 'react';
import { InputSlider } from '@czi-sds/components';
import { Icon } from '@czi-sds/components';

interface SliderControlsProps {
  contrast: [number, number];
  onContrastChange: (value: [number, number]) => void;
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
}

export const SliderControls = ({ contrast, onContrastChange, open, setOpen }: SliderControlsProps) => {
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
              min={-0.1}
              max={0.1}
              step={0.0001}
              value={contrast}
              onChange={(_, value) => {
                const limits = value as [number, number];
                // Prevent updating if the limits are invalid (equal or decreasing)
                // Also add a small buffer to prevent values that are too close
                if (limits[0] >= limits[1] || Math.abs(limits[1] - limits[0]) < 0.0001) {
                  return;
                }
                onContrastChange(limits);
              }}
              className="my-2 w-full"
            />
          </div>
        </div>
      )}
    </div>
  );
};
