import { Button, Icon } from '@czi-sds/components';

interface QualityControlsProps {
  selectedQuality: string;
  onAccept: () => void;
  onReject: () => void;
  onUncertain: () => void;
}

export const QualityControls = ({ selectedQuality, onAccept, onReject, onUncertain }: QualityControlsProps) => {
  return (
    <div className="w-[300px] p-4 flex flex-col gap-4">
      <h3 className="m-0 text-base font-semibold">Assign Tomogram Quality:</h3>
      <Button
        startIcon={<Icon sdsIcon="Check" sdsSize="s" />}
        sdsStyle="square"
        sdsType="secondary"
        fullWidth
        onClick={onAccept}
      >
        Accept [1]
      </Button>
      <Button
        startIcon={<Icon sdsIcon="XMark" sdsSize="l" />}
        sdsStyle="square"
        sdsType={selectedQuality === "rejected" ? "primary" : "secondary"}
        fullWidth
        onClick={onReject}
      >
        Reject [2]
      </Button>
      <Button
        startIcon={<Icon sdsIcon="QuestionMark" sdsSize="l" />}
        sdsStyle="square"
        sdsType="secondary"
        fullWidth
        onClick={onUncertain}
      >
        Uncertain [3]
      </Button>
    </div>
  );
};
