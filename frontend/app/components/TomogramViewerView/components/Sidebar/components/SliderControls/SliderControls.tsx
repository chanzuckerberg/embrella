import { SidebarSection } from "../SidebarSection";
import { SliderContainer, Slider, SliderLabel } from "./style";
import { ChangeEvent } from "react";

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
        <SidebarSection>
            <SliderContainer>
                <h3>View Controls</h3>
                <div>
                    <SliderLabel>Tomogram Contrast</SliderLabel>
                    <Slider
                        type="range"
                        min="0"
                        max="100"
                        value={contrast}
                        onChange={(e: ChangeEvent<HTMLInputElement>) => onContrastChange(Number(e.target.value))}
                    />
                </div>
                <div>
                    <SliderLabel>Slab-Thickness</SliderLabel>
                    <Slider
                        type="range"
                        min="300"
                        max="1500"
                        value={slabThickness}
                        onChange={(e: ChangeEvent<HTMLInputElement>) => onSlabThicknessChange(Number(e.target.value))}
                    />
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span>300Å</span>
                        <span>1000Å</span>
                        <span>1500Å</span>
                    </div>
                </div>
            </SliderContainer>
        </SidebarSection>
    );
};