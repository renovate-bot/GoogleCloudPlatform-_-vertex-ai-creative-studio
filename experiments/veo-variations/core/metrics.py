import os
import subprocess
import tempfile
import numpy as np
from pathlib import Path
import pyiqa
import torch

def extract_frames(video_path, output_dir, num_frames=5):
    """Extracts a fixed number of frames from a video using ffmpeg."""
    # Get total duration
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)]
    duration = float(subprocess.check_output(cmd).decode().strip())
    
    # Extract frames at regular intervals
    intervals = np.linspace(0, duration, num_frames + 2)[1:-1]
    
    for i, timestamp in enumerate(intervals):
        frame_path = Path(output_dir) / f"frame_{i:03d}.png"
        cmd = [
            "ffmpeg", "-ss", str(timestamp), "-i", str(video_path),
            "-frames:v", "1", "-q:v", "2", str(frame_path), "-y", "-loglevel", "error"
        ]
        subprocess.run(cmd)
    
    return list(Path(output_dir).glob("*.png"))

def evaluate_technical_quality(video_path, metric_name="niqe"):
    """Calculates no-reference quality metrics using pyiqa."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    iqa_metric = pyiqa.create_metric(metric_name, device=device)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        frames = extract_frames(video_path, tmpdir)
        scores = []
        for frame in frames:
            score = iqa_metric(str(frame)).item()
            scores.append(score)
            
    return {
        "metric": metric_name,
        "avg_score": float(np.mean(scores)),
        "min_score": float(np.min(scores)),
        "max_score": float(np.max(scores)),
        "frame_scores": [float(s) for s in scores]
    }
