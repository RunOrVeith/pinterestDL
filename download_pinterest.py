#! /usr/bin/env python

import sys
import os
import signal
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
from stateful_ordered_set import *

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

def handle_download_report(future, url):
    download_report = future.result()
    skipped = 0
    if not download_report["downloaded"]:
        reason = download_report["reason"]
        if reason == "err_present":
            skipped = 1
        elif reason == "err_timeout":
            print(f"Could not download {url}: {reason}")
            skipped = 1
    return skipped

def retrieve_bord_info(board_name, board_url, download_folder, num_pins, body):
    if board_name is None:
        board_name = find_board_name(board_url)

    # Find the number of pins to download, minimum between available pins and requested pins
    num_available_pins = find_num_pins(body)
    if num_pins is None:
        num_pins = num_available_pins
    else:
        num_pins = min(num_available_pins, num_pins)

    # Choose the destination folder so that we can download into an existing folder
    if os.path.basename(download_folder) != board_name:
        download_folder = os.path.join(download_folder, board_name)
        os.makedirs(download_folder, exist_ok=True)

    return board_name, num_pins, download_folder

class Downloader(object):

    def __init__(self, download_folder, size_verifier):
        self.download_folder = download_folder
        self.verify_size = size_verifier
        self.previously_downloaded = os.listdir(self.download_folder)

    def __call__(self, *args, **kwargs):
        return self.download_high_res(*args, **kwargs)

    def download_high_res(self, high_res_source):
        stripped_slashes = high_res_source.split("/")[-1]
        title = stripped_slashes.split("--")[-1]

        status_report = {"downloaded": True, "reason": "valid"}

        if title in self.previously_downloaded:
            status_report["downloaded"] = False
            status_report["reason"] = "err_present"
        else:
            destination = os.path.join(self.download_folder, title)
            try:
                urllib.request.urlretrieve(high_res_source, destination)
                img = Image.open(destination)
                width, height = img.size
                # If the image was smaller then we want, we delete it again
                if not self.verify_size(width, height):
                    os.remove(destination)
                    status_report["downloaded"] == False
                    status_report["reason"] == "err_size"
            except urllib.request.ContentTooShortError:
                print(f"Connection died during download of Pin {title}.")
                status_report["downloaded"] = False
                status_report["reason"] = "err_timeout"

        return status_report



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
        body = self.update_body_html()
        board_name, num_pins, download_folder = retrieve_bord_info(board_name=board_name,
                                                                   download_folder=download_folder,
                                                                   board_url=board_url,
                                                                   num_pins=num_pins,
                                                                   body=body)

        # Extract sources of images and download the found ones in parallel
        # Pinterest loads further images with JS, so selenium needs to scroll
        # down to load more images
        num_srcs = 0
        num_skipped = 0
        downloaded_this_time = 0
        url_cache = MemorySet()
        downloader = Downloader(download_folder, self.size_verifier)

        with concurrent.futures.ThreadPoolExecutor(self.num_threads) as consumers:
            print("Starting download...")

            while downloaded_this_time < num_pins and num_skipped < skip_tolerance:

                high_res_srcs, new_num_srcs = find_high_res_links(body)
                retrieved_new_urls = url_cache.update(high_res_srcs)
                if not retrieved_new_urls:
                    print(f"Stopped, no new pins found. Skipped {num_skipped} pins.")
                    break
                else:
                    print("Found some pins")

                future_to_url = {}
                for high_res_link in url_cache:

                    future = consumers.submit(downloader,
                                              high_res_source=high_res_link)
                    future_to_url[future] = high_res_link
                    if len(future_to_url) + downloaded_this_time == num_pins:
                        break

                for fut in concurrent.futures.as_completed(future_to_url):
                    url = future_to_url[fut]
                    skipped = handle_download_report(future=fut, url=url)
                    num_skipped += 1 if skipped else 0
                    downloaded_this_time += 0 if skipped else 1

                # Scroll down if we have not downloaded enough images yet
                num_srcs = new_num_srcs
                if num_srcs < num_pins:
                    print(f"Need to scroll down because {num_srcs} < {num_pins}")
                    body =  self.scroll_down_for_new_body(times=7)

        if num_skipped >= skip_tolerance:
            print("Skip limit reached. Stopping.")
        print(f"Downloaded {downloaded_this_time} pins to {download_folder}. \
              Skipped {num_skipped} pins.")
        self.browser.close()

    def update_body_html(self):
        return self.browser.find_element_by_tag_name("body")

    def scroll_down_for_new_body(self, times, sleep_time=0.5):
        scroll_js = "let height = document.body.scrollHeight; window.scrollTo(0, height);"
        for _ in range(times):
            self.browser.execute_script(scroll_js)
            sleep(sleep_time)
        return self.update_body_html()


def handle_signals(signal, frame):
    print("Aborted, download may be incomplete.")
    sys.exit(0)

def parse_cmd():
    parser = argparse.ArgumentParser(description='Download a pinterest board or tag page.')
    parser.add_argument(dest="link", help="Link to the pinterest page you want to download.")
    parser.add_argument(dest="dest_folder", help="Folder into which the board will be downloaded.")
    parser.add_argument("-n", "--name", default=None, required=False, dest="board_name",
                        help="The name for the folder the board is downloaded in. If not given, will try to extract board name from pinterest.")
    parser.add_argument("-c", "--count", default=None, type=int, required=False, dest="num_pins",
                        help="Download only the first 'c' pins found on the page. If bigger than the number of pins on the board, \
                             all pins in the board will be downloaded. The default is to download all pins.")
    parser.add_argument("-j", "--threads", default=4, type=int, required=False, dest="nr_threads",
                        help="Number of threads that download images in parallel.")
    parser.add_argument("-r", "--resolution", default="0x0", required=False, dest="min_resolution",
                        help="Minimal resolution to download an image. Both dimension must be bigger than the given dimensions. \
                              Input as widthxheight.")
    parser.add_argument("-m", "--mode", default="individual", required=False, choices=["individual", "area"], dest="mode",
                        help="Pick how the resolution limit is treated: \
                             'individual': Both image dimensions must be bigger than the given resolution. \
                             'area': The area of the image must be bigger than the provided resolution.")
    parser.add_argument("-s" "--skip-limit", default=float("inf"), type=int, required=False, dest="skip_limit",
                        help="Abort the download after so many pins have been skipped. A pin is skipped if it was already present in \
                              the download folder.")
    args = parser.parse_args()

    if not os.path.isdir(args.dest_folder):
        raise ValueError("The folder you provided does not exist: {}".format(args.dest_folder))

    return args

if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_signals)
    arguments = parse_cmd()
    dl = PinterestDownloader(num_threads=arguments.nr_threads,
                            min_resolution=arguments.min_resolution,
                            size_compare_mode=arguments.mode)
    dl.load_board(board_url=arguments.link, download_folder=arguments.dest_folder,
                  num_pins=arguments.num_pins, board_name=arguments.board_name,
                  skip_tolerance=arguments.skip_limit)
