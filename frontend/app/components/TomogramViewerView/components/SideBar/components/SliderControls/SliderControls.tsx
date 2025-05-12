import { ChangeEvent } from 'react';
import { SideBarSection } from '../SideBarSection';

interface SliderControlsProps {
  contrast: number;
  onContrastChange: (value: number) => void;
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
        <h3 className="m-0">View Controls</h3>

        <div>
          <label className="block mb-2 font-medium">Tomogram Contrast</label>
          <input
            type="range"
            min="0"
            max="100"
            value={contrast}
            onChange={(e: ChangeEvent<HTMLInputElement>) => onContrastChange(Number(e.target.value))}
            className="my-2"
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
            className="my-2"
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
