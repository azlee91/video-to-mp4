import argparse
import logging
import os
import subprocess
import time
from pathlib import Path

LOGGER = None


def encode_video_ffmpeg(
    input_dir: str,
    output_dir: str,
    video_file: str,
    video: bool = True,
    audio: bool = True,
    dry_run: bool = False,
) -> bool:
    """
    Use FFMPEG to convert the input video to MP4 web playable

    :arg input_dir: The directory to look for the source
    :arg output_dir: The location to output the result file to
    :arg video: True to convert video, False to skip conversion
    :arg audio: True to convert audio, False to skip audio

    :returns: True if conversion was successful, false otherwise

    audio=False/video=False: Simple conversion to MP4
        If video codec is already H264 and audio codec is already AAC

    audio=False/video=True: Encode video only
        If video codec is not H264 and audio codec is already AAC

    audio=True/video=False: Encode audio only
        If video codec is already H264, but audio codec is not AAC

    audio=True/video=True: Encode both audio and video
        If video codec not H264, and audio codec is not AAC
    """

    output_file = os.path.join(output_dir, f"converted_{video_file[:-4]}.mp4")

    ffmpeg_args = {
        "both": [
            "ffmpeg",
            "-n",
            "-i",
            os.path.join(input_dir, video_file),
            "-movflags",
            "faststart",
            "-brand",
            "mp42",
            "-map",
            "0:v",
            "-map",
            "0:m:language:eng",
            "-c:v",
            "libx264",
            "-level:v",
            "4.0",
            "-c:a",
            "aac",
            output_file,
        ],
        "none": [
            "ffmpeg",
            "-n",
            "-i",
            os.path.join(input_dir, video_file),
            "-movflags",
            "faststart",
            "-brand",
            "mp42",
            "-map",
            "0:v",
            "-map",
            "0:m:language:eng",
            "-c:v",
            "copy",
            "-c:a",
            "copy",
            output_file,
        ],
        "audio_only": [
            "ffmpeg",
            "-n",
            "-i",
            os.path.join(input_dir, video_file),
            "-movflags",
            "faststart",
            "-brand",
            "mp42",
            "-map",
            "0:v",
            "-map",
            "0:m:language:eng",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            output_file,
        ],
        "video_only": [
            "ffmpeg",
            "-n",
            "-i",
            os.path.join(input_dir, video_file),
            "-movflags",
            "faststart",
            "-brand",
            "mp42",
            "-map",
            "0:v",
            "-map",
            "0:m:language:eng",
            "-c:v",
            "libx264",
            "-c:a",
            "copy",
            output_file,
        ],
    }

    if not audio and not video:
        LOGGER.info("MP4 only conversion")
        ffargs = ffmpeg_args["none"]
    elif audio and not video:
        LOGGER.info("Audio only conversion")
        ffargs = ffmpeg_args["audio_only"]
    elif not audio and video:
        LOGGER.info("Video only conversion")
        ffargs = ffmpeg_args["video_only"]
    else:
        LOGGER.info("Audio and Video conversion")
        ffargs = ffmpeg_args["both"]

    try:
        start_time = time.time()
        LOGGER.info(f"Beginning {video_file} conversion...")
        if dry_run is False:
            conversion_proc = subprocess.run(
                ffargs, check=True, stdout=subprocess.PIPE, universal_newlines=True,
            )
            LOGGER.debug(conversion_proc.stdout)
        LOGGER.info(
            f"FFMPEG completed conversion of {video_file} "
            f"in {seconds_to_time(int(time.time() - start_time))}s"
        )
        return True
    except Exception as ex:
        LOGGER.error(repr(ex))
        try:
            os.remove(output_file)
        except:
            pass
        return False


def codec_info(video_file: str) -> tuple:
    """ Get information about the video codec """
    # Check video codec with ffprobe
    ffprobe_args = {
        "video_codec": [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name",
            "-of",
            "default=nokey=1:noprint_wrappers=1",
            video_file,
        ],
        "audio_codec": [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_name",
            "-of",
            "default=nokey=1:noprint_wrappers=1",
            video_file,
        ],
    }

    video_codec_info = subprocess.run(
        ffprobe_args["video_codec"],
        check=True,
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )

    video_output = video_codec_info.stdout.rstrip("\r\n")

    audio_codec_info = subprocess.run(
        ffprobe_args["audio_codec"],
        check=True,
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )

    audio_output = audio_codec_info.stdout.rstrip("\r\n")

    return (audio_output, video_output)


def determine_encoding_method_and_convert(
    input_dir: str, output_dir: str, video_file: str, dry_run: bool = False
) -> bool:
    """
    Determines a video file's encoding method
    and runs the converter based on the encoding
    """
    audio_codec, video_codec = codec_info(os.path.join(input_dir, video_file))
    LOGGER.info(f"{video_file}: A - [{audio_codec}] V: [{video_codec}]")

    convert_audio = True
    convert_video = True

    if video_codec == "h264":
        convert_video = False
    if audio_codec == "aac":
        convert_audio = False

    return encode_video_ffmpeg(
        input_dir,
        output_dir,
        video_file,
        video=convert_video,
        audio=convert_audio,
        dry_run=dry_run,
    )


