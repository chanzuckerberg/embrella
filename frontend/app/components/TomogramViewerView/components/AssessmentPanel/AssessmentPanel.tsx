import { Button, Icon } from '@czi-sds/components';
import { QualityControls } from '../QualityControls';
import { ObjectLabelsSelector } from '../ObjectLabelsSelector';
import { RejectionReasonsSelector } from '../RejectionReasonsSelector';
import { QualityValue } from '../../types';

interface AssessmentPanelProps {
  isDisabled: boolean;
  isSaving: boolean;
  quality: QualityValue;
  availableAnnotationObjects: string[];
  objectLabels: string[];
  rejectionReasons: string[];
  canDownload: boolean;
  onQualityChange: (quality: QualityValue) => void;
  onObjectLabelsChange: (labels: string[]) => void;
  onRejectionReasonsChange: (reasons: string[]) => void;
  onPrevious: () => void;
  onNext: () => void;
  onDownload: () => void;
}

/**
 * Grading controls for the current tomogram. Rendered as the right-hand column on
 * wide screens and inside the drawer on narrow ones, so it must not assume a
 * fixed width of its own.
 */
export const AssessmentPanel = ({
  isDisabled,
  isSaving,
  quality,
  availableAnnotationObjects,
  objectLabels,
  rejectionReasons,
  canDownload,
  onQualityChange,
  onObjectLabelsChange,
  onRejectionReasonsChange,
  onPrevious,
  onNext,
  onDownload,
}: AssessmentPanelProps) => {
  return (
    <div className="flex flex-col gap-3">
      <div className="shrink-0 !pt-[20px] !pr-[20px] !pl-[20px] !pb-[20px]">
        <QualityControls
          isDisabled={isDisabled}
          selectedQuality={quality}
          onAccept={() => onQualityChange('accepted')}
          onReject={() => onQualityChange('rejected')}
          onUncertain={() => onQualityChange('uncertain')}
          onExemplary={() => onQualityChange('exemplary')}
        />
      </div>
      {(quality === 'accepted' || quality === 'uncertain' || quality === 'exemplary') && (
        <div className="shrink-0 !pb-[20px] !pr-[20px] !pl-[20px] !pt-0">
          <ObjectLabelsSelector
            isDisabled={isDisabled}
            availableObjects={availableAnnotationObjects}
            selectedObjects={objectLabels}
            setSelectedObjects={onObjectLabelsChange}
          />
        </div>
      )}
      {quality === 'rejected' && (
        <div className="shrink-0 !pb-[20px] !pr-[20px] !pl-[20px] !pt-0">
          <RejectionReasonsSelector
            isDisabled={isDisabled}
            selectedReasons={rejectionReasons}
            setSelectedReasons={onRejectionReasonsChange}
          />
        </div>
      )}
      <div className="flex justify-center gap-4 !pt-[50px] max-lg:!pt-[20px]">
        <Button
          disabled={isSaving}
          className="!w-32"
          sdsStyle="outline"
          sdsType="secondary"
          startIcon={<Icon sdsIcon="ChevronLeft" sdsSize="xs" />}
          onClick={onPrevious}
        >
          Previous Tomo
        </Button>
        <Button
          disabled={isSaving}
          className="!w-32"
          sdsStyle="solid"
          sdsType="primary"
          endIcon={<Icon sdsIcon="ChevronRight" sdsSize="xs" />}
          onClick={onNext}
        >
          Next Tomo
        </Button>
      </div>
      <div className="flex justify-center !pt-[20px] max-lg:!pb-[20px]">
        <Button
          disabled={isSaving || !canDownload}
          className="!w-60"
          sdsStyle="outline"
          sdsType="secondary"
          onClick={onDownload}
        >
          Download Review
        </Button>
      </div>
    </div>
  );
};
