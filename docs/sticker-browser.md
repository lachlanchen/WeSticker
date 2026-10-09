# Compact Sticker Browser

Discover opens the first collection immediately. A vertical collection list
sits between the existing application navigation and the sticker grid. At
1100 px and below, the collection list becomes horizontal to leave room for
the stickers. Mobile keeps the existing collapsible application menu.

Search and theme filters choose the first matching collection if the previous
selection is hidden. Three lettering languages, collection favorites, previews,
individual GIF downloads, and account-gated collection downloads are preserved.

Visible stickers autoplay. The playback button switches to static posters;
the setting survives collection/language changes. Reduced-motion users start
paused and can explicitly play. Late image loads cannot restart paused GIFs.

Implementation: `src/StickerBrowser.tsx`, `src/AnimatedSticker.tsx`, and the
scoped browser styles in `src/style.css`. The browser test covers initial
visibility, playback, filtering, downloads, favorites, reduced motion, and
320/390/768/1024/1200/1440 px layouts, then the existing creator workflow.

AYA's shop has the corresponding layout, with its independent checkout and
11-language interface. No AYA orders or WeChat submissions are modified.
