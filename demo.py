from moviepy import ImageClip

from pyanimator.animator import animate

import time

# Constants
FPS = 48
TEXT_PATH = "./.test/speech.txt"  # Path to a transcript text file (optional)
AUDIO_PATH = "./.test/speech.mp3"  # Path to an audio file of speech
BACKGROUND_IMAGE = "./.test/image.png"  # Path to an image for the video background
OUTPUT_VIDEO = "./output_animation_with_transcript.mp4"  # Output for Example 1

start_time = time.time()

# Load the transcript
with open(TEXT_PATH, "r") as file:
    transcript = file.read()

# Generate the animation with the provided transcript
animation = animate(audio_file=AUDIO_PATH, transcript=transcript)

# Create a background clip
background_clip = ImageClip(BACKGROUND_IMAGE)
background_clip = background_clip.with_fps(FPS).with_duration(animation.duration)


# Export the animation
animation.export(path=OUTPUT_VIDEO, background=background_clip)

end_time = time.time()

print(f"Total time: {end_time - start_time} seconds")