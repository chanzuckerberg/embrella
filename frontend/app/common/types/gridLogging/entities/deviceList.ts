export interface Device {
  id: number;
  name: string;
  maker_model: string;
}

export interface DeviceListResponse {
  total_devices_count: number;
  devices: Device[];
}

export const transformDevice = (device: Device) => {
  return {
    ...device,
    label: device.name,
    value: device.id,
  };
};
