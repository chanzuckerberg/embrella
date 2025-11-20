import { API } from '@app/common/constants/api';
import { DriveFolderListResponse } from '@app/common/types/gridLogging/resources/driveFolderList';
import { useListResource } from '../base/useListResource';

export const useDriveFolderList = () => {
  const { items, isSuccess, totalCount } = useListResource({
    endpoint: API.GRID_LOGGING_DRIVE_FOLDERS,
    selectItems: (data: DriveFolderListResponse) => data.folders || [],
    getTotalCount: (data: DriveFolderListResponse) => data.total_count || 0,
  });

  return {
    folders: items,
    isSuccess,
    totalCount,
  };
};
