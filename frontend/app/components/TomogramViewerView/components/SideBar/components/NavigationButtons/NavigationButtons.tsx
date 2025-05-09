import { Button, Icon } from "@czi-sds/components";
import { NavigationButtonsContainer } from './style';


interface NavigationButtonsProps {
    currentIndex: number;
    totalItems: number;
    onPrevious: () => void;
    onNext: () => void;
}

export const NavigationButtons = ({
    currentIndex,
    totalItems,
    onPrevious,
    onNext,
}: NavigationButtonsProps) => {
    return (
        <div className="flex justify-between gap-4 mt-4">
            <Button
                sdsStyle="square"
                sdsType="secondary"
                disabled={currentIndex <= 0}
                onClick={onPrevious}
                startIcon={<Icon sdsIcon="ChevronLeft" sdsSize="s" sdsType="iconButton" />}
                className="flex-1 text-sm text-blue-600 disabled:text-gray-400"
            >
                Previous
            </Button>
            <Button
                sdsStyle="square"
                sdsType="secondary"
                disabled={currentIndex >= totalItems - 1}
                onClick={onNext}
                endIcon={<Icon sdsIcon="ChevronRight" sdsSize="s" sdsType="iconButton" />}
                className="flex-1 text-sm text-blue-600 disabled:text-gray-400"
            >
                Next
            </Button>
        </div>
    );
};
