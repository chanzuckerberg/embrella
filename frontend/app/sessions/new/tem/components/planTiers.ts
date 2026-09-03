import { PLAN_TIERS, PlanSelection, PlanTier, SessionPlanOption } from '../types';

/**
 * Tiered plan choice. A SessionPlan is a (workflow, scope, software, camera) tuple; users pick
 * one tier at a time and each pick narrows the plans left for the tiers below it.
 *
 *   workflow ─> scope ─> software ─> camera ─> plan
 *
 * A tier with a single remaining option is filled in automatically.
 */

function tiersAbove(tier: PlanTier): PlanTier[] {
  return PLAN_TIERS.slice(0, PLAN_TIERS.indexOf(tier));
}

function tiersBelow(tier: PlanTier): PlanTier[] {
  return PLAN_TIERS.slice(PLAN_TIERS.indexOf(tier) + 1);
}

/** Plans consistent with every tier set in `selection`. */
export function matchingPlans(plans: SessionPlanOption[], selection: PlanSelection): SessionPlanOption[] {
  return plans.filter((plan) => PLAN_TIERS.every((tier) => !selection[tier] || plan[tier] === selection[tier]));
}

/** Distinct values offered at `tier`, given only the tiers above it. */
export function tierOptions(plans: SessionPlanOption[], selection: PlanSelection, tier: PlanTier): string[] {
  const upstream: PlanSelection = {};
  for (const above of tiersAbove(tier)) upstream[above] = selection[above];

  return Array.from(new Set(matchingPlans(plans, upstream).map((plan) => plan[tier])));
}

/** Fill unset tiers from the top while exactly one option remains; stop at the first real choice. */
export function autoFill(plans: SessionPlanOption[], selection: PlanSelection): PlanSelection {
  const filled: PlanSelection = { ...selection };
  for (const tier of PLAN_TIERS) {
    if (filled[tier]) continue;

    const options = tierOptions(plans, filled, tier);
    if (options.length !== 1) break;
    filled[tier] = options[0];
  }
  return filled;
}

/** Apply a pick: tiers below it reset (their options changed), then auto-fill resumes. */
export function pickTier(
  plans: SessionPlanOption[],
  selection: PlanSelection,
  tier: PlanTier,
  value: string | undefined
): PlanSelection {
  const next: PlanSelection = { ...selection, [tier]: value };
  for (const below of tiersBelow(tier)) delete next[below];

  return autoFill(plans, next);
}

/** The plan a complete selection identifies, or null while any tier is open. */
export function resolvePlan(plans: SessionPlanOption[], selection: PlanSelection): SessionPlanOption | null {
  if (!PLAN_TIERS.every((tier) => selection[tier])) return null;

  return matchingPlans(plans, selection)[0] ?? null;
}
