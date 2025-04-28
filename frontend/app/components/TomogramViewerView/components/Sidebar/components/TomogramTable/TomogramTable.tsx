import { TomogramTableContainer, TomogramTableHeader, TomogramRow } from './style';
import { ReviewTomogramSummary } from '../../../../types';

interface TomogramTableProps {
    tomograms: ReviewTomogramSummary[];
    selectedTomogram: string | null;
    onSelectTomogram: (tomogramId: string) => void;
}

export const TomogramTable = ({
    tomograms,
    selectedTomogram,
    onSelectTomogram,
}: TomogramTableProps) => {
    return (
        <TomogramTableContainer>
            <TomogramTableHeader>
                <div>Tomogram</div>
                <div>Status</div>
            </TomogramTableHeader>
            {tomograms.map((tomogram) => (
                <TomogramRow
                    key={tomogram.tomogramId}
                    selected={selectedTomogram === tomogram.tomogramId}
                    onClick={() => onSelectTomogram(tomogram.tomogramId)}
                >
                    <div>{tomogram.tomogramId}</div>
                    <div>{tomogram.status}</div>
                </TomogramRow>
            ))}
        </TomogramTableContainer>
    );
};