#!/usr/bin/env python3
"""Build the 90-second introduction video of lab.meteo@uniparthenope (macOS).

Inputs, produced by ``scripts/capture_media.py`` against a running deployment:
    media/clips/01-gallery.webm … 06-dashboard.webm   screen recordings (1280×720)
    media/architecture.png                             architecture figure (1920 px wide)

Output: media/lab-meteo-intro.mp4 (H.264 1920×1080, 30 fps) with
    audio 1  "English"                  narration (default track)
    audio 2  "English (audio comments)" commentary describing what is on screen
    subtitle "English"                  narration text
Voices are macOS system voices (``say``); every track uses a female and a male voice.
The video and its working files stay in media/, which Git ignores.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "media"
WORK = MEDIA / "build"
OUT = MEDIA / "lab-meteo-intro.mp4"
W, H, FPS = 1920, 1080, 30
TOTAL = 90.0
PRIMARY, ACCENT, SECONDARY = (31, 78, 121), (24, 28, 99), (42, 145, 235)
FONT = "/System/Library/Fonts/Avenir Next.ttc"
LOGO = ROOT / "jupyterhub/assets/logo.png"

# Voices: main track Samantha (female, en_US) and Daniel (male, en_GB);
# commentary track Karen (female, en_AU) and Reed (male, en_GB).
MAIN_F, MAIN_M = "Samantha", "Daniel"
COMM_F, COMM_M = "Karen", "Reed (English (UK))"
BRAND_SPOKEN = "lab dot meteo at uni Parthenope"

# Each segment: visual source, minimum duration, on-screen caption, narration lines, commentary lines.
SEGMENTS = [
    dict(kind="card", card="title", min=6.0, caption=None,
         main=[(MAIN_F, "What if every forecast, every ocean model, and every sensor reading were one click away?")],
         comm=[(COMM_F, "Title card: the lab dot meteo logo on a deep-blue gradient.")]),
    dict(kind="clip", clip="01-gallery", min=9.0, caption="Thirty notebooks · weather, sea, sensors, AI",
         main=[(MAIN_M, f"Meet {BRAND_SPOKEN}: thirty ready-to-run notebooks built on the operational "
                        "models and sensor network of the University of Naples Parthenope.")],
         comm=[(COMM_M, "The public gallery: the forecast API, numerical models, live weather stations, and transparent AI.")]),
    dict(kind="clip", clip="02-browser-runtime", min=12.0, caption="No install · Python runs in your browser",
         main=[(MAIN_F, "Open one, and it runs. No installation, no account: Python executes inside your "
                        "browser, compiled to WebAssembly, so your code never runs on our servers.")],
         comm=[(COMM_F, "JupyterLite runs a Pyodide kernel. A polar plot of wind direction and speed appears "
                        "beside a forty-eight hour WRF forecast for the Gulf of Naples.")]),
    dict(kind="card", card="connect", min=3.0, caption=None,
         main=[(MAIN_M, "Need more power?")],
         comm=[(COMM_M, "Sign in. Connect. Compute.")]),
    dict(kind="clip", clip="03-start-page", min=11.0, caption="Colab-style start page · Examples · Recent · GitHub · Upload",
         main=[(MAIN_M, "Sign in, and it feels like Colab: examples, recent notebooks, GitHub links, "
                        "uploads, and a runtime one click away.")],
         comm=[(COMM_M, "The start page. Typing 'forecast' filters the examples; a GitHub link is pasted. "
                        "The runtime card shows memory, CPU, and idle shutdown.")]),
    dict(kind="clip", clip="04-server-notebook", min=12.0, caption="Your own container · Xarray · Dask · Zarr · Cartopy",
         main=[(MAIN_F, "Your notebook opens in a private container with the full scientific Python stack: "
                        "Xarray, Dask, Zarr, and Cartopy, with storage that persists between sessions.")],
         comm=[(COMM_F, "The same notebook, copied into the user's workspace and opened in Jupyter Notebook "
                        "seven. This time it runs on a standard Python kernel in the user's own container.")]),
    dict(kind="clip", clip="05-jupyterlab", min=6.0, caption="JupyterLab · terminals · Git · Voilà dashboards",
         main=[(MAIN_M, "Switch to JupyterLab at any time, with terminals, Git, and dashboards.")],
         comm=[(COMM_M, "JupyterLab, with folders for GitHub copies, outputs, and uploads.")]),
    dict(kind="still", still="architecture", min=11.0, caption="Model archives and station data · strictly read-only",
         main=[(MAIN_F, "Inside every runtime: WRF, ROMS, WaveWatch Three, WaComM, and AIquam output, plus "
                        "the station network, all mounted strictly read-only.")],
         comm=[(COMM_F, "The architecture: one front proxy, JupyterHub, an unprivileged container per user, "
                        "and archives bound read-only, checked at every server start.")]),
    dict(kind="clip", clip="06-dashboard", min=7.0, caption="Roles · privacy self-service · live security audit",
         main=[(MAIN_M, "Roles, resource tiers, privacy self-service, and a live security audit, by design.")],
         comm=[(COMM_M, "The dashboard: accounts and roles, data sources, privacy requests, security posture.")]),
    dict(kind="card", card="end", min=8.0, caption=None,
         main=[(MAIN_F, f"{BRAND_SPOKEN}. Open science, from forecast to insight."),
               (MAIN_M, "Start exploring today.")],
         comm=[(COMM_F, "End card: the service name, web address, and open-source repository.")]),
]

SUBTITLE_TEXT = {  # what the subtitles show instead of the phonetic brand spelling
    BRAND_SPOKEN: "lab.meteo@uniparthenope",
    "WaveWatch Three": "WaveWatch III",
    "Jupyter Notebook seven": "Jupyter Notebook 7",
}


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return result.stdout


def duration(path: Path) -> float:
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)]))


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    # Avenir Next collection: index 0 Bold, 7 Regular (checked by name below).
    for index in range(12):
        try:
            candidate = ImageFont.truetype(FONT, size, index=index)
        except OSError:
            break
        style = candidate.getname()[1]
        if (bold and style == "Bold") or (not bold and style == "Regular"):
            return candidate
    return ImageFont.truetype(FONT, size)


def gradient() -> Image.Image:
    image = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(image)
    for x in range(W):
        t = x / (W - 1)
        draw.line([(x, 0), (x, H)], fill=tuple(int(PRIMARY[i] * (1 - t) + ACCENT[i] * t) for i in range(3)))
    return image


def logo(size: int) -> Image.Image:
    mark = Image.open(LOGO).convert("RGBA").resize((size, size), Image.LANCZOS)
    disc = Image.new("RGBA", (size + 16, size + 16), (0, 0, 0, 0))
    ImageDraw.Draw(disc).ellipse([0, 0, size + 15, size + 15], fill=(255, 255, 255, 255))
    disc.alpha_composite(mark, (8, 8))
    return disc


def centered(draw, y, text, fnt, fill=(255, 255, 255)):
    width = draw.textlength(text, font=fnt)
    draw.text(((W - width) / 2, y), text, font=fnt, fill=fill)


def make_card(name: str) -> Path:
    image = gradient().convert("RGBA")
    draw = ImageDraw.Draw(image)
    if name == "title":
        image.alpha_composite(logo(220), ((W - 236) // 2, 190))
        centered(draw, 480, "lab.meteo@uniparthenope", font(104, True))
        centered(draw, 625, "Weather and marine science, one click away", font(52))
        centered(draw, 760, "University of Naples “Parthenope” · meteo@uniparthenope", font(34), (210, 228, 245))
    elif name == "connect":
        centered(draw, 380, "Sign in.  Connect.  Compute.", font(110, True))
        centered(draw, 560, "A private server runtime with the operational archives", font(46), (210, 228, 245))
    elif name == "end":
        image.alpha_composite(logo(170), ((W - 186) // 2, 140))
        centered(draw, 380, "lab.meteo@uniparthenope", font(100, True))
        centered(draw, 515, "Open science, from forecast to insight", font(54))
        centered(draw, 650, "lab.meteo.uniparthenope.it", font(58, True), (170, 214, 255))
        centered(draw, 760, "Open source · github.com/CCMMMA/lab-meteo-uniparthenope", font(36), (210, 228, 245))
        centered(draw, 830, "JupyterHub · Jupyter Notebook 7 · JupyterLab · JupyterLite", font(32), (210, 228, 245))
    path = WORK / f"card-{name}.png"
    image.convert("RGB").save(path)
    return path


def make_caption(text: str, index: int) -> Path:
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    fnt = font(44, True)
    width = draw.textlength(text, font=fnt)
    box = [80, H - 170, 80 + width + 80, H - 80]
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([box[0] + 6, box[1] + 10, box[2] + 6, box[3] + 10], 22, fill=(0, 0, 0, 90))
    overlay.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(12)))
    draw.rounded_rectangle(box, 22, fill=(*PRIMARY, 235))
    draw.rectangle([box[0], box[1] + 18, box[0] + 10, box[3] - 18], fill=(*SECONDARY, 255))
    draw.text((box[0] + 44, box[1] + 18), text, font=fnt, fill=(255, 255, 255))
    path = WORK / f"caption-{index:02d}.png"
    overlay.save(path)
    return path


def speak(voice: str, text: str, path: Path) -> float:
    run(["say", "-v", voice, "-r", "178", "--file-format=WAVE", "--data-format=LEI16@48000", "-o", str(path), text])
    return duration(path)


def build_audio(segment_starts, kind: str) -> tuple[list[tuple[Path, float]], list[tuple[float, float, str]]]:
    """Synthesize one track's lines; return (wav, start) placements and subtitle cues."""
    placements, cues = [], []
    for index, (segment, start) in enumerate(zip(SEGMENTS, segment_starts)):
        cursor = start + 0.35
        for line_no, (voice, text) in enumerate(segment[kind]):
            wav = WORK / f"{kind}-{index:02d}-{line_no}.wav"
            length = speak(voice, text, wav)
            placements.append((wav, cursor))
            shown = text
            for spoken, written in SUBTITLE_TEXT.items():
                shown = shown.replace(spoken, written)
            cues.append((cursor, cursor + length, shown))
            cursor += length + 0.25
    return placements, cues


