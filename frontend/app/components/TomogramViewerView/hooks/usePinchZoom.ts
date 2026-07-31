import { RefObject, useEffect } from 'react';

/**
 * Idetik's camera controls only ever track a single pointer — `onPointerDown/Move/End`
 * drive a pan, and zoom is reachable only through `onWheel`. A trackpad pinch arrives
 * as a wheel event so it zooms, but a touchscreen pinch arrives as two pointer streams:
 * the first one pans and the second is ignored.
 *
 * This bridges the gap by measuring the pinch ourselves and replaying it as the wheel
 * events Idetik already understands, anchored on the pinch midpoint (it reads
 * `clientX`/`clientY` off the event to pick the zoom centre).
 *
 * Requires `touch-action: none` on the container, or the browser consumes the gesture
 * before we ever see the second pointer.
 */

/** Idetik zooms by this fixed factor per wheel event, regardless of `deltaY` magnitude. */
const ZOOM_FACTOR_PER_WHEEL_EVENT = 1.05;

/** Guards against one large finger movement firing a burst of zoom steps. */
const MAX_STEPS_PER_MOVE = 8;

export const usePinchZoom = (containerRef: RefObject<HTMLElement | null>) => {
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const activePointers = new Map<number, { x: number; y: number }>();
    let isPinching = false;
    let lastDistance = 0;

    const distanceBetweenPointers = () => {
      const [a, b] = [...activePointers.values()];
      return Math.hypot(a.x - b.x, a.y - b.y);
    };

    const midpointBetweenPointers = () => {
      const [a, b] = [...activePointers.values()];
      return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
    };

    const zoom = (steps: number, at: { x: number; y: number }) => {
      const canvas = container.querySelector('canvas');
      if (!canvas) return;
      for (let i = 0; i < Math.abs(steps); i++) {
        canvas.dispatchEvent(
          new WheelEvent('wheel', {
            // Idetik reads only the sign: negative zooms in.
            deltaY: steps > 0 ? -1 : 1,
            clientX: at.x,
            clientY: at.y,
            bubbles: true,
            cancelable: true,
          })
        );
      }
    };

    /**
     * Idetik began a single-pointer pan on the first finger and is holding pointer
     * capture. Hand it a pointerup so it stops panning for the rest of the gesture.
     */
    const cancelIdetikPan = (pointerId: number, at: { x: number; y: number }) => {
      const canvas = container.querySelector('canvas');
      canvas?.dispatchEvent(
        new PointerEvent('pointerup', {
          pointerId,
          clientX: at.x,
          clientY: at.y,
          button: 0,
          bubbles: true,
          cancelable: true,
        })
      );
    };

    const onPointerDown = (event: PointerEvent) => {
      // Ignore the pointerup/wheel events this hook dispatches itself.
      if (!event.isTrusted || event.pointerType !== 'touch') return;
      activePointers.set(event.pointerId, { x: event.clientX, y: event.clientY });

      if (activePointers.size === 2 && !isPinching) {
        isPinching = true;
        lastDistance = distanceBetweenPointers();
        const [firstPointerId] = [...activePointers.keys()];
        cancelIdetikPan(firstPointerId, midpointBetweenPointers());
      }
      if (isPinching) event.stopPropagation();
    };

    const onPointerMove = (event: PointerEvent) => {
      if (!event.isTrusted || event.pointerType !== 'touch') return;
      if (!activePointers.has(event.pointerId)) return;
      activePointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
      if (!isPinching) return;

      // Suppress the pan Idetik would otherwise apply from the leading finger.
      event.stopPropagation();
      if (event.cancelable) event.preventDefault();

      if (activePointers.size < 2 || lastDistance <= 0) return;
      const distance = distanceBetweenPointers();
      const steps = Math.round(Math.log(distance / lastDistance) / Math.log(ZOOM_FACTOR_PER_WHEEL_EVENT));
      if (steps === 0) return; // Below one zoom step; keep accumulating against the same baseline.

      zoom(Math.max(-MAX_STEPS_PER_MOVE, Math.min(MAX_STEPS_PER_MOVE, steps)), midpointBetweenPointers());
      lastDistance = distance;
    };

    const onPointerEnd = (event: PointerEvent) => {
      if (!event.isTrusted || event.pointerType !== 'touch') return;
      activePointers.delete(event.pointerId);
      if (!isPinching) return;
      // Stay in pinch mode until every finger is up, so a leftover finger does not
      // resume panning from a stale drag origin.
      event.stopPropagation();
      if (activePointers.size === 0) {
        isPinching = false;
        lastDistance = 0;
      }
    };

    const options = { capture: true, passive: false } as const;
    container.addEventListener('pointerdown', onPointerDown, options);
    container.addEventListener('pointermove', onPointerMove, options);
    container.addEventListener('pointerup', onPointerEnd, options);
    container.addEventListener('pointercancel', onPointerEnd, options);
    return () => {
      container.removeEventListener('pointerdown', onPointerDown, options);
      container.removeEventListener('pointermove', onPointerMove, options);
      container.removeEventListener('pointerup', onPointerEnd, options);
      container.removeEventListener('pointercancel', onPointerEnd, options);
    };
  }, [containerRef]);
};
