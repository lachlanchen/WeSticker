import { useEffect, useRef, useState } from "react";
import type { Sticker } from "./api";

export function AnimatedSticker({ sticker }: { sticker: Sticker }) {
  const ref = useRef<HTMLImageElement>(null),
    [source, setSource] = useState(sticker.poster);
  useEffect(() => {
    let active = true;
    setSource(sticker.poster);
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          const preload = new Image();
          preload.src = sticker.gif;
          preload.onload = () => {
            if (active) setSource(sticker.gif);
          };
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
  }, [sticker.gif, sticker.poster]);
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
