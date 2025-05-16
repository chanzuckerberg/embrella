import { SideBarSection } from './components/SideBarSection';
import { NavigationButtons } from './components/NavigationButtons';
import { TomogramTable } from './components/TomogramTable';
import { TomogramInfo } from './components/TomogramInfo';
import { SliderControls } from './components/SliderControls';
import { ReviewTomogramSummary, TomogramDetail } from '../../types';

interface SideBarProps {
  reviewName: string;
  tomograms: ReviewTomogramSummary[];
  selectedTomogram?: string;
  tomogramDetail: TomogramDetail | null;
  currentIndex: number;
  onPrevious: () => void;
  onNext: () => void;
  onSelectTomogram: (tomogramId: string) => void;
  contrastLimits: [number, number];
  onContrastLimitsChange: (value: [number, number]) => void;
}

export const SideBar = ({
  reviewName,
  tomograms,
  selectedTomogram,
  tomogramDetail,
  currentIndex,
  onPrevious,
  onNext,
  onSelectTomogram,
  contrastLimits: contrast,
  onContrastLimitsChange: onContrastChange,
}: SideBarProps) => {
  const reviewedCount = tomograms.filter(t => t.status !== 'pending').length;
  return (
    <div className="basis-[280px] shrink-0 flex flex-col justify-start gap-8 !p-[20px]">
      <SideBarSection>
        <div className="border-b border-gray-400">
          <div className="flex flex-col gap-2">
            <h2 className="font-bold text-xl leading-tight">
              Tomogram Quality Review <br />
            </h2>
            <span className="font-normal">{reviewName}</span>
            <div className="mt-2">
              <p className="text-sm font-medium">
                {reviewedCount} of {tomograms.length} Tomograms Reviewed
              </p>
            </div>
          </div>
        </div>
      </SideBarSection>

      <SideBarSection>
        <div className="border-b border-gray-400 flex flex-col gap-4">
          <TomogramTable tomograms={tomograms} selectedTomogram={selectedTomogram} onSelectTomogram={onSelectTomogram} />
          <NavigationButtons
            currentIndex={currentIndex}
            totalItems={tomograms.length}
            onPrevious={onPrevious}
            onNext={onNext}
          />
          <div className="h-6"></div>
        </div>
      </SideBarSection>

      <SideBarSection>
        <div className="border-b border-gray-400">
          <TomogramInfo tomogramDetail={tomogramDetail} />
          <div className="h-6"></div>
        </div>
      </SideBarSection>
      <SideBarSection>
        <SliderControls contrast={contrast} onContrastChange={onContrastChange} />
      </SideBarSection>
    </div >
  );
};
