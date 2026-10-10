"""Build small animated catalog previews; preserve every original GIF.

Inputs are an explicit approved public artwork root and this app's catalog.
Outputs are reproducible, ignored derivatives used by the static PWA build.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from urllib.parse import urlparse
from PIL import Image


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('artwork_root', type=Path)
    p.add_argument('--catalog', type=Path, default=Path('public/catalog.json'))
    p.add_argument('--output', type=Path, default=Path('public/motion'))
    a = p.parse_args()
    root = a.artwork_root.resolve()
    a.output.mkdir(parents=True, exist_ok=True)
    catalog = json.loads(a.catalog.read_text())
    rows = {}
    for pack in catalog['packs']:
        for stickers in pack['stickers'].values():
            for sticker in stickers:
                url = sticker['gif']
                parsed = urlparse(url)
                assert parsed.scheme == 'https' and parsed.netloc == 'aya.lazying.art'
                source = (root / parsed.path.lstrip('/')).resolve()
                source.relative_to(root)
                assert source.is_file() and source.suffix.lower() == '.gif'
                digest = hashlib.sha256(source.read_bytes()).hexdigest()
                name = digest[:24] + '-160-10-70-v1.webp'
                target = a.output / name
                if not target.exists():
                    temporary = target.with_name(target.stem + '.partial.webp')
                    subprocess.run(['ffmpeg', '-nostdin', '-y', '-loglevel', 'error',
                        '-i', str(source), '-vf', 'fps=10,scale=160:160:flags=lanczos',
                        '-c:v', 'libwebp_anim', '-quality', '70', '-compression_level', '6',
                        '-loop', '0', '-threads', '1', str(temporary)], check=True, timeout=40)
                    with Image.open(temporary) as image:
                        assert image.size == (160, 160) and image.n_frames > 1
                    temporary.replace(target)
                rows[url] = {'preview': '/motion/' + name, 'source_sha256': digest,
                             'source_bytes': source.stat().st_size,
                             'preview_bytes': target.stat().st_size}
    result = {'version': 1, 'previews': rows,
              'source_bytes': sum(r['source_bytes'] for r in rows.values()),
              'preview_bytes': sum(r['preview_bytes'] for r in rows.values())}
    (a.output / 'manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'previews'}))


if __name__ == '__main__':
    main()
