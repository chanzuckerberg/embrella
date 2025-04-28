import { SidebarContainer } from './style';
import { SidebarSection } from './components/SidebarSection';
import { NavigationButtons } from './components/NavigationButtons';
import { TomogramTable } from './components/TomogramTable';
import { TomogramInfo } from './components/TomogramInfo';
import { SliderControls } from './components/SliderControls';
import { ReviewTomogramSummary } from '../../types';

interface SidebarProps {
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

export const Sidebar = ({
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
}: SidebarProps) => {
    return (
        <SidebarContainer>
            <SidebarSection>
                <div>
                    <h2>{reviewName}</h2>
                    <p>0 of {tomograms.length} Tomograms Reviewed</p>
                </div>
            </SidebarSection>

            <SidebarSection>
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
            </SidebarSection>

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
        </SidebarContainer>
    );
};