#! /usr/bin/env python
import signal

import argparse

from pinterest_downloader import *


def handle_sig_int(signal, frame):
    """
    Exit gracefully on CTRL+C or other source of SIGINT.

    :param signal: The signal that was received.
    :param frame: The stack frame in which the signal was received.
    :return None.
    """
    print("Aborted, download may be incomplete.")
    sys.exit(0)


def parse_cmd():
    """
    Parses command line flags that control how pinterest will be scraped.
    Start the script with the '-h' option to read about all the arguments.

    :returns a namespace populated with the arguments supplied (or default arguments, if given).
    """
    parser = argparse.ArgumentParser(description="""Download a pinterest board or tag page. When downloading a tag page,
    and no maximal number of downloads is provided, stop the script with CTRL+C.""")
    # Required arguments
    parser.add_argument(dest="link", help="Link to the pinterest page you want to download.")
    parser.add_argument(dest="dest_folder",
                        help="""Folder into which the board will be downloaded. Folder with board name is automatically created or found, if it already exists.""")
    # Optional arguments
    parser.add_argument("-n", "--name", default=None, required=False, dest="board_name",
                        help="The name for the folder the board is downloaded in. If not given, will try to extract board name from pinterest.")
    parser.add_argument("-c", "--count", default=None, type=int, required=False, dest="num_pins",
                        help="""Download only the first 'c' pins found on the page. If bigger than the number of pins on the board, all pins in the board will be downloaded. The default is to download all pins.""")
    parser.add_argument("-j", "--threads", default=4, type=int, required=False, dest="nr_threads",
                        help="Number of threads that download images in parallel.")
    parser.add_argument("-r", "--resolution", default="0x0", required=False, dest="min_resolution",
                        help="""Minimal resolution to download an image. Both dimension must be bigger than the given dimensions. Input as widthxheight.""")
    parser.add_argument("-m", "--mode", default="individual", required=False, choices=["individual", "area"], dest="mode",
                        help="""Pick how the resolution limit is treated:
                             'individual': Both image dimensions must be bigger than the given resolution.
                             'area': The area of the image must be bigger than the provided resolution.""")
    parser.add_argument("-s" "--skip-limit", default=float("inf"), type=int, required=False, dest="skip_limit",
                        help="""Abort the download after so many pins have been skipped. A pin is skipped if it was already present in the download folder.""")
    args = parser.parse_args()

    return args


if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_sig_int)
    arguments = parse_cmd()

    with PinterestDownloader(num_threads=arguments.nr_threads,
                            min_resolution=arguments.min_resolution,
                            size_compare_mode=arguments.mode) as dl:
        dl.download_board(board_url=arguments.link, download_folder=arguments.dest_folder,
                      num_pins=arguments.num_pins, board_name=arguments.board_name,
                      skip_tolerance=arguments.skip_limit)
