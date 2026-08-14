'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Box, FormControl, InputLabel, MenuItem, Select, Tooltip, Typography } from '@mui/material';
import { Callout, Tab, Tabs } from '@czi-sds/components';
import { parseAsString, useQueryState } from 'nuqs';

import { EntityTableFilters } from '@app/common/components/EntityTableFilters/EntityTableFilters';
import { FilterableTableMain } from '@app/common/components/FilterableTableMain/FilterableTableMain';
import { Sidebar } from '@app/common/components/Sidebar/Sidebar';
import { TableStateProvider } from '@app/common/components/TableStateProvider/TableStateProvider';
import { TableWrapper } from '@app/common/components/TableWrapper/TableWrapper';
import { API } from '@app/common/constants/api';
import { formatDate } from '@app/common/utils/format';
import { DirectoryExplorerView } from '@app/components/DirectoryExplorerView';
import { fetchSurveys } from '@app/components/DirectoryExplorerView/api';

import { fetchStorageSummary, recordStorageDecision } from './api';
import { StatusActionMenu } from './components/StatusActionMenu';
import { StorageSearchBar } from './components/StorageSearchBar';
import { StorageStatsCard } from './components/StorageStatsCard';
import { STORAGE_FILTER_CATEGORIES, STORAGE_FILTER_CONFIGS } from './constants/filters';
import { StorageDecisionContext } from './context/StorageDecisionContext';
import { GroupTable } from './GroupTable';
import { DecisionTarget, SettableStatus, StorageFilterCategory, StorageFilterId, StorageSummary } from './types';

const ENTITY_TAB = 'entity';
const PATHS_TAB = 'paths';

const TABS = [ENTITY_TAB, PATHS_TAB] as const;
const TAB_LABELS: Record<(typeof TABS)[number], string> = {
  [ENTITY_TAB]: 'By MSI Session',
  [PATHS_TAB]: 'All Paths',
};

