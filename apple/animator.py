import os
import json
import random

from PIL import Image
import numpy as np
import cv2

from .util import read_json
from .dataloader import get_assets
from .lipsync import viseme_sequencer


class FrameSequence:
    def __init__(self):
        self.pose_files = []
        self.mouth_files = []
        self.pose_images = []
        self.mouth_images = []
        self.mouth_coords = []
        self.final_frames = []


class animate:
    """Animates a cartoon that is lip synced to provieded audio voiceover."""

    def __init__(self, audio_file: str, txt_file: str, video_path: str):
        self.viseme_sequence = viseme_sequencer(audio_file, txt_file)
        print(self.viseme_sequence)

        self.duration = self.viseme_sequence[-1].time_end
        self.video_path = video_path

        self.assets = get_assets()
        self.mouth_files = []  # load_mouth_files()
        self.sequence = FrameSequence()
        self.fps = 24

        self.build_pose_sequence()
        self.sequence.pose_files = [
            f"{os.path.dirname(__file__)}{file}" for file in self.sequence.pose_files
        ]

        number_pose = len(self.sequence.pose_files)
        print(f"Len Poses: {number_pose}")

        self.build_mouth_sequence()
        # Create path to mouth images

        self.frame_size = self.get_frame_size()
        self.compile_animation()

    def build_pose_sequence(self):
        """Creates the sequence of pose images for the video"""
        seconds_per_pose = 6

        emotion = self.random_emotion()
        pose = random.choice(emotion)
        for i, _ in enumerate(self.viseme_sequence):
            if i % (seconds_per_pose * self.fps) == 0:
                emotion = self.random_emotion()
                pose = random.choice(emotion)

            # Add to image file sequence
            pose_files = [pose.image_files["open"] for _ in range(self.fps)]
            mouth_coords = [pose.mouth_coordinates for _ in range(self.fps)]
            self.sequence.pose_files.extend(pose_files)
            self.sequence.mouth_coords.extend(mouth_coords)

            # Generate blink animation frames every 2 seconds
            if pose_seconds % 2 == 0 and pose_seconds > 0:
                num_blink_frames = self.blink(pose=pose)
                pose_seconds += num_blink_frames / self.fps
                total_seconds += num_blink_frames / self.fps

            # End if total video duration has been met
            if total_seconds >= self.duration:
                break
        return

    def blink(self, pose):
        """Generates an animation sequence for eye blinking in a specific pose

        Args:
            pose (Pose): A Pose object containing pose configuration data

        Returns:
            int: Returns the number of frames that were generated for talling total generated
        """
        frames = []
        blink_duration = 0.4
        subsequence_duration = blink_duration / 5
        num_frames = int(self.fps * subsequence_duration)

        open_frames = [pose.image_files["open"] for _ in range(num_frames)]
        mid_frames = [pose.image_files["middle"] for _ in range(num_frames)]
        shut_frames = [pose.image_files["shut"] for _ in range(num_frames)]
        open_wait = [pose.image_files["open"] for _ in range(int(self.fps * 1.5))]

        frames.extend(open_frames)
        frames.extend(mid_frames)
        frames.extend(shut_frames)
        frames.extend(mid_frames)
        frames.extend(open_frames)

        self.sequence.pose_files.extend(frames)

        mouth_coords = [pose.mouth_coordinates for _ in range(len(frames))]
        self.sequence.mouth_coords.extend(mouth_coords)

        return len(frames)

    def build_mouth_sequence(self):
        """Generates a sequence of mouth images for video"""

        last_idx = 0
        for i, _ in len(self.viseme_sequence):
            # index of frame within video where viseme should be added
            start_idx = int(self.fps * self.viseme_sequence[i].time_start)

            # Add None to sequence in previous positions where there are no visemes
            if start_idx != last_idx:
                idx_jump = start_idx - last_idx
                self.sequence.mouth_files.extend([None for _ in range(idx_jump)])

            # Add visemes images to sequence
            if self.viseme_sequence[i].visemes:
                self.sequence.mouth_files.extend(self.viseme_sequence[i].visemes)
            else:
                continue
            last_idx += len(self.viseme_sequence[i].visemes)

        mth_fls = len(self.sequence.mouth_files)
        print(f"Mouth Files: {mth_fls}")
        for i, _ in enumerate(self.sequence.mouth_files):
            if self.sequence.mouth_files[i] is not None:
                file = self.sequence.mouth_files[i]
                new_file = f"{os.path.dirname(__file__)}/assets/visemes/positive/{file}"
                self.sequence.mouth_files[i] = new_file

        for i, _ in enumerate(self.sequence.mouth_files):
            # Create transformed mouth image to fit pose
            if self.sequence.mouth_files[i] is not None:
                transformed_image = mouth_transformation(
                    mouth_file=self.sequence.mouth_files[i],
                    mouth_coord=self.sequence.mouth_coords[i],
                )
                self.sequence.mouth_images.append(transformed_image)
            else:
                self.sequence.mouth_images.append(None)

    def random_emotion(self):
        """Generates a random emotion to use in sequence

        Returns:
            list[Pose]: List of poses from a random emotion
        """
        emotions_list = list(self.assets.__dict__.keys())
        emotion = random.choice(emotions_list)
        return getattr(self.assets, emotion)

    def get_frame_size(self):
        pose_image = cv2.imread(self.sequence.pose_files[0])
        height, width, _ = pose_image.shape
        return (width, height)

    def compile_animation(self):
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        video = cv2.VideoWriter(self.video_path, fourcc, self.fps, self.frame_size)

        for i, _ in enumerate(self.sequence.pose_files):
            frame = cv2.imread(self.sequence.pose_files[i])
            if self.sequence.mouth_files[i] is not None:
                final_frame = render_frame(
                    pose_img=frame,
                    mouth_img=self.sequence.mouth_images[i],
                    mouth_coord=self.sequence.mouth_coords[i],
                )
            else:
                final_frame = frame
            video.write(final_frame)
        video.release()


