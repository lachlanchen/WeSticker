import { useEffect, useRef, useState } from "react";
import type { Sticker } from "./api";

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
    setSource(sticker.poster);
    if (!playing) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          const preload = new Image();
          preload.onload = () => {
            if (active) setSource(sticker.gif);
          };
          preload.src = sticker.gif;
          observer.disconnect();
        }
      },
      { rootMargin: "160px" },
    );
    if (ref.current) observer.observe(ref.current);
    return () => {
      active = false;
      observer.disconnect();
    };
  }, [sticker.gif, sticker.poster, playing]);
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