function useSurveyedClusters(): string[] {
  const [clusters, setClusters] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;
    fetchSurveys(undefined, 'completed')
      .then((response) => {
        if (cancelled) return;
        setClusters([...new Set((response.surveys ?? []).map((survey) => survey.cluster))].sort());
      })
      .catch(() => {
        // A failed lookup leaves the selector empty rather than guessing; the
        // table still works, on whichever cluster the backend defaults to.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return clusters;
}

const StorageExplorerLayout = (): React.JSX.Element => {
  const [tab, setTab] = useQueryState('tab', parseAsString.withDefault(ENTITY_TAB));
  const [clusterParam, setClusterParam] = useQueryState('cluster', parseAsString);

  const clusters = useSurveyedClusters();
  const [summary, setSummary] = useState<StorageSummary | null>(null);
  const [loadingSummary, setLoadingSummary] = useState(true);

  const cluster = clusterParam ?? '';

  // Switching cluster
  const [loadedCluster, setLoadedCluster] = useState(cluster);
  if (cluster !== loadedCluster) {
    setLoadedCluster(cluster);
    setLoadingSummary(true);
  }

  useEffect(() => {
    let cancelled = false;

    fetchStorageSummary(cluster || undefined)
      .then((data) => {
        if (!cancelled) setSummary(data);
      })
      .catch(() => {
        if (!cancelled) setSummary(null);
      })
      .finally(() => {
        if (!cancelled) setLoadingSummary(false);
      });

    return () => {
      cancelled = true;
    };
  }, [cluster]);

  const survey = summary?.survey ?? null;

  // The backend resolves its default when no cluster is named
  const selectedCluster = cluster || survey?.cluster || '';

  const tabIndex = Math.max(TABS.indexOf(tab as (typeof TABS)[number]), 0);

  const goToAllPaths = useCallback(() => {
    void setTab(PATHS_TAB);
  }, [setTab]);

  // Set-status menu, shared by all three tiers via context.
  const [menuAnchor, setMenuAnchor] = useState<HTMLElement | null>(null);
  const [menuTarget, setMenuTarget] = useState<DecisionTarget | null>(null);
  const [decisionVersion, setDecisionVersion] = useState(0);

  const openMenu = useCallback((anchor: HTMLElement, target: DecisionTarget) => {
    setMenuAnchor(anchor);
    setMenuTarget(target);
  }, []);

  const closeMenu = useCallback(() => {
    setMenuAnchor(null);
    setMenuTarget(null);
  }, []);

  const applyDecision = useCallback(
    async (status: SettableStatus, notes: string) => {
      if (!menuTarget) return;
      await recordStorageDecision(selectedCluster, menuTarget.pathPrefixes, status, notes);
      setDecisionVersion((previous) => previous + 1);
    },
    [menuTarget, selectedCluster]
  );

  const decisionContext = useMemo(() => ({ openMenu }), [openMenu]);

  return (
    <Box>
      <Box sx={{ px: 3 }}>
        <Tabs
          value={tabIndex}
          onChange={(_, index: number) => void setTab(TABS[index] ?? ENTITY_TAB)}
          sdsSize="large"
          sx={{ '&.MuiTabs-root': { mt: '0px', mb: '12px' } }}
        >
          {TABS.map((value) => (
            <Tab key={value} label={TAB_LABELS[value]} />
          ))}
        </Tabs>
      </Box>

      {tab === PATHS_TAB ? (
        <DirectoryExplorerView />
      ) : (
        <StorageDecisionContext.Provider value={decisionContext}>
          {!!survey?.stale && (
            <Box sx={{ px: 3, pt: 1.5 }}>
              {/* Wrong numbers with no warning are worse than a missing view. */}
              <Callout
                intent="notice"
                sdsStyle="persistent"
                body="This survey changed after its storage tree was built, so the figures below may be out of date. Re-run rebuild_storage_tree --current to refresh them."
              />
            </Box>
          )}
          <Box sx={{ px: 3 }}>
            <StorageStatsCard
              summary={summary}
              loading={loadingSummary}
              onViewAllPaths={goToAllPaths}
              leading={
                <Box sx={{ flex: '0 0 auto', pt: 0.25 }}>
                  <FormControl size="small" sx={{ minWidth: 130 }}>
                    <InputLabel id="storage-cluster-label">Cluster</InputLabel>
                    <Select
                      labelId="storage-cluster-label"
                      label="Cluster"
                      value={clusters.includes(selectedCluster) ? selectedCluster : ''}
                      onChange={(event) => void setClusterParam(event.target.value || null)}
                    >
                      {clusters.map((option) => (
                        <MenuItem key={option} value={option}>
                          {option}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                  {!!survey && (
                    <Tooltip title={`Survey ${survey.id}`}>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ display: 'block', mt: 0.5, pl: '14px' }}
                      >
                        as of {survey.completedAt ? formatDate(survey.completedAt) : `survey ${survey.id}`}
                      </Typography>
                    </Tooltip>
                  )}
                </Box>
              }
            />
            <StorageSearchBar />
          </Box>

          <FilterableTableMain>
            <Sidebar>
              <EntityTableFilters<StorageFilterId, StorageFilterCategory>
                entityFilterConfigs={STORAGE_FILTER_CONFIGS}
                entityFilterListApi={
                  (cluster
                    ? `${API.STORAGE_SESSIONS_FILTERLIST}?cluster=${encodeURIComponent(cluster)}`
                    : API.STORAGE_SESSIONS_FILTERLIST) as API
                }
              />
            </Sidebar>
            <TableWrapper>
              <GroupTable cluster={cluster} refetchSignal={decisionVersion} />
            </TableWrapper>
          </FilterableTableMain>

          <StatusActionMenu anchor={menuAnchor} target={menuTarget} onClose={closeMenu} onChoose={applyDecision} />
        </StorageDecisionContext.Provider>
      )}
    </Box>
  );
};

export const StorageExplorerView = (): React.JSX.Element => (
  <TableStateProvider
    filterCategories={STORAGE_FILTER_CATEGORIES}
    // Matches table_default_sort in processes/viewsets.py, so the first render
    // agrees with what the server actually sorted by
    initialSortState={[{ desc: true, id: 'size' }]}
  >
    <StorageExplorerLayout />
  </TableStateProvider>
);