def music_bed(path: Path) -> None:
    """A quiet synthesized pad (A minor – F – C – G), so no third-party music is needed."""
    chords = [(110.0, 220.0, 261.63, 329.63), (87.31, 174.61, 261.63, 349.23),
              (130.81, 196.0, 261.63, 329.63), (98.0, 196.0, 246.94, 293.66)]
    step = TOTAL / 16
    terms = []
    for c, freqs in enumerate(chords):
        voice = "+".join(f"sin(2*PI*{f}*t)" for f in freqs)
        terms.append(f"(between(mod(t,{4 * step}),{c * step},{(c + 1) * step})*({voice}))")
    expr = "0.06*(" + "+".join(terms) + ")*(0.8+0.2*sin(2*PI*0.25*t))"
    run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
         f"aevalsrc='{expr}|{expr}':s=48000:d={TOTAL}",
         "-af", f"lowpass=f=1400,aecho=0.8:0.7:120|240:0.25|0.15,afade=t=in:d=3,afade=t=out:st={TOTAL - 4}:d=4",
         str(path)])


def mix_track(placements, music: Path, path: Path) -> None:
    inputs, filters, labels = ["-i", str(music)], [], []
    for n, (wav, start) in enumerate(placements, start=1):
        inputs += ["-i", str(wav)]
        delay = int(start * 1000)
        filters.append(f"[{n}:a]aformat=channel_layouts=stereo,adelay={delay}|{delay}[v{n}]")
        labels.append(f"[v{n}]")
    filters.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0[voice]")
    filters.append("[voice]asplit=2[voice1][voice2]")
    # Duck the pad under speech, then normalise to a broadcast-style loudness.
    filters.append("[0:a][voice1]sidechaincompress=threshold=0.02:ratio=8:attack=20:release=400[bed]")
    filters.append(f"[bed][voice2]amix=inputs=2:normalize=0,atrim=0:{TOTAL},loudnorm=I=-16:TP=-1.5:LRA=11[out]")
    run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(filters),
         "-map", "[out]", "-ar", "48000", "-ac", "2", str(path)])


