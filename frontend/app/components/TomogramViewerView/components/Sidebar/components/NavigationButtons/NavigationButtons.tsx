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
        <NavigationButtonsContainer>
            <Button
                sdsStyle="square"
                sdsType="secondary"
                disabled={currentIndex <= 0}
                onClick={onPrevious}
                startIcon={<Icon sdsIcon="ChevronLeft" sdsSize="s" sdsType="iconButton" />}
            >
                Previous
            </Button>
            <Button
                sdsStyle="square"
                sdsType="secondary"
                disabled={currentIndex >= totalItems - 1}
                onClick={onNext}
                endIcon={<Icon sdsIcon="ChevronRight" sdsSize="s" sdsType="iconButton" />}
            >
                Next
            </Button>
        </NavigationButtonsContainer>
    );
};