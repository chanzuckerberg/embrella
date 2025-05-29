import { Region } from '../../../imaging-active-learning/packages/core/src/data/region';

const DEFAULT_REGION: Region = [
  { dimension: 'z', index: { type: 'full' } },
  { dimension: 'y', index: { type: 'full' } },
  { dimension: 'x', index: { type: 'full' } },
];

export async function getRegionFromZattrs(zarrUrl: string): Promise<Region> {
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
      } else {
        return { dimension: dim, index: { type: 'full' } };
      }
    });
    return region;
  } catch (err) {
    console.warn('Falling back to default region due to error:', err);
    return DEFAULT_REGION;
  }
}
