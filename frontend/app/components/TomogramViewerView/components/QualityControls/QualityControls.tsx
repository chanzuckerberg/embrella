import { Button, Icon } from '@czi-sds/components';

interface QualityControlsProps {
  isDisabled: boolean;
  selectedQuality: string | null;
  onAccept: () => void;
  onReject: () => void;
  onUncertain: () => void;
  onExemplary: () => void;
}

export const QualityControls = ({
  isDisabled,
  selectedQuality,
  onAccept,
  onReject,
  onUncertain,
  onExemplary,
}: QualityControlsProps) => {
  return (
    <div className="w-[300px] p-4 flex flex-col gap-4">
      <h3 className="m-0 text-base font-semibold">Assign Tomogram Quality:</h3>
      <Button
        startIcon={<Icon sdsIcon="Check" sdsSize="s" />}
        sdsStyle={selectedQuality === 'accepted' ? 'solid' : 'outline'}
        sdsType={selectedQuality === 'accepted' ? 'primary' : 'secondary'}
        fullWidth
        disabled={isDisabled}
        onClick={onAccept}
      >
        Accept [a]
      </Button>
      <Button
        startIcon={<Icon sdsIcon="XMark" sdsSize="l" />}
        sdsStyle={selectedQuality === 'rejected' ? 'solid' : 'outline'}
        sdsType={selectedQuality === 'rejected' ? 'primary' : 'secondary'}
        fullWidth
        disabled={isDisabled}
        onClick={onReject}
      >
        Reject [r]
      </Button>
      <Button
        startIcon={<Icon sdsIcon="QuestionMark" sdsSize="l" />}
        sdsStyle={selectedQuality === 'uncertain' ? 'solid' : 'outline'}
        sdsType={selectedQuality === 'uncertain' ? 'primary' : 'secondary'}
        fullWidth
        disabled={isDisabled}
        onClick={onUncertain}
      >
        Uncertain [u]
      </Button>
      <Button
        startIcon={<Icon sdsIcon="Star" sdsSize="l" />}
        sdsStyle={selectedQuality === 'exemplary' ? 'solid' : 'outline'}
        sdsType={selectedQuality === 'exemplary' ? 'primary' : 'secondary'}
        fullWidth
        disabled={isDisabled}
        onClick={onExemplary}
      >
        Exemplary [e]
      </Button>
    </div>
  );
};
