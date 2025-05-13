import { ReviewTomogramSummary } from '../../../../types';

interface TomogramTableProps {
  tomograms: ReviewTomogramSummary[];
  selectedTomogram?: string;
  onSelectTomogram: (tomogramId: string) => void;
}

export const TomogramTable = ({ tomograms, selectedTomogram, onSelectTomogram }: TomogramTableProps) => {
  return (
    <div className="flex flex-col gap-2">
      <div className="grid grid-cols-2 gap-2 font-bold p-2 bg-gray-100 rounded">
        <div>Tomogram</div>
        <div>Status</div>
      </div>

      {tomograms.map((tomogram) => {
        const isSelected = selectedTomogram === tomogram.tomogramId;
        return (
          <div
            key={tomogram.tomogramId}
            onClick={() => onSelectTomogram(tomogram.tomogramId)}
            className={`grid grid-cols-2 gap-2 p-2 cursor-pointer rounded ${
              isSelected ? 'bg-blue-100' : 'hover:bg-gray-100 transition-colors duration-100'
            }`}
          >
            <div>{tomogram.tomogramId}</div>
            <div>{tomogram.status}</div>
          </div>
        );
      })}
    </div>
  );
};
