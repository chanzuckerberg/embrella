import { SideBarSection } from './components/SideBarSection';
import { NavigationButtons } from './components/NavigationButtons';
import { TomogramTable } from './components/TomogramTable';
import { TomogramInfo } from './components/TomogramInfo';
import { SliderControls } from './components/SliderControls';
import { ReviewTomogramSummary } from '../../types';

interface SideBarProps {
    reviewName: string;
    tomograms: ReviewTomogramSummary[];
    selectedTomogram: string | null;
    currentIndex: number;
    onPrevious: () => void;
    onNext: () => void;
    onSelectTomogram: (tomogramId: string) => void;
    contrast: number;
    onContrastChange: (value: number) => void;
    slabThickness: number;
    onSlabThicknessChange: (value: number) => void;
}

export const SideBar = ({
    reviewName,
    tomograms,
    selectedTomogram,
    currentIndex,
    onPrevious,
    onNext,
    onSelectTomogram,
    contrast,
    onContrastChange,
    slabThickness,
    onSlabThicknessChange,
}: SideBarProps) => {
    return (
        <div className="w-[300px] h-full bg-white border-r border-gray-300 flex flex-col overflow-y-auto">
            <SideBarSection>
                <div className="p-6">
                    <h2>{reviewName}</h2>
                    <p>0 of {tomograms.length} Tomograms Reviewed</p>
                </div>
            </SideBarSection>

            <SideBarSection>
                <TomogramTable
                    tomograms={tomograms}
                    selectedTomogram={selectedTomogram}
                    onSelectTomogram={onSelectTomogram}
                />
                <NavigationButtons
                    currentIndex={currentIndex}
                    totalItems={tomograms.length}
                    onPrevious={onPrevious}
                    onNext={onNext}
                />
            </SideBarSection>

            {selectedTomogram && (
                <>
                    <TomogramInfo tomogramId={selectedTomogram} />
                    <SliderControls
                        contrast={contrast}
                        onContrastChange={onContrastChange}
                        slabThickness={slabThickness}
                        onSlabThicknessChange={onSlabThicknessChange}
                    />
                </>
            )}
        </div>
    );
};
