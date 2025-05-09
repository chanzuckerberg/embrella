import { Button, Icon } from "@czi-sds/components";
import { useRouter } from "next/navigation";

interface TopBarProps {
    onMarkComplete?: () => void;
}

export const TopBar = ({ onMarkComplete }: TopBarProps) => {
    const router = useRouter();
    return (
        <div className="w-full flex justify-between items-center h-16 px-6 max-w-6xl mx-auto bg-purple-300 border border-black">
            <Button
                sdsStyle="square"
                sdsType="secondary"
                startIcon={
                    <Icon sdsIcon="ChevronLeft" sdsSize="xs" sdsType="iconButton" />
                }
                onClick={() => router.push("/reviews")}
            >
                Exit review session
            </Button>

            <Button
                sdsStyle="square"
                sdsType="secondary"
                onClick={onMarkComplete}
                size="small"
            >
                Mark as Complete
            </Button>
        </div>
    );
};
