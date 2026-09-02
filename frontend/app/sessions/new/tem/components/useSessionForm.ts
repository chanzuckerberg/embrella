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
  const suggestedNameRef = useRef('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Fetch form options + suggested name + users on mount
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
          suggestedNameRef.current = suggested;
          setSuggestedName(suggested);
          setState((prev) => ({ ...prev, name: suggested }));
        }

        if (usersRes.ok) {
          const data = await usersRes.json();
          const userList = data.users || data.results || data;
          setUsers(userList);

          // Pre-select current user for grid filtering
          if (user?.id) {
            setState((prev) => ({ ...prev, filterUserId: Number(user.id) }));
          }
        }
      } catch (err) {
        console.error('Failed to load form options:', err);
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, [user?.id]);

  // Fetch grids when filterUserId changes
  useEffect(() => {
    const loadGrids = async () => {
      const url = state.filterUserId
        ? `${DJANGO_URL}${TEM_API.GRIDS_BY_USER}?user_id=${state.filterUserId}`
        : `${DJANGO_URL}${TEM_API.GRIDS_BY_USER}`;

      try {
        const res = await fetchResource(url);
        if (res.ok) {
          const data: GridOption[] = await res.json();
          setGrids(data);

          // Auto-select default grid if available
          const defaultGrid = data.find((g) => g.is_default);
          if (defaultGrid) {
            setState((prev) => ({ ...prev, gridId: defaultGrid.id }));
          } else {
            setState((prev) => ({ ...prev, gridId: null }));
          }
        }
      } catch (err) {
        console.error('Failed to load grids:', err);
      }
    };
    loadGrids();
  }, [state.filterUserId]);

  // Reset the magnification selection when the session plan changes.
  const [prevSessionPlanId, setPrevSessionPlanId] = useState(state.sessionPlanId);
  if (state.sessionPlanId !== prevSessionPlanId) {
    setPrevSessionPlanId(state.sessionPlanId);
    setState((prev) => ({ ...prev, magnificationId: null }));
    if (!state.sessionPlanId) {
      setMagnifications([]);
    }
  }

  // Fetch magnifications when sessionPlanId changes
  useEffect(() => {
    if (!state.sessionPlanId) {
      return;
    }

    const loadMags = async () => {
      try {
        const res = await fetchResource(
          `${DJANGO_URL}${TEM_API.MAGNIFICATIONS}?session_plan_id=${state.sessionPlanId}`
        );
        if (res.ok) {
          const data: MagnificationOption[] = await res.json();
          setMagnifications(data);
        }
      } catch (err) {
        console.error('Failed to load magnifications:', err);
      }
    };
    loadMags();
  }, [state.sessionPlanId]);

  // Re-suggest the name when the plan changes
  useEffect(() => {
    if (!state.sessionPlanId) {
      return;
    }

    let stale = false;
    const reSuggest = async () => {
      try {
        const suggested = await fetchSuggestedName(state.sessionPlanId);
        if (stale || suggested === null) return;

        const previous = suggestedNameRef.current;
        suggestedNameRef.current = suggested;
        setSuggestedName(suggested);
        setState((prev) => (prev.name === '' || prev.name === previous ? { ...prev, name: suggested } : prev));
      } catch (err) {
        console.error('Failed to load suggested name:', err);
      }
    };
    reSuggest();

    // A slower response for an earlier plan must not overwrite the current one.
    return () => {
      stale = true;
    };
  }, [state.sessionPlanId]);

  const updateField = useCallback(<K extends keyof SessionFormState>(field: K, value: SessionFormState[K]) => {
    setState((prev) => ({ ...prev, [field]: value }));
    // Clear error for this field when user changes it
    setErrors((prev) => {
      if (prev[field]) {
        const next = { ...prev };
        delete next[field];
        return next;
      }
      return prev;
    });
  }, []);

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
      submit,
    ]
  );
}
