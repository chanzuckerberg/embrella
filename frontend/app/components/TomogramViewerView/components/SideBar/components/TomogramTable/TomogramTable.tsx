import { ReviewTomogramSummary } from '../../../../types';

interface TomogramTableProps {
  tomograms: ReviewTomogramSummary[];
  selectedTomogram?: string | undefined;
  onSelectTomogram: (tomogramId: string) => void;
}

export const TomogramTable = ({ tomograms, selectedTomogram, onSelectTomogram }: TomogramTableProps) => {
  return (
    <div className="flex flex-col gap-2">
      <div className="grid grid-cols-3 gap-2 font-bold p-2 bg-gray-100 rounded">
        <div>Tomogram</div>
        <div>Status</div>
        <div className="text-center">Reviewed</div>
      </div>

      <div className="overflow-y-auto max-h-[100px]">
        {tomograms.map((tomogram) => {
          const isSelected = selectedTomogram === tomogram.tomogramId;
          const isReviewed = tomogram.status !== 'pending';
          return (
            <div
              key={tomogram.tomogramId}
              onClick={() => onSelectTomogram(tomogram.tomogramId)}
              className={`grid grid-cols-3 gap-2 p-2 cursor-pointer rounded ${isSelected ? 'bg-blue-100' : 'hover:bg-gray-100 transition-colors duration-100'
                }`}
            >
              <div>{tomogram.position}</div>
              <div>{tomogram.status}</div>
              <div className="flex justify-center items-center">
                <div
                  className={`w-4 h-4 rounded-full border-1 ${isReviewed ? 'bg-gray-300 border-gray-400' : 'border-gray-300'
                    }`}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
