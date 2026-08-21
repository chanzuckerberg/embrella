import { useState } from 'react';
import { Box, Card, CardContent, Skeleton, Tooltip, Typography } from '@mui/material';
import { Link } from '@czi-sds/components';

import { StorageSummary } from '../types';

/** How many software rows fit beside the other tiles without growing the card. */
const COLLAPSED_SOFTWARE = 6;

interface StorageStatsCardProps {
  summary: StorageSummary | null;
  loading: boolean;
  onViewAllPaths: () => void;
  leading?: React.ReactNode;
}

const CARD_SX = { mb: 1 } as const;
const CONTENT_SX = { px: 2, py: 1.25, '&:last-child': { pb: 1.25 } } as const;
const ROW_SX = { display: 'flex', flexWrap: 'wrap', columnGap: 4, rowGap: 1.5, alignItems: 'flex-start' } as const;

const Caption = ({ children }: { children: React.ReactNode }) => (
  <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
    {children}
  </Typography>
);

const Label = Caption;
const Detail = Caption;

const Value = ({ children }: { children: React.ReactNode }) => <Typography variant="h6">{children}</Typography>;

const Tile = ({ children, minWidth = 150 }: { children: React.ReactNode; minWidth?: number }) => (
  <Box sx={{ flex: `0 1 ${minWidth}px`, minWidth }}>{children}</Box>
);

export const StorageStatsCard = ({
  summary,
  loading,
  onViewAllPaths,
  leading,
}: StorageStatsCardProps): React.JSX.Element => {
  const [showAllSoftware, setShowAllSoftware] = useState(false);

  if (loading) {
    return (
      <Card sx={CARD_SX} variant="outlined">
        <CardContent sx={CONTENT_SX}>
          <Box sx={ROW_SX}>
            {leading}
            <Box sx={{ flex: 1, minWidth: 240 }}>
              <Skeleton variant="rectangular" height={48} />
            </Box>
          </Box>
        </CardContent>
      </Card>
    );
  }

  if (!summary?.total || !summary.inTree || !summary.outsideTree) {
    return (
      <Card sx={CARD_SX} variant="outlined">
        <CardContent sx={CONTENT_SX}>
          <Box sx={ROW_SX}>
            {leading}
            <Typography variant="body2" color="text.secondary">
              No completed survey for this cluster yet, so there is nothing to summarise.
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  const { total, inTree, outsideTree, bySoftware } = summary;
  const visibleSoftware = showAllSoftware ? bySoftware : bySoftware.slice(0, COLLAPSED_SOFTWARE);
  const hiddenCount = bySoftware.length - visibleSoftware.length;

  return (
    <Card sx={CARD_SX} variant="outlined">
      <CardContent sx={CONTENT_SX}>
        <Box sx={ROW_SX}>
          {leading}

          <Tile minWidth={175}>
            <Label>Cluster total</Label>
            <Value>{total.totalSizeDisplay}</Value>
            <Detail>{total.directoryCount.toLocaleString()} dirs</Detail>
            <Tooltip
              title={`${outsideTree.directoryCount.toLocaleString()} directories are not under a processing software folder, so they cannot appear in this table. They are visible in All Paths.`}
            >
              <Link
                component="button"
                variant="caption"
                onClick={onViewAllPaths}
                sx={{ textAlign: 'left', whiteSpace: 'nowrap' }}
              >
                {outsideTree.totalSizeDisplay} elsewhere →
              </Link>
            </Tooltip>
          </Tile>

          <Tile>
            <Label>Processing data</Label>
            <Value>{inTree.totalSizeDisplay}</Value>
            <Detail>
              {inTree.sessionCount} sessions · {inTree.runCount.toLocaleString()} runs
            </Detail>
            {inTree.unregisteredSessionCount > 0 && (
              <Detail>{inTree.unregisteredSessionCount} not tracked in Embrella</Detail>
            )}
          </Tile>

          <Tile minWidth={420}>
            <Label>By software</Label>
            <Box
              sx={{
                display: 'grid',
                // Three columns so the tile stays the same height as its
                // neighbours instead of stretching the card into a list.
                gridTemplateColumns: 'repeat(3, auto)',
                columnGap: 3,
                width: 'fit-content',
              }}
            >
              {visibleSoftware.map((item) => (
                <Tooltip
                  key={item.software}
                  title={`${item.sessionCount} sessions · ${item.directoryCount.toLocaleString()} dirs`}
                  placement="top"
                >
                  <Typography variant="caption" sx={{ whiteSpace: 'nowrap' }}>
                    {item.software}{' '}
                    <Box component="span" sx={{ color: 'text.secondary' }}>
                      {item.totalSizeDisplay}
                    </Box>
                  </Typography>
                </Tooltip>
              ))}
            </Box>
            {(hiddenCount > 0 || showAllSoftware) && (
              <Link
                component="button"
                variant="caption"
                onClick={() => setShowAllSoftware((previous) => !previous)}
                aria-expanded={showAllSoftware}
              >
                {showAllSoftware ? 'show fewer' : `+${hiddenCount} more`}
              </Link>
            )}
          </Tile>
        </Box>
      </CardContent>
    </Card>
  );
};
