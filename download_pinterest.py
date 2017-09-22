#! /usr/bin/env python
import sys
import os
import argparse
from math import ceil
import threading
import concurrent.futures
from time import sleep
import urllib.request
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import selenium.webdriver.support.ui as ui
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
DEBUG = True



def find_num_pins(body):
    spans = body.find_elements_by_tag_name("span")
    num_elements = 0
    for span in spans:
        if "Pins" in span.text:
            num_elements = int(span.text.split(" ")[0])
    return num_elements

def find_board_name(board_url):
    name_idx = -1
    if board_url[-1] == "/":
        name_idx = -2
    return board_url.split("/")[name_idx]

def find_all_visible_low_res(body):
    low_res_imgs = body.find_elements(By.XPATH, "//a[@href]")
    low_res_imgs = [link.get_attribute("href") for link in low_res_imgs]
    low_res_imgs = [link for link in low_res_imgs if "/pin/" in link]
    return low_res_imgs, len(low_res_imgs)

def download_high_res(high_res_source, img_id, download_folder):
    extension = high_res_source.split(".")[-1]
    print(f"Going to download {high_res_source} to {download_folder}")
    try:
        urllib.request.urlretrieve(high_res_source, os.path.join(download_folder, f"pin_{img_id}.{extension}"))
    except urllib.request.ContentTooShortError:
        print(f"Connection died during download of Pin {img_id}.")


class PinterestDownloader(object):

    def __init__(self, browser_type="chrome"):
        self.browser = None
        if "chrome" in browser_type:
            self.browser = webdriver.Chrome()
        else:
            raise ValueError("Unsupported browser type")

    def load_board(self, board_url, download_folder,
                   num_pins=None, board_name=None, min_resolution=None,
                   skip_tolerance=float('inf')):
        self.browser.get(board_url)
        #sleep(1) # Let the page load bad style

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
            print("Found a file with content that was previously downloaded.")
            with open(memory_file_name, 'r') as f:
                previously_downloaded = [line.strip() for line in f.readlines()]
        else:
            previously_downloaded = []

        # Pick a minimal image resolution
        min_x, min_y = [int(r) for r in min_resolution.split("x")]

        print(f"Will download {num_pins} pins from {board_name} to {download_folder}")

        downloaded_this_time = []
        with concurrent.futures.ThreadPoolExecutor(3) as consumers:
            num_srcs = 0
            num_skipped = 0
            nr_previously_downloaded = len(previously_downloaded)

            while len(downloaded_this_time) < num_pins and num_skipped < skip_tolerance:
                low_res_srcs, new_num_srcs = find_all_visible_low_res(body)
                end_idx = -1 if num_pins > new_num_srcs else num_pins
                # Submit the newly found pins to the download queue
                for i, low_res_link in enumerate(low_res_srcs[num_srcs:end_idx]):
                    if low_res_link not in previously_downloaded:
                        print(f"Submitting {low_res_link}")
                        future = consumers.submit(extract_high_res, low_res_link, i + nr_previously_downloaded, download_folder)
                        downloaded_this_time.append(low_res_link)
                    else:
                        print("Skipped")
                        num_skipped += 1

                num_srcs = new_num_srcs
                if num_srcs < num_pins:
                    print(f"Scrolling, because {nr_srcs} < {num_pins}")
                    self.scroll_down(times=7)


        if not DEBUG:
            with open(memory_file_name, 'w+') as f:
                for source in downloaded_this_time:
                    f.write(f"{source}\n")



    def scroll_down(self, times, sleep_time=0.5):
        scroll_js = "let height = document.body.scrollHeight; window.scrollTo(0, height);"
        for _ in range(times):
            self.browser.execute_script(scroll_js)
            sleep(sleep_time)

def extract_high_res(low_res_link, img_id, download_folder):
    print("extract high res")
    fp = urllib.request.urlopen(low_res_link)
    html = fp.read().decode("utf8")
    fp.close()
    soup = BeautifulSoup(html, "html.parser")
    high_res_source = soup.find("img")["src"]
    print(high_res_source)
    download_high_res(high_res_source, img_id, download_folder)
    return high_res_source




def parse_cmd():
    parser = argparse.ArgumentParser(description='Download a pinterest board or tag page.')
    parser.add_argument(dest="link", help="Link to the pinterest page you want to download.")
    parser.add_argument(dest="dest_folder", help="Folder into which the board will be downloaded.")
    parser.add_argument("-n", "--name", default=None, required=False, dest="board_name",
                        help="The name for the folder the board is downloaded in. If not given, will try to extract board name from pinterest.")
    parser.add_argument("-c", "--count", default=None, type=int, required=False, dest="num_pins",
                        help="Download only the first 'c' pins found on the page.")
    parser.add_argument("-r", "--resolution", default="0x0", required=False, dest="min_resolution",
                        help="Minimal resolution to download an image. Both dimension must be bigger than the given dimensions. Input as widthxheight.")
    args = parser.parse_args()

    if not os.path.isdir(args.dest_folder):
        raise ValueError("The folder you provided does not exist: {}".format(args.dest_folder))

    return args

if __name__ == "__main__":
    arguments = parse_cmd()
    dl = PinterestDownloader()
    dl.load_board(board_url=arguments.link, download_folder=arguments.dest_folder,
                  num_pins=arguments.num_pins, board_name=arguments.board_name,
                  min_resolution=arguments.min_resolution)
