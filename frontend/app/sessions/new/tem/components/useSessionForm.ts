'use client';

import { useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { DJANGO_URL } from '@app/common/constants/api';
import { fetchResource, postResource } from '@app/common/queries/fetchResource';
import { UserContext } from '@app/common/context/UserProvider';
import { CreatedSession, FormOptions, GridOption, MagnificationOption, SessionFormState, UserOption } from '../types';
import { TEM_API } from '../constants';

const NAME_REGEX = /[@_!#$%^&*()<>?/\\|}{~:\s]/;

/** The server's suggested name, prefixed per plan when one is given (e.g. s26jun08a). */
async function fetchSuggestedName(sessionPlanId: number | null): Promise<string | null> {
  const query = sessionPlanId ? `?session_plan_id=${sessionPlanId}` : '';
  const res = await fetchResource(`${DJANGO_URL}${TEM_API.SUGGEST_NAME}${query}`);
  if (!res.ok) return null;
  const { suggested_name } = await res.json();
  return suggested_name;
}

function useLatestRequest() {
  const counter = useRef(0);
  const next = useCallback(() => ++counter.current, []);
  const isLatest = useCallback((token: number) => token === counter.current, []);
  return useMemo(() => ({ next, isLatest }), [next, isLatest]);
}

interface UseSessionFormReturn {
  state: SessionFormState;
  formOptions: FormOptions | null;
  users: UserOption[];
  grids: GridOption[];
  magnifications: MagnificationOption[];
  suggestedName: string;
  errors: Record<string, string>;
  isLoading: boolean;
  isSubmitting: boolean;
  updateField: <K extends keyof SessionFormState>(field: K, value: SessionFormState[K]) => void;
  selectSessionPlan: (sessionPlanId: number | null) => void;
  selectFilterUser: (userId: number | null) => void;
  submit: () => Promise<CreatedSession | null>;
}

export function useSessionForm(): UseSessionFormReturn {
  const user = useContext(UserContext);

  const [state, setState] = useState<SessionFormState>({
    sessionPlanId: null,
    projectId: null,
    gridId: null,
    magnificationId: null,
    name: '',
    filterUserId: null,
  });

  const [formOptions, setFormOptions] = useState<FormOptions | null>(null);
  const [users, setUsers] = useState<UserOption[]>([]);
  const [grids, setGrids] = useState<GridOption[]>([]);
  const [magnifications, setMagnifications] = useState<MagnificationOption[]>([]);
  const [suggestedName, setSuggestedName] = useState('');
  // Mirror of suggestedName readable from async handlers without re-creating them.
  const suggestedNameRef = useRef('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const gridsRequest = useLatestRequest();
  const magnificationsRequest = useLatestRequest();
  const nameRequest = useLatestRequest();

  const applySuggestedName = useCallback((suggested: string) => {
    const previous = suggestedNameRef.current;
    suggestedNameRef.current = suggested;
    setSuggestedName(suggested);
    // Only replace a name the user hasn't touched: empty, or still the previous suggestion.
    setState((prev) => (prev.name === '' || prev.name === previous ? { ...prev, name: suggested } : prev));
  }, []);

  const loadGrids = useCallback(
    async (userId: number | null) => {
      const token = gridsRequest.next();
      const url = userId
        ? `${DJANGO_URL}${TEM_API.GRIDS_BY_USER}?user_id=${userId}`
        : `${DJANGO_URL}${TEM_API.GRIDS_BY_USER}`;

      try {
        const res = await fetchResource(url);
        if (!res.ok) return;
        const data: GridOption[] = await res.json();
        if (!gridsRequest.isLatest(token)) return;

        setGrids(data);
        const defaultGrid = data.find((g) => g.is_default);
        setState((prev) => ({ ...prev, gridId: defaultGrid?.id ?? null }));
      } catch (err) {
        console.error('Failed to load grids:', err);
      }
    },
    [gridsRequest]
  );

  const loadMagnifications = useCallback(
    async (sessionPlanId: number) => {
      const token = magnificationsRequest.next();

      try {
        const res = await fetchResource(`${DJANGO_URL}${TEM_API.MAGNIFICATIONS}?session_plan_id=${sessionPlanId}`);
        if (!res.ok) return;
        const data: MagnificationOption[] = await res.json();
        if (magnificationsRequest.isLatest(token)) setMagnifications(data);
      } catch (err) {
        console.error('Failed to load magnifications:', err);
      }
    },
    [magnificationsRequest]
  );

  const loadSuggestedName = useCallback(
    async (sessionPlanId: number) => {
      const token = nameRequest.next();

      try {
        const suggested = await fetchSuggestedName(sessionPlanId);
        if (suggested !== null && nameRequest.isLatest(token)) applySuggestedName(suggested);
      } catch (err) {
        console.error('Failed to load suggested name:', err);
      }
    },
    [nameRequest, applySuggestedName]
  );

  // Initial load: options, users, an unprefixed name, and the grids of the current user.
  useEffect(() => {
    const load = async () => {
      try {
        const [optionsRes, suggested, usersRes] = await Promise.all([
          fetchResource(`${DJANGO_URL}${TEM_API.FORM_OPTIONS}`),
          fetchSuggestedName(null),
          fetchResource(`${DJANGO_URL}${TEM_API.USERS}`),
        ]);

        if (optionsRes.ok) {
          const options: FormOptions = await optionsRes.json();
          setFormOptions(options);
        }

        if (suggested !== null) {
          applySuggestedName(suggested);
        }

        if (usersRes.ok) {
          const data = await usersRes.json();
          setUsers(data.users || data.results || data);
        }

        // Pre-select the current user for grid filtering
        const filterUserId = user?.id ? Number(user.id) : null;
        setState((prev) => ({ ...prev, filterUserId }));
        await loadGrids(filterUserId);
      } catch (err) {
        console.error('Failed to load form options:', err);
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, [user?.id, applySuggestedName, loadGrids]);

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

  const selectFilterUser = useCallback(
    (userId: number | null) => {
      setState((prev) => ({ ...prev, filterUserId: userId }));
      loadGrids(userId);
    },
    [loadGrids]
  );

  const selectSessionPlan = useCallback(
    (sessionPlanId: number | null) => {
      // The magnification list belongs to the old plan.
      setState((prev) => ({ ...prev, sessionPlanId, magnificationId: null }));
      clearError('sessionPlanId');

      if (!sessionPlanId) {
        setMagnifications([]);
        return;
      }
      loadMagnifications(sessionPlanId);
      loadSuggestedName(sessionPlanId);
    },
    [clearError, loadMagnifications, loadSuggestedName]
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
    } else if (state.name.length > 20) {
      newErrors.name = 'Name must be 20 characters or fewer.';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [state, magnifications.length]);

  const submit = useCallback(async (): Promise<CreatedSession | null> => {
    if (!validate()) return null;

    setIsSubmitting(true);
    setErrors({});

    try {
      const payload: Record<string, unknown> = {
        name: state.name.trim(),
        session_plan_id: state.sessionPlanId,
        project_id: state.projectId,
        grid_id: state.gridId,
      };
      // might not have any magnification options, so this is optional
      if (state.magnificationId) {
        payload.magnification_id = state.magnificationId;
      }

      const res = await postResource(`${DJANGO_URL}${TEM_API.CREATE_SESSION}`, payload);

      if (res.ok) {
        const session: CreatedSession = await res.json();
        return session;
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

  return useMemo(
    () => ({
      state,
      formOptions,
      users,
      grids,
      magnifications,
      suggestedName,
      errors,
      isLoading,
      isSubmitting,
      updateField,
      selectSessionPlan,
      selectFilterUser,
      submit,
    }),
    [
      state,
      formOptions,
      users,
      grids,
      magnifications,
      suggestedName,
      errors,
      isLoading,
      isSubmitting,
      updateField,
      selectSessionPlan,
      selectFilterUser,
      submit,
    ]
  );
}
