'use client';

import { useCallback, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { createSession, fetchFormOptions, fetchMagnifications, fetchSuggestedName } from '../services/sessionApi';
import {
  CreatedSession,
  FormOptions,
  MagnificationOption,
  PLAN_TIERS,
  PlanSelection,
  PlanTier,
  SessionFormState,
  SessionPlanOption,
} from '../types';
import { autoFill, pickTier, resolvePlan, tierOptions } from './planTiers';

const NAME_REGEX = /[@_!#$%^&*()<>?/\\|}{~:\s]/;
const MAX_NAME_LENGTH = 20;
const STALE = 5 * 60 * 1000;

const keys = {
  formOptions: ['tem', 'session-form', 'options'] as const,
  magnifications: (planId: number | null) => ['tem', 'session-form', 'magnifications', planId] as const,
  suggestedName: (planId: number | null) => ['tem', 'session-form', 'suggested-name', planId] as const,
};

const NO_MAGNIFICATIONS: MagnificationOption[] = [];

interface UseSessionFormReturn {
  state: SessionFormState;
  formOptions: FormOptions | null;
  magnifications: MagnificationOption[];
  suggestedName: string;
  errors: Record<string, string>;
  isLoading: boolean;
  isSubmitting: boolean;
  /** Tiered plan choice: what is picked so far, and what each tier currently offers. */
  planSelection: PlanSelection;
  planTierOptions: Record<PlanTier, string[]>;
  updateField: <K extends keyof SessionFormState>(field: K, value: SessionFormState[K]) => void;
  selectPlanTier: (tier: PlanTier, value: string | undefined) => void;
  selectSessionPlan: (sessionPlanId: number | null) => void;
  submit: () => Promise<CreatedSession | null>;
}

/**
 * Server data is declared with React Query, keyed on the form state it depends on:
 *
 *   sessionPlanId -> magnifications
 *   sessionPlanId -> suggested name   (applied to the field only while it is untouched)
 *
 * Handlers only change state; the queries follow. The few "react to arriving data" steps are
 * done during render with the previous-value pattern, so there are no effects.
 */
export function useSessionForm(): UseSessionFormReturn {
  const [state, setState] = useState<SessionFormState>({
    sessionPlanId: null,
    projectId: null,
    gridId: null,
    magnificationId: null,
    name: '',
    superResolution: false,
    phasePlateUsed: false,
    energyFilterUsed: true,
  });
  const [planSelection, setPlanSelection] = useState<PlanSelection>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const optionsQuery = useQuery({ queryKey: keys.formOptions, queryFn: fetchFormOptions, staleTime: STALE });
  const magnificationsQuery = useQuery({
    queryKey: keys.magnifications(state.sessionPlanId),
    queryFn: () => fetchMagnifications(state.sessionPlanId as number),
    enabled: state.sessionPlanId !== null,
    staleTime: STALE,
  });
  const nameQuery = useQuery({
    queryKey: keys.suggestedName(state.sessionPlanId),
    queryFn: () => fetchSuggestedName(state.sessionPlanId),
  });

  const plans = useMemo(() => optionsQuery.data?.session_plans ?? [], [optionsQuery.data]);
  const magnifications =
    state.sessionPlanId !== null ? (magnificationsQuery.data ?? NO_MAGNIFICATIONS) : NO_MAGNIFICATIONS;

  // Apply a newly suggested name only while the field is empty or still shows the previous
  // suggestion. Keyed on plan + value so the same text for a new plan still re-applies.
  const suggested = nameQuery.data ?? null;
  const suggestionKey = suggested === null ? null : `${state.sessionPlanId}:${suggested}`;
  const [applied, setApplied] = useState<{ key: string | null; name: string }>({ key: null, name: '' });
  if (suggestionKey !== null && suggestionKey !== applied.key) {
    const previous = applied.name;
    setApplied({ key: suggestionKey, name: suggested as string });
    setState((prev) => (prev.name === '' || prev.name === previous ? { ...prev, name: suggested as string } : prev));
  }

  const clearError = useCallback((field: string) => {
    setErrors((prev) => {
      if (!prev[field]) return prev;
      const next = { ...prev };
      delete next[field];
      return next;
    });
  }, []);

  const updateField = useCallback(
    <K extends keyof SessionFormState>(field: K, value: SessionFormState[K]) => {
      setState((prev) => ({ ...prev, [field]: value }));
      clearError(field);
    },
    [clearError]
  );

  const selectSessionPlan = useCallback(
    (sessionPlanId: number | null) => {
      // The magnification list belongs to the old plan; Acquisition settings restart from the new plan's profile.
      const plan = plans.find((p) => p.id === sessionPlanId);
      const defaults = plan?.acquisition_defaults;
      const superResolution = defaults?.super_resolution ?? false;
      const phasePlateUsed = defaults?.phase_plate_used ?? false;
      const energyFilterUsed = defaults?.energy_filter_used ?? true;
      setState((prev) => ({
        ...prev,
        sessionPlanId,
        magnificationId: null,
        superResolution,
        phasePlateUsed,
        energyFilterUsed,
      }));
      clearError('sessionPlanId');
    },
    [plans, clearError]
  );

  const planTierOptions = useMemo(
    () =>
      Object.fromEntries(PLAN_TIERS.map((tier) => [tier, tierOptions(plans, planSelection, tier)])) as Record<
        PlanTier,
        string[]
      >,
    [plans, planSelection]
  );

  const applyPlanSelection = useCallback(
    (availablePlans: SessionPlanOption[], selection: PlanSelection) => {
      setPlanSelection(selection);
      selectSessionPlan(resolvePlan(availablePlans, selection)?.id ?? null);
    },
    [selectSessionPlan]
  );

  // Once the plans are known, pre-fill the tiers that have a single option. Only ever once,
  // so a background refetch cannot undo what the user has picked since.
  const [tiersInitialised, setTiersInitialised] = useState(false);
  if (!tiersInitialised && optionsQuery.data) {
    setTiersInitialised(true);
    applyPlanSelection(plans, autoFill(plans, {}));
  }

  const selectPlanTier = useCallback(
    (tier: PlanTier, value: string | undefined) => {
      applyPlanSelection(plans, pickTier(plans, planSelection, tier, value));
    },
    [plans, planSelection, applyPlanSelection]
  );

  const validate = useCallback((): boolean => {
    const newErrors: Record<string, string> = {};

    if (!state.sessionPlanId) newErrors.sessionPlanId = 'Session plan is required.';
    if (!state.projectId) newErrors.projectId = 'Project is required.';
    if (!state.gridId) newErrors.gridId = 'Grid is required.';
    if (!state.magnificationId && magnifications.length > 0) newErrors.magnificationId = 'Magnification is required.';

    if (!state.name.trim()) {
      newErrors.name = 'Session name is required.';
    } else if (NAME_REGEX.test(state.name)) {
      newErrors.name = 'Name cannot contain special characters or spaces.';
    } else if (state.name.length > MAX_NAME_LENGTH) {
      newErrors.name = `Name must be ${MAX_NAME_LENGTH} characters or fewer.`;
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [state, magnifications.length]);

  const submit = useCallback(async (): Promise<CreatedSession | null> => {
    if (!validate()) return null;

    setIsSubmitting(true);
    setErrors({});

    try {
      const res = await createSession({
        name: state.name.trim(),
        session_plan_id: state.sessionPlanId,
        project_id: state.projectId,
        grid_id: state.gridId,
        // might not have any magnification options, so this is optional
        ...(state.magnificationId ? { magnification_id: state.magnificationId } : {}),
        super_resolution: state.superResolution,
        phase_plate_used: state.phasePlateUsed,
        energy_filter_used: state.energyFilterUsed,
      });

      if (res.ok) {
        return (await res.json()) as CreatedSession;
      }

      // Handle validation errors from server
      const errorData = await res.json();
      const serverErrors: Record<string, string> = {};
      for (const [field, msgs] of Object.entries(errorData)) {
        if (Array.isArray(msgs)) {
          serverErrors[field] = msgs.join(', ');
        } else if (typeof msgs === 'string') {
          serverErrors[field] = msgs;
        }
      }
      setErrors(serverErrors);
      return null;
    } catch {
      setErrors({ submit: 'An error occurred. Please try again.' });
      return null;
    } finally {
      setIsSubmitting(false);
    }
  }, [state, validate]);

  const isLoading = optionsQuery.isPending;
  const formOptions = optionsQuery.data ?? null;
  const suggestedName = applied.name;

  return useMemo(
    () => ({
      state,
      formOptions,
      magnifications,
      suggestedName,
      errors,
      isLoading,
      isSubmitting,
      planSelection,
      planTierOptions,
      updateField,
      selectPlanTier,
      selectSessionPlan,
      submit,
    }),
    [
      state,
      formOptions,
      magnifications,
      suggestedName,
      errors,
      isLoading,
      isSubmitting,
      planSelection,
      planTierOptions,
      updateField,
      selectPlanTier,
      selectSessionPlan,
      submit,
    ]
  );
}
