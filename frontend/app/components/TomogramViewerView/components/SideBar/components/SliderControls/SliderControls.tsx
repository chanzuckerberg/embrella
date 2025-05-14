import { ChangeEvent } from 'react';
import { SideBarSection } from '../SideBarSection';
import { InputSlider } from '@czi-sds/components';

interface SliderControlsProps {
  contrast: [number, number];
  onContrastChange: (value: [number, number]) => void;
}

export const SliderControls = ({
  contrast,
  onContrastChange,
}: SliderControlsProps) => {
  return (
    <SideBarSection>
      <div className="flex flex-col gap-4">
        <h3 className="m-2">View Controls</h3>

        <div>
          <label className="block mb-2 font-medium">Tomogram Contrast</label>
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
    </SideBarSection>
  );
};
