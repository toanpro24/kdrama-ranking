import { useRef, useCallback, useEffect } from "react";

const LONG_PRESS_MS = 400;
const DRAG_THRESHOLD = 8; // px before we consider it a drag vs a tap

export interface TouchDragCallbacks {
  onDrop: (actressId: string, targetTier: string | null) => void;
  onDragOverTier: (tierId: string | null) => void;
}

/**
 * Custom touch drag-and-drop for mobile.
 * Long-press on a card to pick it up, drag to a tier row, release to drop.
 */
export function useTouchDrag(callbacks: TouchDragCallbacks) {
  const dragging = useRef(false);
  const dragActressId = useRef<string | null>(null);
  const ghostEl = useRef<HTMLElement | null>(null);
  const longPressTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const startPos = useRef({ x: 0, y: 0 });
  const sourceEl = useRef<HTMLElement | null>(null);

  const cleanup = useCallback(() => {
    dragging.current = false;
    dragActressId.current = null;
    clearTimeout(longPressTimer.current);
    if (ghostEl.current) {
      ghostEl.current.remove();
      ghostEl.current = null;
    }
    if (sourceEl.current) {
      sourceEl.current.style.opacity = "";
      sourceEl.current = null;
    }
    callbacks.onDragOverTier(null);
    document.body.style.overflow = "";
  }, [callbacks]);

  // Find which tier row or unranked section is under the touch point
  const findDropTarget = useCallback((x: number, y: number): string | null | undefined => {
    const els = document.elementsFromPoint(x, y);
    for (const el of els) {
      const tierRow = (el as HTMLElement).closest<HTMLElement>("[data-tier-id]");
      if (tierRow) {
        const tierId = tierRow.dataset.tierId;
        return tierId === "unranked" ? null : (tierId ?? undefined);
      }
    }
    return undefined; // not over any drop target
  }, []);

  const handleTouchStart = useCallback((e: React.TouchEvent, actressId: string) => {
    const touch = e.touches[0];
    startPos.current = { x: touch.clientX, y: touch.clientY };
    const card = (e.target as HTMLElement).closest<HTMLElement>(".actress-card");
    if (!card) return;

    longPressTimer.current = setTimeout(() => {
      dragging.current = true;
      dragActressId.current = actressId;
      sourceEl.current = card;

      // Prevent scrolling while dragging
      document.body.style.overflow = "hidden";

      // Dim the source card
      card.style.opacity = "0.4";

      // Create ghost element
      const rect = card.getBoundingClientRect();
      const ghost = card.cloneNode(true) as HTMLElement;
      ghost.style.position = "fixed";
      ghost.style.left = `${rect.left}px`;
      ghost.style.top = `${rect.top}px`;
      ghost.style.width = `${rect.width}px`;
      ghost.style.zIndex = "10000";
      ghost.style.pointerEvents = "none";
      ghost.style.transform = "scale(1.08)";
      ghost.style.boxShadow = "0 16px 48px rgba(0,0,0,0.5), 0 0 0 2px rgba(229,0,164,0.4)";
      ghost.style.borderRadius = "14px";
      ghost.style.opacity = "0.95";
      ghost.style.transition = "transform 0.15s ease";
      ghost.classList.add("touch-drag-ghost");
      document.body.appendChild(ghost);
      ghostEl.current = ghost;

      // Haptic feedback if available
      if (navigator.vibrate) navigator.vibrate(30);
    }, LONG_PRESS_MS);
  }, []);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    const touch = e.touches[0];
    const dx = touch.clientX - startPos.current.x;
    const dy = touch.clientY - startPos.current.y;

    // Cancel long-press if finger moves too much before activation
    if (!dragging.current && (Math.abs(dx) > DRAG_THRESHOLD || Math.abs(dy) > DRAG_THRESHOLD)) {
      clearTimeout(longPressTimer.current);
      return;
    }

    if (!dragging.current || !ghostEl.current) return;

    e.preventDefault(); // prevent scroll

    // Move ghost to follow finger
    const ghost = ghostEl.current;
    const w = parseFloat(ghost.style.width);
    ghost.style.left = `${touch.clientX - w / 2}px`;
    ghost.style.top = `${touch.clientY - 40}px`;

    // Auto-scroll near edges
    const edgeSize = 80;
    if (touch.clientY < edgeSize) {
      window.scrollBy(0, -8);
    } else if (touch.clientY > window.innerHeight - edgeSize) {
      window.scrollBy(0, 8);
    }

    // Highlight drop target
    const target = findDropTarget(touch.clientX, touch.clientY);
    if (target !== undefined) {
      callbacks.onDragOverTier(target === null ? "unranked" : target);
    } else {
      callbacks.onDragOverTier(null);
    }
  }, [findDropTarget, callbacks]);

  const handleTouchEnd = useCallback(() => {
    clearTimeout(longPressTimer.current);

    if (dragging.current && dragActressId.current && ghostEl.current) {
      // Find where the ghost is centered
      const ghost = ghostEl.current;
      const ghostRect = ghost.getBoundingClientRect();
      const cx = ghostRect.left + ghostRect.width / 2;
      const cy = ghostRect.top + ghostRect.height / 2;

      const target = findDropTarget(cx, cy);
      if (target !== undefined) {
        callbacks.onDrop(dragActressId.current, target);
      }
    }

    cleanup();
  }, [findDropTarget, callbacks, cleanup]);

  // Clean up on unmount
  useEffect(() => {
    return cleanup;
  }, [cleanup]);

  return { handleTouchStart, handleTouchMove, handleTouchEnd, isDragging: dragging };
}