def segment_video(index: int, segment: dict, length: float) -> Path:
    out = WORK / f"seg-{index:02d}.mp4"
    fade = f"fade=t=in:d=0.35,fade=t=out:st={length - 0.35:.3f}:d=0.35"
    if segment["kind"] == "card":
        src = make_card(segment["card"])
        vf = f"scale={W}:{H},zoompan=z='1+0.0006*on':d={int(length * FPS)}:s={W}x{H}:fps={FPS},{fade}"
        cmd = ["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", str(src), "-t", f"{length:.3f}", "-vf", vf]
    else:
        if segment["kind"] == "still":
            src = MEDIA / "architecture.png"
            base = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
                    f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0xf4f7fa,"
                    f"zoompan=z='1+0.0002*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(length * FPS)}:s={W}x{H}:fps={FPS}[b]")
            pre = ["-i", str(src)]  # one frame; zoompan generates the whole segment
        else:
            src = MEDIA / "clips" / f"{segment['clip']}.webm"
            available = duration(src)
            speed = min(max(available / length, 1.0), 1.6)
            start = max(available - length * speed, 0.0)
            base = (f"[0:v]trim=start={start:.3f},setpts=(PTS-STARTPTS)/{speed:.4f},fps={FPS},"
                    f"scale={W}:{H}:flags=lanczos,tpad=stop_mode=clone:stop_duration={length:.3f}[b]")
            pre = ["-i", str(src)]
        caption = make_caption(segment["caption"], index)
        graph = (f"{base};[1:v]format=rgba,fade=t=in:st=0.6:d=0.4:alpha=1[c];"
                 f"[b][c]overlay=0:0,trim=duration={length:.3f},{fade}[v]")
        cmd = ["ffmpeg", "-y", "-v", "error", *pre, "-loop", "1", "-i", str(caption),
               "-filter_complex", graph, "-map", "[v]", "-t", f"{length:.3f}"]
    cmd += ["-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-an", str(out)]
    run(cmd)
    return out


def srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def main() -> None:
    if shutil.which("say") is None:
        sys.exit("This script needs macOS (the say command).")
    for clip in [s["clip"] for s in SEGMENTS if s["kind"] == "clip"]:
        if not (MEDIA / "clips" / f"{clip}.webm").exists():
            sys.exit(f"Missing media/clips/{clip}.webm; run scripts/capture_media.py first.")
    WORK.mkdir(parents=True, exist_ok=True)

    # 1. Time every segment so that both tracks fit, then stretch to exactly TOTAL seconds.
    needs = []
    for index, segment in enumerate(SEGMENTS):
        longest = 0.0
        for kind in ("main", "comm"):
            spoken = sum(speak(v, t, WORK / f"probe-{kind}-{index}-{n}.wav") + 0.25
                         for n, (v, t) in enumerate(segment[kind]))
            longest = max(longest, spoken)
        needs.append(max(segment["min"], longest + 0.7))
    if sum(needs) > TOTAL:
        sys.exit(f"Narration needs {sum(needs):.1f} s, more than {TOTAL} s; shorten the script.")
    spare = TOTAL - sum(needs)
    stretchable = [i for i, s in enumerate(SEGMENTS) if s["kind"] != "card"]
    lengths = list(needs)
    for i in stretchable:
        lengths[i] += spare / len(stretchable)
    starts = [sum(lengths[:i]) for i in range(len(lengths))]

    # 2. Video.
    parts = [segment_video(i, s, lengths[i]) for i, s in enumerate(SEGMENTS)]
    listing = WORK / "parts.txt"
    listing.write_text("".join(f"file '{p}'\n" for p in parts))
    video = WORK / "video.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(video)])

    # 3. Audio tracks and subtitles.
    music = WORK / "music.wav"
    music_bed(music)
    main_places, cues = build_audio(starts, "main")
    comm_places, _ = build_audio(starts, "comm")
    mix_track(main_places, music, WORK / "track-main.wav")
    mix_track(comm_places, music, WORK / "track-comments.wav")
    srt = WORK / "narration.srt"
    srt.write_text("".join(f"{n}\n{srt_time(a)} --> {srt_time(b)}\n{text}\n\n"
                           for n, (a, b, text) in enumerate(cues, start=1)), encoding="utf-8")

    # 4. Mux: video, two English audio tracks (narration default, audio comments), subtitles.
    run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-i", str(WORK / "track-main.wav"),
         "-i", str(WORK / "track-comments.wav"), "-i", str(srt),
         "-map", "0:v", "-map", "1:a", "-map", "2:a", "-map", "3:s",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-c:s", "mov_text",
         "-metadata", "title=lab.meteo@uniparthenope — introduction",
         "-metadata:s:a:0", "language=eng", "-metadata:s:a:0", "title=English",
         "-metadata:s:a:1", "language=eng", "-metadata:s:a:1", "title=English (audio comments)",
         "-metadata:s:s:0", "language=eng", "-metadata:s:s:0", "title=English",
         "-disposition:a:0", "default", "-disposition:a:1", "comment", "-disposition:s:0", "0",
         "-t", str(TOTAL), "-movflags", "+faststart", str(OUT)])
    (WORK / "timeline.json").write_text(json.dumps(
        [{"segment": i, "start": round(starts[i], 2), "length": round(lengths[i], 2)} for i in range(len(SEGMENTS))], indent=1))
    print(f"{OUT} ({duration(OUT):.1f} s)")


if __name__ == "__main__":
    main()
