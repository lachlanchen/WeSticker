"""Convert an approved Japanese GIF pack to a separately reviewed LINE APNG edition.

Originals are read-only. Output is a new directory, never an existing submission.
LINE animation limits verified 2026-10-10: 8/16/24, <=20 frames, <=4 seconds,
PNG/APNG <=1 MB, transparent, <=320x270 with one dimension >=270.
"""
import argparse
import hashlib
import html
import json
from pathlib import Path
from urllib.parse import urlparse
import zipfile

from PIL import Image, ImageChops, ImageDraw


def exterior_alpha(image):
    """Remove only near-white pixels connected to the image perimeter."""
    result = image.convert("RGBA")
    r, g, b, alpha = result.split()
    low = ImageChops.darker(ImageChops.darker(r, g), b)
    high = ImageChops.lighter(ImageChops.lighter(r, g), b)
    white = low.point(lambda value: 255 if value >= 244 else 0)
    neutral = ImageChops.subtract(high, low).point(lambda value: 255 if value <= 18 else 0)
    mask = ImageChops.lighter(ImageChops.multiply(white, neutral), alpha.point(lambda value: 255 if value == 0 else 0))
    w, h = mask.size
    for x, y in [(x,y) for x in range(w) for y in (0,h-1)] + [(x,y) for y in range(h) for x in (0,w-1)]:
        if mask.getpixel((x,y)) == 255:
            ImageDraw.floodfill(mask, (x,y), 128)
    alpha.paste(0, mask=mask.point(lambda value: 255 if value == 128 else 0))
    result.putalpha(alpha)
    return result


def selected_frames(source, side):
    with Image.open(source) as image:
        frames, ends, total = [], [], 0
        for index in range(image.n_frames):
            image.seek(index)
            frames.append(image.convert("RGBA"))
            total += max(20, image.info.get("duration", 80))
            ends.append(total)
    output = []
    for index in range(20):
        time = index * total / 20
        chosen = next((i for i,end in enumerate(ends) if end > time),len(frames)-1)
        output.append(exterior_alpha(frames[chosen]).resize((side,side),Image.Resampling.LANCZOS))
    return output, total


def validate(path, expected_size, main=False):
    if path.stat().st_size > 1_000_000:
        raise ValueError(f"APNG exceeds conservative 1 MB cap: {path.name}")
    with Image.open(path) as image:
        assert image.size == expected_size and 5 <= image.n_frames <= 20
        assert image.info.get("loop") == 1
        duration = 0
        for index in range(image.n_frames):
            image.seek(index)
            duration += image.info.get("duration",0)
            assert image.convert("RGBA").getchannel("A").getextrema()[0] == 0
        assert abs(duration-4000) < 1
        return {"frames":image.n_frames,"duration_ms":duration,"bytes":path.stat().st_size,
                "sha256":hashlib.sha256(path.read_bytes()).hexdigest()}


def encode(frames, target, palettes=(None, 192, 128)):
    for colors in palettes:
        options = {}
        values = frames
        if colors:
            # APNG palette frames must share the same palette, including transparency.
            samples = Image.new("RGB", (64 * len(frames), 64))
            for i, frame in enumerate(frames):
                samples.paste(frame.convert("RGB").resize((64, 64)), (i * 64, 0))
            palette = samples.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
            values = []
            for frame in frames:
                value = frame.convert("RGB").quantize(palette=palette, dither=Image.Dither.NONE)
                shared_palette = palette.getpalette()
                value.putpalette(shared_palette + [0] * (768 - len(shared_palette)))
                value.paste(255, mask=frame.getchannel("A").point(lambda a: 255 if a < 128 else 0))
                values.append(value)
            options["transparency"] = 255
        values[0].save(target,format="PNG",save_all=True,append_images=values[1:],duration=200,loop=1,disposal=0,blend=0,optimize=True,**options)
        if target.stat().st_size <= 1_000_000:
            return colors
    raise ValueError("APNG exceeds file limit after bounded encoding variants")


def export_pack(catalog, root, pack_id, output):
    pack = next(p for p in catalog["packs"] if p["id"] == pack_id)
    stickers = pack["stickers"]["ja"]
    if len(stickers) not in (8,16,24):
        raise ValueError("LINE requires 8, 16 or 24; choose a separate edition explicitly")
    output.mkdir(parents=True,exist_ok=False)
    rows = []
    first_frames = None
    for number,sticker in enumerate(stickers,1):
        parsed = urlparse(sticker["gif"])
        assert parsed.scheme == "https" and parsed.netloc == "aya.lazying.art"
        source = (root/parsed.path.lstrip("/")).resolve()
        source.relative_to(root.resolve())
        frames, original_ms = selected_frames(source,270)
        target = output/f"{number:02d}.png"
        colors = encode(frames,target)
        rows.append({"number":number,"id":sticker["id"],"label":sticker["label"],"file":target.name,
                     "source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),"source_duration_ms":original_ms,
                     "quantization":colors,"checks":validate(target,(270,270))})
        if first_frames is None: first_frames=frames
    main = [frame.resize((240,240),Image.Resampling.LANCZOS) for frame in first_frames]
    encode(main,output/"main.png")
    validate(output/"main.png",(240,240),True)
    thumb = Image.new("RGBA",(96,74))
    tile = main[0].resize((74,74),Image.Resampling.LANCZOS)
    thumb.alpha_composite(tile,(11,0));thumb.save(output/"tab.png")
    receipt = {"pack":pack_id,"name":pack["name"],"english":pack["english"],"language":"ja",
               "status":"local conversion; visual review and platform upload pending",
               "changes":["20 time-sampled frames", "4 seconds, one loop", "perimeter-connected near-white removed", "270px square; originals preserved"],"stickers":rows}
    (output/"manifest.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n")
    with zipfile.ZipFile(output/"line-upload.zip","w",zipfile.ZIP_DEFLATED) as archive:
        for name in ["main.png","tab.png"]+[r["file"] for r in rows]:archive.write(output/name,name)
    assert (output/"line-upload.zip").stat().st_size < 60_000_000
    cards="".join(f'<figure><img src="{r["file"]}" alt="{html.escape(r["label"])}"><figcaption>{r["number"]:02d} · {html.escape(r["label"])}</figcaption></figure>' for r in rows)
    (output/"index.html").write_text('<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>'+html.escape(pack["english"])+' · LINE</title><style>body{font:16px system-ui;margin:24px;background:#eaf6ff;color:#183a4e}h1{font-size:24px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px}figure{margin:0;background:#b9dce9;border-radius:8px;padding:12px}img{width:100%;aspect-ratio:1;object-fit:contain}button{font:inherit;padding:8px 16px;margin-bottom:16px}</style><h1>'+html.escape(pack["name"])+' · 日本語 LINE版</h1><button onclick="document.querySelectorAll(\'img\').forEach(i=>{const s=i.src;i.src=\'\';i.src=s})">もう一度再生</button><main>'+cards+'</main></html>')
    return {"pack":pack_id,"count":len(rows),"output":str(output),"bytes":(output/"line-upload.zip").stat().st_size}


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("artwork_root",type=Path);p.add_argument("pack");p.add_argument("output",type=Path)
    p.add_argument("--catalog",type=Path,default=Path("public/catalog.json"))
    args=p.parse_args()
    print(json.dumps(export_pack(json.loads(args.catalog.read_text()),args.artwork_root,args.pack,args.output)))
