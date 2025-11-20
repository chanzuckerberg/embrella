import { API } from '@app/common/constants/api';
import { DeviceListResponse, transformDevice } from '@app/common/types/gridLogging/entities/deviceList';
import { useListResource } from '../base/useListResource';

export const useDeviceList = () => {
  const { items, isSuccess, totalCount, transformedItems, rawData } = useListResource({
    endpoint: API.GRID_LOGGING_DEVICES,
    selectItems: (data: DeviceListResponse) => data.devices || [],
    getTotalCount: (data: DeviceListResponse) => data.total_devices_count || 0,
    transform: transformDevice,
  });

  return {
    devices: items,
    isSuccess,
    totalCount,
    transformedDevices: transformedItems,
    rawData,
  };
};
