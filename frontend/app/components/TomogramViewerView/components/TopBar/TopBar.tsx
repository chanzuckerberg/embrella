import { Button, Icon } from "@czi-sds/components";
import Link from "next/link";
import { TopBarContainer } from "./style";

interface TopBarProps {
    onMarkComplete?: () => void;
}

export const TopBar = ({ onMarkComplete }: TopBarProps) => {
    return (
        <TopBarContainer>
            <Link href="/reviews">
                <Button
                    startIcon={<Icon sdsIcon="ChevronLeft" sdsSize="xs" sdsType="iconButton" />}
                    sdsStyle="square"
                    sdsType="secondary"
                >
                    Exit review session
                </Button>
            </Link>
            <Button
                sdsStyle="square"
                sdsType="secondary"
                onClick={onMarkComplete}>
                Mark as Complete
            </Button>
        </TopBarContainer>
    );
};