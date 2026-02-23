import { Region } from '@idetik/core';
import { SliceCoordinates } from '@idetik/core';

// Region that avoids chunk manager (for problematic zarr data)
const SAFE_REGION: Region = [
  { dimension: 'z', index: { type: 'point', value: 0 } },
  { dimension: 'y', index: { type: 'interval', start: 0, stop: -1 } }, // -1 means full extent
  { dimension: 'x', index: { type: 'interval', start: 0, stop: -1 } },
];

export async function getZAxisMetadata(zarrUrl: string): Promise<{ min: number; max: number; count: number }> {
  try {
    // Get the root zarr group info to find z-axis size
    const groupResponse = await fetch(`${zarrUrl}/.zgroup`);
    if (!groupResponse.ok) {
      throw new Error(`Failed to fetch .zgroup from ${zarrUrl}`);
    }

    // Try to get the array info from level 0 (highest resolution)
    const arrayResponse = await fetch(`${zarrUrl}/0/.zarray`);
    if (!arrayResponse.ok) {
      throw new Error(`Failed to fetch .zarray from ${zarrUrl}/0`);
    }

    const arrayInfo = await arrayResponse.json();
    const shape = arrayInfo.shape;

    if (!Array.isArray(shape) || shape.length < 3) {
      throw new Error('Invalid array shape found');
    }

    // Assume shape is [z, y, x] for 3D data
    const zCount = shape[0];
    return { min: 0, max: zCount - 1, count: zCount };
  } catch (err) {
    console.warn('Could not determine z-axis metadata, using defaults:', err);
    return { min: 0, max: 99, count: 100 }; // Default fallback
  }
}

export interface ContrastLimits {
  low: number;
  high: number;
}

export interface ZattrsData {
  region: Region;
  contrastLimits: ContrastLimits | null;
}

/**
 * Fetch and parse .zattrs from a zarr URL, extracting both region and contrast limits.
 * This avoids multiple fetches to the same .zattrs file.
 */
export async function getZattrsData(zarrUrl: string, zIndex?: number): Promise<ZattrsData> {
  const zattrsUrl = `${zarrUrl}/.zattrs`;

  const defaultRegion = (zIdx?: number): Region =>
    zIdx !== undefined
      ? [
          { dimension: 'z', index: { type: 'point', value: zIdx } },
          { dimension: 'y', index: { type: 'interval', start: 0, stop: -1 } },
          { dimension: 'x', index: { type: 'interval', start: 0, stop: -1 } },
        ]
      : SAFE_REGION;

  try {
    const res = await fetch(zattrsUrl);
    if (!res.ok) {
      console.warn(`Failed to fetch zattrs from ${zattrsUrl}: ${res.statusText}`);
      return { region: defaultRegion(zIndex), contrastLimits: null };
    }

    const zattrs = await res.json();

    // Extract region from axes
    const axes = zattrs?.axes ?? zattrs?.multiscales?.[0]?.axes;
    let region: Region;

    if (!Array.isArray(axes)) {
      console.warn('No axes found in zattrs, using default region');
      region = defaultRegion(zIndex);
    } else {
      region = axes.map((axis: { name: string; type: string }) => {
        const dim = axis.name;
        if (axis.type === 'time') {
          return { dimension: dim, index: { type: 'point', value: 0 } };
        } else if (dim === 'z' && zIndex !== undefined) {
          return { dimension: dim, index: { type: 'point', value: zIndex } };
        } else if (dim === 'x' || dim === 'y') {
          return { dimension: dim, index: { type: 'interval', start: 0, stop: -1 } };
        } else {
          return { dimension: dim, index: { type: 'full' } };
        }
      });
    }

    // Extract contrast limits if available
    let contrastLimits: ContrastLimits | null = null;
    const contrastLimitsData = zattrs?.image_statistics?.contrast_limits;
    if (
      contrastLimitsData &&
      typeof contrastLimitsData.low === 'number' &&
      typeof contrastLimitsData.high === 'number'
    ) {
      contrastLimits = {
        low: contrastLimitsData.low,
        high: contrastLimitsData.high,
      };
    }

    return { region, contrastLimits };
  } catch (err) {
    console.warn('Falling back to default region due to error:', err);
    return { region: defaultRegion(zIndex), contrastLimits: null };
  }
}

export function regionToSliceCoordinates(region: Region): SliceCoordinates {
  const sliceCoords: SliceCoordinates = {};
  region.forEach((regionDim) => {
    if (regionDim.index?.type === 'point') {
      const dimension = regionDim.dimension.toLowerCase();
      if (dimension === 'z' || dimension === 'c' || dimension === 't') {
        sliceCoords[dimension as keyof SliceCoordinates] = regionDim.index.value;
      }
    }
  });
  return sliceCoords;
}
