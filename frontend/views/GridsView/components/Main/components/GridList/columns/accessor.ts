import { GridData } from "@/app/common/types/types";
import { formatDate } from "@/views/common/date/utils";
import { LinkTValue } from "@/app/components/Table/components/CellComponent/types";

/**
 * Cryogrid accessor function.
 * @param originalRow - Original row data.
 * @returns model to be used as props for the Link component.
 */
export function getCryogridAccessorFn(originalRow: GridData): LinkTValue {
  const {
    grid: { name, url },
  } = originalRow;
  return {
    children: name,
    href: url,
  };
}

/**
 * Freezing plan accessor function.
 * @param originalRow - Original row data.
 * @returns model to be used as props for the Links component.
 */
export function getFreezingPlanAccessorFn(originalRow: GridData): LinkTValue[] {
  const {
    freezingPlan: { sample },
  } = originalRow;
  return sample.map(({ name, url }) => ({
    children: name,
    href: url,
  }));
}

/**
 * Freezing session accessor function.
 * @param originalRow - Original row data.
 * @returns string value.
 */
export function getFreezingSessionAccessorFn(originalRow: GridData): string {
  return formatDate(originalRow.freezingSession.createdAt);
}

/**
 * MSI accessor function.
 * @param originalRow - Original row data.
 * @returns model to be used as props for the Links component.
 */
export function getMSIAccessorFn(originalRow: GridData): LinkTValue[] {
  const { msiSession } = originalRow;
  return msiSession.map(({ name, url }) => ({
    children: name,
    href: url,
  }));
}

/**
 * Project accessor function.
 * @param originalRow - Original row data.
 * @returns model to be used as props for the Link component.
 */
export function getProjectAccessorFn(originalRow: GridData): LinkTValue {
  const {
    project: { name, url },
  } = originalRow;
  return {
    children: name,
    href: url,
  };
}

/**
 * Updated at accessor function.
 * @param originalRow - Original row data.
 * @returns string value.
 */
export function getUpdatedAtAccessorFn(originalRow: GridData): string {
  const {
    grid: { updatedAt },
  } = originalRow;
  if (!updatedAt) return "-";
  return formatDate(updatedAt);
}
