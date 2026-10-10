import { useEffect, useRef, useState } from "react";
import type { Sticker } from "./api";
import { previewTransfer } from "./previewQueue";

export function AnimatedSticker({
  sticker,
  playing = true,
}: {
  sticker: Sticker;
  playing?: boolean;
}) {
  const ref = useRef<HTMLImageElement>(null),
    [source, setSource] = useState(sticker.poster);
  useEffect(() => {
    let active = true;
    let cancel: (() => void) | undefined;
    setSource(sticker.poster);
    if (!playing) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          const bounds = ref.current?.getBoundingClientRect();
          cancel = previewTransfer(
            sticker.motion || sticker.gif,
            () => {
              if (active) setSource(sticker.motion || sticker.gif);
            },
            bounds ? Math.max(0, bounds.top) + bounds.left / 10_000 : 0,
          );
          observer.disconnect();
        }
      },
      { rootMargin: "160px" },
    );
    if (ref.current) observer.observe(ref.current);
    return () => {
      active = false;
      cancel?.();
      observer.disconnect();
    };
  }, [sticker.gif, sticker.motion, sticker.poster, playing]);
  return (
    <img
      ref={ref}
      src={source}
      alt={sticker.label}
      loading="lazy"
      width="240"
      height="240"
    />
  );
}
