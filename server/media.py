"""Deterministic photo lettering and packaging, never mislabeled as AI animation."""

import io

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageSequence


def font(config, size):
    name = config.get("font", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    return ImageFont.truetype(name, size)


def sticker_png(source, label, config):
    with Image.open(source) as raw:
        image = ImageOps.exif_transpose(raw).convert("RGBA")
        image.thumbnail((228, 190), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (240, 240), (0, 0, 0, 0))
        canvas.alpha_composite(
            image, ((240 - image.width) // 2, 4 + (190 - image.height) // 2)
        )
    draw = ImageDraw.Draw(canvas)
    size = 27
    while (
        size > 12
        and draw.textbbox((0, 0), label, font=font(config, size), stroke_width=2)[2]
        > 225
    ):
        size -= 1
    draw.text(
        (120, 215),
        label,
        font=font(config, size),
        anchor="mm",
        fill="white",
        stroke_width=2,
        stroke_fill="#352b3f",
    )
    out = io.BytesIO()
    canvas.save(out, "PNG", optimize=True)
    return out.getvalue()


def packaging(images, title, config):
    pieces = [Image.open(io.BytesIO(x)).convert("RGBA") for x in images]
    result = {}
    for name, size in [
        ("cover.png", (240, 240)),
        ("icon.png", (50, 50)),
        ("banner.jpg", (750, 400)),
        ("thanks.png", (750, 750)),
    ]:
        if name in {"cover.png", "icon.png"}:
            canvas = ImageOps.contain(pieces[0], size, Image.Resampling.LANCZOS)
        else:
            canvas = Image.new("RGBA", size, "#fff1f6")
            for index, piece in enumerate(pieces[:3]):
                piece = piece.resize((220, 220), Image.Resampling.LANCZOS)
                canvas.alpha_composite(piece, (35 + index * 230, (size[1] - 220) // 2))
        out = io.BytesIO()
        if name.endswith(".jpg"):
            canvas.convert("RGB").save(out, "JPEG", quality=90)
        else:
            canvas.save(out, "PNG", optimize=True)
        result[name] = out.getvalue()
    return result


def sticker_gif(source, label, config):
    frames = []
    durations = []
    with Image.open(source) as raw:
        if getattr(raw, "n_frames", 1) > 180:
            raise ValueError("Animation exceeds the short-sticker limit.")
        for frame in ImageSequence.Iterator(raw):
            png = io.BytesIO()
            frame.convert("RGBA").save(png, "PNG")
            png.seek(0)
            frames.append(
                Image.open(io.BytesIO(sticker_png(png, label, config))).convert("RGBA")
            )
            durations.append(max(20, frame.info.get("duration", 80)))
    if sum(durations) > 12000:
        raise ValueError("Animation exceeds 12 seconds.")
    for colors in (128, 96, 64):
        out = io.BytesIO()
        converted = [
            frame.convert("P", palette=Image.Palette.ADAPTIVE, colors=colors)
            for frame in frames
        ]
        converted[0].save(
            out,
            "GIF",
            save_all=True,
            append_images=converted[1:],
            duration=durations,
            loop=0,
            disposal=2,
            optimize=True,
        )
        if out.tell() <= 500_000:
            return out.getvalue()
    raise ValueError(
        "GIF is too large. Preserve the original and review its animation before export."
    )
