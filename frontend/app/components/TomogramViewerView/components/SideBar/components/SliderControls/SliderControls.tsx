import { ChangeEvent } from 'react';
import { SideBarSection } from '../SideBarSection';
import { InputSlider } from '@czi-sds/components';

interface SliderControlsProps {
  contrast: [number, number];
  onContrastChange: (value: [number, number]) => void;
  slabThickness: number;
  onSlabThicknessChange: (value: number) => void;
}

export const SliderControls = ({
  contrast,
  onContrastChange,
  slabThickness,
  onSlabThicknessChange,
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
              console.log(value);
              onContrastChange(value as [number, number]);
            }}
            className="my-2 w-full"
          />
        </div>

        <div>
          <label className="block mb-2 font-medium">Slab-Thickness</label>
          <input
            type="range"
            min="300"
            max="1500"
            value={slabThickness}
            onChange={(e: ChangeEvent<HTMLInputElement>) => onSlabThicknessChange(Number(e.target.value))}
            className="my-2 w-full"
          />
          <div className="flex justify-between text-sm mt-1">
            <span>300Å</span>
            <span>1000Å</span>
            <span>1500Å</span>
          </div>
        </div>
      </div>
    </SideBarSection>
  );
};
