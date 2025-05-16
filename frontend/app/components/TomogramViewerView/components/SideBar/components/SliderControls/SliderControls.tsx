import { useState } from 'react';
import { SideBarSection } from '../SideBarSection';
import { InputSlider } from '@czi-sds/components';
import { Icon } from '@czi-sds/components';

interface SliderControlsProps {
  contrast: [number, number];
  onContrastChange: (value: [number, number]) => void;
}

export const SliderControls = ({ contrast, onContrastChange }: SliderControlsProps) => {
  const [open, setOpen] = useState(true);
  return (
    <SideBarSection>
      <div className="flex flex-col gap-4 w-full min-w-[300px] max-w-[450px]">
        <div className="flex items-center justify-between cursor-pointer w-full" onClick={() => setOpen((v) => !v)}>
          <h3 className="font-bold text-lg">View Controls</h3>
          <span className="ml-2">
            {open ? (
              <Icon sdsIcon="ChevronUp" sdsSize="s" />
            ) : (
              <Icon sdsIcon="ChevronDown" sdsSize="s" />
            )}
          </span>
        </div>
        {open && (
          <div className="flex flex-col gap-4 w-full">
            <div>
              <label className="block mb-2 font-semibold">Tomogram Contrast</label>
              <InputSlider
                min={-0.0001}
                max={0.0001}
                step={0.000001}
                value={contrast}
                onChange={(_, value) => {
                  onContrastChange(value as [number, number]);
                }}
                className="my-2 w-full"
              />
            </div>
          </div>
        )}
      </div>
    </SideBarSection>
  );
};
