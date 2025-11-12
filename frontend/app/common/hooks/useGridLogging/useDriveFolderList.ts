import { useFetchData } from '@hooks/useFetchData/useFetchData';
import { API } from '@app/common/constants/api';
import { DriveFolderListResponse } from '@app/common/types/gridLogging/driveFolderList';

export const useDriveFolderList = () => {
  const { data, isSuccess } = useFetchData<DriveFolderListResponse>(
    API.GRID_LOGGING_DRIVE_FOLDERS
  );

  return {
    folders: data?.folders || [],
    isSuccess,
    totalCount: data?.total_count || 0,
  };
};