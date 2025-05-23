import { Region } from '../../../imaging-active-learning/packages/core/src/data/region';

export async function getRegionFromZattrs(zarrUrl: string): Promise<Region> {
  const zattrsUrl = `${zarrUrl}/.zattrs`;
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
    } else {
      return { dimension: dim, index: { type: 'full' } };
    }
  });
  return region;
}

export async function getZarrayMetadata(zarrUrl: string, levelIndex: number) {
  const zarrayUrl = `${zarrUrl}/${levelIndex}/.zarray`;
  const res = await fetch(zarrayUrl);
  if (!res.ok) {
    throw new Error(`Failed to fetch zarray from ${zarrayUrl}: ${res.statusText}`);
  }
  return await res.json();
}

export async function getRegionAndZarray(zarrUrl: string, levelIndex: number) {
  const [region, zarrayMeta] = await Promise.all([
    getRegionFromZattrs(zarrUrl),
    getZarrayMetadata(zarrUrl, levelIndex),
  ]);
  return { region, zarrayMeta };
}
