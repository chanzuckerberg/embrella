import { ViewControlsContainer, Slider, SliderLabel } from './style';

interface ViewControlsProps {
    contrast: number;
    onContrastChange: (value: number) => void;
    slabThickness: number;
    onSlabThicknessChange: (value: number) => void;
}

export const ViewControls = ({
    contrast,
    onContrastChange,
    slabThickness,
    onSlabThicknessChange,
}: ViewControlsProps) => {
    return (
        <ViewControlsContainer>
            <h3>View Controls</h3>
            <div>
                <SliderLabel>Tomogram Contrast</SliderLabel>
                <Slider
                    type="range"
                    min="0"
                    max="100"
                    value={contrast}
                    onChange={(e) => onContrastChange(Number(e.target.value))}
                />
            </div>
            <div>
                <SliderLabel>Slab-Thickness</SliderLabel>
                <Slider
                    type="range"
                    min="300"
                    max="1500"
                    value={slabThickness}
                    onChange={(e) => onSlabThicknessChange(Number(e.target.value))}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>300Å</span>
                    <span>1000Å</span>
                    <span>1500Å</span>
                </div>
            </div>
        </ViewControlsContainer>
    );
};