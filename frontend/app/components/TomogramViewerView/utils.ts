import { Region } from '../../../idetik/packages/core/src/data/region';
import { SliceCoordinates } from '../../../idetik/packages/core/src/data/chunk';

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

export async function getRegionFromZattrs(zarrUrl: string, zIndex?: number): Promise<Region> {
  const zattrsUrl = `${zarrUrl}/.zattrs`;

  try {
    const res = await fetch(zattrsUrl);
    if (!res.ok) {
      throw new Error(`Failed to fetch zattrs from ${zattrsUrl}: ${res.statusText}`);
    }

    const zattrs = await res.json();
    const axes = zattrs?.axes ?? zattrs?.multiscales?.[0]?.axes;

    if (!Array.isArray(axes)) {
      throw new Error('No axes found in multiscales[0].axes');
    }

    const region: Region = axes.map((axis: { name: string; type: string }) => {
      const dim = axis.name;
      if (axis.type === 'time') {
        return { dimension: dim, index: { type: 'point', value: 0 } };
      } else if (dim === 'z' && zIndex !== undefined) {
        // For dynamic z-slicing, set z to a specific point
        return { dimension: dim, index: { type: 'point', value: zIndex } };
      } else if (dim === 'x' || dim === 'y') {
        // Use intervals to avoid chunk manager issues
        return { dimension: dim, index: { type: 'interval', start: 0, stop: -1 } };
      } else {
        return { dimension: dim, index: { type: 'full' } };
      }
    });
    return region;
  } catch (err) {
    console.warn('Falling back to default region due to error:', err);
    // If zIndex provided, create safe region with z-point
    if (zIndex !== undefined) {
      return [
        { dimension: 'z', index: { type: 'point', value: zIndex } },
        { dimension: 'y', index: { type: 'interval', start: 0, stop: -1 } },
        { dimension: 'x', index: { type: 'interval', start: 0, stop: -1 } },
      ];
    }
    return SAFE_REGION;
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
