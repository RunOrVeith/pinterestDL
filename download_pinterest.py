#! /usr/bin/env python

import os
import argparse
from math import ceil
import threading
import concurrent.futures
import urllib.request
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import selenium.webdriver.support.ui as ui
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from datetime import datetime
from time import sleep
from PIL import Image
DEBUG = True



def find_num_pins(body):
    spans = body.find_elements_by_tag_name("span")
    num_elements = float("inf")  # If we download from a tag page, return as many as possible
    for span in spans:
        if "Pins" in span.text:
            num_elements = int(span.text.split(" ")[0])
            break

    return num_elements

def find_board_name(board_url):
    if "?q=" in board_url:
        # We're downloading a tag page, find the search tags in the url
        name_start = board_url.index("=") + 1
        name_end = board_url.index("&")
        return board_url[name_start:name_end]
    else:
        # We're downloading a board, extract the title
        name_idx = -1
        if board_url[-1] == "/":
            name_idx = -2
        return board_url.split("/")[name_idx]

def find_high_res_links(body):
    soup = BeautifulSoup(body.get_attribute("outerHTML"), "html.parser")
    low_res_imgs = soup.find_all("img")
    return [img["src"] for img in low_res_imgs], len(low_res_imgs)

def download_high_res(high_res_source, download_folder, verify_size):
    title = high_res_source.split("--")[-1]
    if not title:
        extension = high_res_source.split(".")[-1]
        title = str(datetime.now()) + f".{extension}"
    destination = os.path.join(download_folder, title)
    try:
        urllib.request.urlretrieve(high_res_source, destination)
    except urllib.request.ContentTooShortError:
        print(f"Connection died during download of Pin {title}.")
        return False

    img = Image.open(destination)
    width, height = img.size
    # If the image was smaller then we want, we delete it again
    if not verify_size(width, height):
        os.remove(destination)
        return False
    return True

def get_size_verifier(min_x, min_y, mode):
    def by_area(width, height):
        return width * height >= min_x*min_y
    def by_both(width, height):
        return width >= min_x and height >= min_y
    def anything_goes(width, height):
        return True
    if mode == "area":
        return by_area
    elif mode == "individual":
        return by_both
    else:
        return anything_goes

class PinterestDownloader(object):

    def __init__(self, browser_type="chrome", num_threads=4,
                 min_resolution="0x0",size_compare_mode=None):
        self.browser = None
        if "chrome" in browser_type:
            self.browser = webdriver.Chrome()
        else:
            raise ValueError("Unsupported browser type")
        self.num_threads = num_threads
        # Pick a minimal image resolution
        min_x, min_y = [int(r) for r in min_resolution.split("x")]
        self.size_verifier = get_size_verifier(min_x, min_y, size_compare_mode)

    def load_board(self, board_url, download_folder,
                   board_name=None, num_pins=None,
                   skip_tolerance=float('inf')):

        self.browser.get(board_url)
        body = self.browser.find_element_by_tag_name("body")

        if board_name is None:
            board_name = find_board_name(board_url)

        # Find the number of pins to download
        _num_pins = find_num_pins(body)
        if num_pins is None:
            num_pins = _num_pins
        else:
            num_pins = min(_num_pins, num_pins)

        # Choose the destination folder so that we can download into an existing folder
        if os.path.basename(download_folder) != board_name:
            download_folder = os.path.join(download_folder, board_name)
            os.makedirs(download_folder, exist_ok=True)

        # Check if we can find a file that tells us what we have already downloaded
        memory_file_name = os.path.join(download_folder, f".memory_{board_name}")
        if os.path.isfile(memory_file_name):
            print(f"Found a file with content that was previously downloaded: {memory_file_name}.")
            with open(memory_file_name, 'r') as f:
                previously_downloaded = [line.strip() for line in f.readlines()]
        else:
            previously_downloaded = []

        print(f"Will download {num_pins} pins from {board_name} to {download_folder}")


        # Extract sources of images and download the found ones in parallel
        # Pinterest loads further images with JS, so selenium needs to scroll
        # down to load more images
        num_srcs = 0
        num_skipped = 0
        downloaded_this_time = []
        nr_previously_downloaded = len(previously_downloaded)
        with concurrent.futures.ThreadPoolExecutor(self.num_threads) as consumers:
            while len(downloaded_this_time) < num_pins and num_skipped < skip_tolerance and num_srcs < num_pins:
                high_res_srcs, new_num_srcs = find_high_res_links(body)
                # Submit only the newly found pins to the download queue
                end_idx = -1 if num_pins > new_num_srcs else num_pins + 1
                future_to_url = {}
                for i, high_res_link in enumerate(high_res_srcs[num_srcs:end_idx]):
                    if high_res_link not in previously_downloaded:
                        future = consumers.submit(download_high_res,
                                                  high_res_source=high_res_link,
                                                  download_folder=download_folder,
                                                  verify_size=self.size_verifier)
                    else:
                        num_skipped += 1
                    for fut in concurrent.futures.as_completed(future_to_url):
                        url = future_to_url[fut]
                        downloaded = future.result()
                        if downloaded:
                            downloaded_this_time.append(url)


                # Scroll down if we have not downloaded enough images yet
                num_srcs = new_num_srcs
                if num_srcs < num_pins:
                    print(f"Need to scroll down")
                    self.scroll_down(times=7)
                    body = self.browser.find_element_by_tag_name("body")

        self.browser.close()
        # Write the downloaded images to the memory file.
        if not DEBUG:
            with open(memory_file_name, 'w+') as f:
                for source in downloaded_this_time:
                    f.write(f"{source}\n")

    def scroll_down(self, times, sleep_time=0.5):
        scroll_js = "let height = document.body.scrollHeight; window.scrollTo(0, height);"
        for _ in range(times):
            self.browser.execute_script(scroll_js)
            sleep(sleep_time)


def parse_cmd():
    parser = argparse.ArgumentParser(description='Download a pinterest board or tag page.')
    parser.add_argument(dest="link", help="Link to the pinterest page you want to download.")
    parser.add_argument(dest="dest_folder", help="Folder into which the board will be downloaded.")
    parser.add_argument("-n", "--name", default=None, required=False, dest="board_name",
                        help="The name for the folder the board is downloaded in. If not given, will try to extract board name from pinterest.")
    parser.add_argument("-c", "--count", default=None, type=int, required=False, dest="num_pins",
                        help="Download only the first 'c' pins found on the page.")
    parser.add_argument("-j", "--threads", default=4, type=int, required=False, dest="nr_threads",
                        help="Number of threads that download images in parallel.")
    parser.add_argument("-r", "--resolution", default="0x0", required=False, dest="min_resolution",
                        help="Minimal resolution to download an image. Both dimension must be bigger than the given dimensions. \
                              Input as widthxheight.")
    parser.add_argument("-m", "--mode", default="individual", required=False, choices=["individual", "area"], dest="mode",
                        help="Pick how the resolution limit is treated: \
                        'individual': Both image dimensions must be bigger than the given resolution. \
                        'area': The area of the image must be bigger than the provided resolution.")
    args = parser.parse_args()

    if not os.path.isdir(args.dest_folder):
        raise ValueError("The folder you provided does not exist: {}".format(args.dest_folder))

    return args

if __name__ == "__main__":
    arguments = parse_cmd()
    dl = PinterestDownloader(num_threads=arguments.nr_threads,
                            min_resolution=arguments.min_resolution,
                            size_compare_mode=arguments.mode)
    dl.load_board(board_url=arguments.link, download_folder=arguments.dest_folder,
                  num_pins=arguments.num_pins, board_name=arguments.board_name)