def load_mouth_files():
    """Loads image file paths to mouth images"""
    path = f"{os.path.dirname(__file__)}/assets/mouths"
    files = os.listdir(path)
    files.sort(key=lambda x: int(x.split(".")[0]))
    files = [os.path.join(path, file) for file in files]
    return files


def mouth_transformation(mouth_file, mouth_coord) -> Image:
    """Transforms mouth image with scaling, flipping, and rotation.
        This transformation is applied because, the same mouth shape images
        are used for different pose images, but the size, angle, and position
        of a mouth image will depend on which pose image is being used.

    Args:
        mouth_path (str): .png file path pointing to mouth image
        transformation (np.array): image transformation data for mouth

    Returns:
        Image: PIL Image object of mouth image with applied transformations
    """
    mouth = Image.open(mouth_file)
    # Flip mouth horizontally if necessary
    if mouth_coord.flip_x is True:
        mouth = mouth.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    # Scale mouth image if necessary
    if mouth_coord.scale_y != 1:
        og_width, og_height = mouth.size
        new_width = int(abs(og_width * mouth_coord.scale_x))
        new_height = int(og_height * mouth_coord.scale_y)
        try:
            mouth = mouth.resize(new_width, new_height, Image.Resampling.LANCZOS)
        except:
            pass
    # Apply image rotation if necessary
    if mouth_coord.rotation != 0:
        mouth = mouth.rotate(-mouth_coord.rotation, resample=Image.Resampling.BICUBIC)
    return mouth


def render_frame(pose_img: Image, mouth_img: Image, mouth_coord):
    pose_img = Image.fromarray(pose_img)
    mouth_width, mouth_height = mouth_img.size

    # Location in pose image where mouth / viseme image will be added
    paste_coordinates = (
        int(mouth_coord.x - (mouth_width / 2)),
        int(mouth_coord.y - (mouth_height / 2)),
    )

    # Paste the mouth image onto the face image at the specified coordinates
    pose_img.paste(im=mouth_img, box=paste_coordinates, mask=mouth_img)
    np_image = np.array(pose_img)

    # Convert BGR PIL image to RGB (if necessary)
    if np_image.shape[2] == 3:
        np_image = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)
    return np_image
