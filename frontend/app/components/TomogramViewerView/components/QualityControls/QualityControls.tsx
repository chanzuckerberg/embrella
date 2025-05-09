import { Button, Icon } from "@czi-sds/components";

interface QualityControlsProps {
    onAccept: () => void;
    onReject: () => void;
    onUncertain: () => void;
}

export const QualityControls = ({ onAccept, onReject, onUncertain }: QualityControlsProps) => {
    return (
        <div className="w-[300px] p-4 bg-white border-l border-gray-300 flex flex-col gap-4">
            <h3 className="m-0 text-base font-semibold">Assign Tomogram Quality:</h3>
            <Button
                startIcon={<Icon sdsIcon="Check" sdsSize="s" sdsType="iconButton" />}
                sdsStyle="square"
                sdsType="secondary"
                fullWidth
                onClick={onAccept}
            >
                Accept [1]
            </Button>
            <Button
                startIcon={<Icon sdsIcon="XMark" sdsSize="l" sdsType="iconButton" />}
                sdsStyle="square"
                sdsType="secondary"
                fullWidth
                onClick={onReject}
            >
                Reject [2]
            </Button>
            <Button
                startIcon={<Icon sdsIcon="QuestionMark" sdsSize="l" sdsType="iconButton" />}
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