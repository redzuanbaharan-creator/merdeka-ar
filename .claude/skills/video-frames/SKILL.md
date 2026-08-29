---
name: video-frames
description: "Read a video the user cannot otherwise show you — a screen recording, a UI demo, a mechanism, a tutorial clip. Turns a video file into the fewest frames that still show what changed, plus a single timestamped contact sheet to read first. Use whenever the user attaches or points at a video file (.mp4, .mov, .webm, .mkv, .avi, .gif) and wants you to copy a design, reproduce an interaction, understand a mechanism, or follow steps shown on screen. Also use when they say they wish they could show you a video, or describe something they saw in one."
---

# Reading a video without spending a hundred vision calls

A video reaches you as images, and every image costs a vision call. Tools that
sample at a fixed frame rate send 30–100 frames for a short clip — most of them
photographs of the same motionless screen. That is the expensive way to answer
"make it work like this".

Two ideas make it cheap:

**Scene detection, not a frame rate.** A screen recording is mostly static.
`ffmpeg`'s scene filter returns only the moments the picture actually changed,
which for a UI demo is a handful of frames rather than dozens.

**The contact sheet first.** One tiled image with timestamps is a single vision
call and is nearly always enough to say *"the thing you mean is at 0:14"*. Only
then is it worth opening one or two frames full size.

## Use it

```bash
python3 scripts/frames.py VIDEO -o frames
```

Then **read `frames/contact.jpg` first** — one image, every scene, timestamped.
Say what you see, confirm which moment the user means, and only then Read the
individual `f_*.jpg` for that moment.

| flag | for |
|---|---|
| `--threshold 0.15` | subtle changes (a menu sliding, a colour shift). Lower finds more |
| `--threshold 0.4` | a busy video returning too many near-identical frames |
| `--start 12 --end 30` | the one section that matters — cheapest possible read |
| `--max 24` | ceiling on frames. Thins evenly, so the ending is never lost |
| `--cols 3 --width 460` | contact sheet layout |

Timestamps are real video times even after `--start`, so the user can scrub
straight back to the moment being discussed.

## How to actually answer

1. Run the script. Read `contact.jpg`. **Nothing else yet.**
2. Describe what you see and name the timestamps — this is what lets the user
   correct you before you build anything.
3. If a moment needs detail, Read that single frame. Two or three at most.
4. Re-run with `--start/--end` around the moment rather than lowering
   `--threshold` across the whole video; a narrow window is far cheaper than a
   sensitive pass over everything.

**A video shows what something looks like, not why.** Frames give you layout,
sequence and state changes. They do not give you the reasoning, the data model,
or anything off screen — so state what you actually saw and ask about the rest
instead of inferring it.

**There is no audio in this.** If the point is spoken rather than shown, say so
and ask the user for the sentence; transcription is a different tool and
usually unnecessary for a design or interaction question.

## When NOT to use it

If the user can screenshot the two or three moments themselves, that is better
and costs almost nothing — **they know which frame matters and the detector does
not.** Suggest it for a simple "make it look like this". Reach for the script
when the sequence or the motion is the point, or when they have a file and no
easy way to pick moments out of it.

## Requirements

`ffmpeg` and `ffprobe` on PATH. Pillow is optional — without it the frames are
still extracted and the script says so, it just cannot tile them.