def encode_video_handbrake(input_dir: str, output_dir: str, video_file: str) -> bool:
    """
    Encodes the video to a web playable format using handbrake cli
    example:
      HandBrakeCLI -i vid.mkv -o /output/path/vid.mp4 --encoder x264 --vb 900 --ab 128 --optimize  # noqa: E501
    """
    LOGGER.info(f"Working on video file: {video_file}")
    converted_name = f"converted_{video_file[:-4]}.mp4"
    LOGGER.info(f"Output file will be: {os.path.join(output_dir, video_file)}")
    handbrake_params = [
        "HandBrakeCLI",
        "-i",
        os.path.join(input_dir, video_file),
        "-o",
        f"{os.path.join(output_dir, converted_name)}",
        "--encoder",
        "x264",
        "--vb",
        "900",
        "--ab",
        "128",
        "--optimize",
    ]
    try:
        start_time = time.time()
        subprocess.run(handbrake_params, check=True)
        LOGGER.info(
            f"{video_file} took {seconds_to_time(int(time.time() - start_time))}s"
        )
        return True
    except:  # noqa E722
        LOGGER.info(
            f"Error occurred trying to convert [{video_file}]; "
            f"Took {seconds_to_time(int(time.time() - start_time))}s"
        )
        return False


def seconds_to_time(sec: int) -> str:
    """
    Given seconds, convert it to high level days/hours/minutes/seconds
    Will output something like:
    00d:00h:01m:04s

    :param sec: Seconds to convert
    :return: String
    """
    day = int(sec // (24 * 3600))
    sec %= 24 * 3600
    hour = int(sec // 3600)
    sec %= 3600
    minutes = int(sec // 60)
    sec %= 60

    return f"{day:02d}d:{hour:02d}h:{minutes:02d}m:{int(sec):02d}s"


def main(args: argparse.Namespace) -> None:
    """ Converts MKV files to MP4 for web playback """

    LOGGER.info(f"Working with input directory {args.inputdir}")
    LOGGER.info(f"Outputting results to {args.outputdir}")
    LOGGER.info(f"Option delete source files == {args.delete_source}")

    # Look for files with these extensions only
    valid_exts = [".mkv"]

    files = [
        f
        for f in os.listdir(args.inputdir)
        if os.path.isfile(os.path.join(args.inputdir, f))
        and "converted_" not in f
        and Path(os.path.join(args.inputdir, f)).suffix in valid_exts
    ]

    failed = []
    succeeded = []

    LOGGER.info(f"Found {len(files)} unconverted files")
    LOGGER.debug(f"Files: {files}")

    start_time = time.time()
    for vid in files:
        # Encode with handbrake if requested
        if args.handbrake:
            LOGGER.info("Using HandbrakeCLI to convert videos")
            success = encode_video_handbrake(args.inputdir, args.outputdir, vid)
        else:  # Use FFMPEG to encode
            LOGGER.info("Using FFMPEG to convert videos")
            success = determine_encoding_method_and_convert(
                args.inputdir, args.outputdir, vid, dry_run=args.dry_run
            )
        if success:
            succeeded.append(vid)
            if not args.dry_run:
                LOGGER.info("Renaming source file with prefix 'converted_'")
                new_name = f"converted_{vid}"
                os.rename(
                    os.path.join(args.inputdir, vid),
                    os.path.join(args.inputdir, new_name),
                )
            # Delete the source video if the option was passed in
            if args.delete_source and not args.dry_run:
                LOGGER.info("Deleting source file")
                os.remove(os.path.join(args.inputdir, new_name))
        else:
            failed.append(vid)

    total_time = seconds_to_time(int(time.time() - start_time))
    LOGGER.info(f"Finished processing {len(files)} in {total_time}s")
    LOGGER.info(f"Failed: {failed}\nSucceeded: {succeeded}")


def setup_logging(log_level: str = "INFO") -> None:
    """ Sets up the application logger """
    global LOGGER

    if LOGGER is None:
        LOGGER = logging.getLogger("autoconvert")

    logging_level = getattr(logging, log_level)
    LOGGER.setLevel(logging_level)

    fh = logging.FileHandler("autoconverter.log")
    fh.setLevel(logging_level)

    ch = logging.StreamHandler()
    ch.setLevel(logging_level)

    # create formatter and add it to the handlers
    formatter = logging.Formatter(
        "[%(asctime)s] %(filename)s:%(lineno)d - %(levelname)s - %(message)s"
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    # add the handlers to the logger
    LOGGER.addHandler(fh)
    LOGGER.addHandler(ch)
    LOGGER.info(f"Logger initialized with log level: {log_level}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("inputdir", help="The directory with files to convert")
    parser.add_argument(
        "outputdir", help="The directory where the converted files will go"
    )
    parser.add_argument(
        "--log-level", help="Set the application log level", default="INFO"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not do any conversion but show what will be done instead",
    )
    parser.add_argument(
        "--delete_source",
        action="store_true",
        help="Delete the source file after conversion complete",
    )
    parser.add_argument(
        "--handbrake",
        action="store_true",
        help="Use handbrake to convert videos instead of FFMPEG",
    )

    args = parser.parse_args()

    setup_logging(args.log_level)
    main(args)
