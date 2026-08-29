#!/usr/bin/env python3
"""Turn a video into the fewest frames that still show what changed.

Reading a video costs one vision call per frame, so the whole point is to send
few frames, not many. Two ideas do the work:

  * SCENE DETECTION, not a fixed frame rate. A screen recording of a UI is
    mostly static; sampling at 2 fps spends most of its budget photographing
    the same motionless screen. ffmpeg's scene filter returns only the moments
    the picture actually changed.
  * A CONTACT SHEET FIRST. One tiled image with timestamps costs a single
    vision call and is usually enough to say "the thing you mean is at 0:14".
    Only then is it worth looking at one or two frames full size.

Usage:
    frames.py VIDEO [-o OUTDIR] [--threshold 0.25] [--max 24]
               [--start SEC] [--end SEC] [--cols 3] [--width 460]
"""
import argparse, glob, os, shutil, subprocess, sys

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"ffmpeg failed:\n{(p.stderr or '').strip()[-800:]}")
    return p

def duration(path):
    p = run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'csv=p=0', path])
    try: return float(p.stdout.strip())
    except ValueError: return 0.0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('video')
    ap.add_argument('-o', '--outdir', default='frames')
    ap.add_argument('--threshold', type=float, default=0.25,
                    help='scene-change sensitivity, 0-1. Lower finds more.')
    ap.add_argument('--max', type=int, default=24, help='hard ceiling on frames')
    ap.add_argument('--start', type=float, help='seconds; trims before extracting')
    ap.add_argument('--end', type=float)
    ap.add_argument('--cols', type=int, default=3)
    ap.add_argument('--width', type=int, default=460, help='per-tile width')
    a = ap.parse_args()

    if not shutil.which('ffmpeg'): sys.exit('ffmpeg is not installed')
    if not os.path.isfile(a.video): sys.exit(f'no such file: {a.video}')

    out = a.outdir
    shutil.rmtree(out, ignore_errors=True); os.makedirs(out, exist_ok=True)

    # -ss/-t BEFORE -i so ffmpeg seeks instead of decoding and discarding.
    trim = []
    if a.start is not None: trim += ['-ss', str(a.start)]
    if a.end is not None:   trim += ['-t', str(a.end - (a.start or 0))]

    total = duration(a.video)
    # Timestamps come from showinfo on stderr; without them a frame is just an
    # image, and "the bit at 0:14" is the only way to talk about a moment.
    p = subprocess.run(
        ['ffmpeg', '-hide_banner', *trim, '-i', a.video,
         '-vf', f"select='gt(scene,{a.threshold})',showinfo",
         '-vsync', 'vfr', '-q:v', '3', os.path.join(out, 'f_%03d.jpg')],
        capture_output=True, text=True)
    # showinfo reports pts relative to the TRIMMED stream, so after --start
    # every timestamp is short by that offset — and a timestamp you cannot
    # scrub back to in the original video is worse than none, because it looks
    # authoritative. Add the offset back.
    offset = a.start or 0.0
    times = []
    for line in (p.stderr or '').splitlines():
        if 'pts_time:' in line:
            try: times.append(float(line.split('pts_time:')[1].split()[0]) + offset)
            except (IndexError, ValueError): pass

    # The opening frame is never a "change", so it is never selected — and it
    # is the one that shows where the video starts from.
    first = os.path.join(out, 'f_000.jpg')
    run(['ffmpeg', '-hide_banner', '-loglevel', 'error', *trim, '-i', a.video,
         '-frames:v', '1', '-q:v', '3', first])
    times.insert(0, a.start or 0.0)

    shots = sorted(glob.glob(os.path.join(out, 'f_*.jpg')))
    if not shots: sys.exit('no frames extracted — try a lower --threshold')

    # Thin evenly rather than truncating: the end of a video matters as much as
    # the start, and cutting the tail loses the outcome of whatever was shown.
    if len(shots) > a.max:
        step = len(shots) / a.max
        keep = {shots[min(int(i * step), len(shots) - 1)] for i in range(a.max)}
        for s in shots:
            if s not in keep: os.remove(s)
        idx = [i for i, s in enumerate(shots) if s in keep]
        times = [times[i] for i in idx if i < len(times)]
        shots = sorted(keep)

    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print(f'{len(shots)} frames in {out}/ (install Pillow for a contact sheet)')
        return

    tiles = []
    for i, f in enumerate(shots):
        im = Image.open(f).convert('RGB')
        im = im.resize((a.width, max(1, int(im.height * a.width / im.width))))
        t = times[i] if i < len(times) else 0.0
        tiles.append((f'{int(t) // 60}:{int(t) % 60:02d}', im))

    band = 20
    rh = max(i.height for _, i in tiles) + band
    cols = max(1, a.cols)
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * a.width, rows * rh), (18, 18, 18))
    d = ImageDraw.Draw(sheet)
    for k, (label, im) in enumerate(tiles):
        x, y = (k % cols) * a.width, (k // cols) * rh
        sheet.paste(im, (x, y + band))
        d.text((x + 5, y + 4), label, fill=(255, 255, 255))
    sheet_path = os.path.join(out, 'contact.jpg')
    sheet.save(sheet_path, quality=85)

    kb = os.path.getsize(sheet_path) / 1024
    print(f'video {total:.1f}s -> {len(tiles)} scene frames')
    print(f'contact sheet: {sheet_path} ({kb:.0f} KB) — read this FIRST')
    print('frames: ' + ', '.join(f'{l} {os.path.basename(f)}'
                                 for (l, _), f in zip(tiles, shots)))

if __name__ == '__main__':
    main()
