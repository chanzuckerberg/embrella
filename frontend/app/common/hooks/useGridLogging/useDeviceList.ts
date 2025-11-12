import { useFetchData } from '@hooks/useFetchData/useFetchData';
import { API } from '@app/common/constants/api';
import { useMemo } from 'react';
import { 
  DeviceListResponse, 
  Device, 
  transformDevice 
} from '@app/common/types/gridLogging/deviceList';

export interface UseDeviceListReturn {
  devices: Device[];
  isSuccess: boolean;
  totalCount: number;
  transformedDevices: ReturnType<typeof transformDevice>[];
  rawData?: DeviceListResponse;
}

export const useDeviceList = (): UseDeviceListReturn => {
  const { data, isSuccess } = useFetchData<DeviceListResponse>(
    API.GRID_LOGGING_DEVICES
  );

  const devices = useMemo(() => {
    if (!data) return [];
    return data.devices || [];
  }, [data]);

  const transformedDevices = useMemo(() => {
    return devices.map(transformDevice);
  }, [devices]);

  return {
    devices,
    isSuccess,
    totalCount: data?.total_devices_count || 0,
    transformedDevices,
    rawData: data,
  };
};