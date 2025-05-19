import { TomogramDetail } from '@app/components/TomogramViewerView/types';
import { SideBarSection } from '../SideBarSection';

export const TomogramInfo = ({ tomogramDetail }: { tomogramDetail: TomogramDetail | null }) => {
  return (
    <SideBarSection>
      <div>
        <h3>Current Tomogram Info</h3>
        <p>Organism: Mus musculus</p>
        {tomogramDetail && (
          <>
            <p>ID: {tomogramDetail.tomogramId}</p>
            <p>Display Name: {tomogramDetail.displayName}</p>
            <p>Zarr Path: {tomogramDetail.zarrPath}</p>
          </>
        )}
      </div>
    </SideBarSection>
  );
};
