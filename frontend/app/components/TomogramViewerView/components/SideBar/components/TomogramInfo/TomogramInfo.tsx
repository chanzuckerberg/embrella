import { useState } from 'react';
import { TomogramDetail } from '@app/components/TomogramViewerView/types';
import { Icon } from '@czi-sds/components';

export const TomogramInfo = ({ tomogramDetail }: { tomogramDetail: TomogramDetail | null }) => {
  const [open, setOpen] = useState(true);

  return (
    <div className="min-w-[300px] max-w-[450px] w-full">
      <div className="flex items-center justify-between cursor-pointer w-full" onClick={() => setOpen((v) => !v)}>
        <h3 className="font-bold text-lg">Current Tomogram Info</h3>
        <span className="ml-2">
          {open ? <Icon sdsIcon="ChevronUp" sdsSize="s" /> : <Icon sdsIcon="ChevronDown" sdsSize="s" />}
        </span>
      </div>
      {open && (
        <div className="mt-2 space-y-1 break-all">
          {tomogramDetail && (
            <>
              <div>
                <span className="font-bold">Organism:</span> <span className="italic">Mus musculus</span>
              </div>
              <div className="mt-2 space-y-1">
                <div>
                  <span className="font-bold">ID:</span> <span className="">{tomogramDetail.tomogramId}</span>
                </div>
                <div>
                  <span className="font-bold">Display Name:</span> <span>{tomogramDetail.displayName}</span>
                </div>
                <div>
                  <span className="font-bold">Zarr Path:</span> <span>{tomogramDetail.zarrPath}</span>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};
