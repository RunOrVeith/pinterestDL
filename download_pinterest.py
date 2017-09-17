#! /usr/bin/env python
import sys
import os
from math import ceil
from time import sleep
import urllib.request
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import selenium.webdriver.support.ui as ui
from selenium.webdriver.common.by import By

def find_num_pins(body):
    spans = body.find_elements_by_tag_name("span")
    num_elements = 0
    for span in spans:
        if "Pins" in span.text:
            num_elements = int(span.text.split(" ")[0])
    return num_elements

def find_all_visible_low_res(body):
    low_res_imgs = body.find_elements(By.XPATH, "//a[@href]")
    low_res_imgs = [link.get_attribute("href") for link in low_res_imgs]
    low_res_imgs = [link for link in low_res_imgs if "/pin/" in link]
    return low_res_imgs


class PinterestDownloader(object):

    def __init__(browser_type="chrome"):
        self.browser = None
        if "chrome" in browser_type:
            self.browser(webdriver.Chrome())

    def load_board(self, board_url):
        self.browser.get(board_url)
        sleep(1) # Let the page load bad style

        body = self.browser.find_element_by_tag_name("body")
        num_pins = find_num_pins(body)

        low_res_srcs = find_all_visible_low_res()
        while len(low_res_srcs) < num_pins:
            self.scroll_down(times=7)
            low_res_srcs = find_all_low_res()

        if len(low_res_srcs) > num_pins:
            print("Found more links than pins, will probably download some random images.")


    def scroll_down(self, times, sleep_time=0.5):
        scroll_js = "let height = document.body.scrollHeight; window.scrollTo(0, height);"
        for _ in range(times):
            self.browser.execute_script(scroll_js)
            sleep(sleep_time)


dl = PinterestDownloader()
dl.load_board("https://www.pinterest.de/VeithOrFlight/images-of-my-mind/")

def old_way():
    cmd_args = sys.argv
    input_file = cmd_args[1]
    download_folder = cmd_args[2]
    if not os.path.isdir(download_folder):
        raise ValueError("The folder you provided does not exist: {}".format(download_folder))
    if not os.path.isfile(input_file):
        raise ValueError("The file you provided does not exist {}".format(input_file))

    with open(input_file, 'r') as f:
        sources = f.read()
        sources = sources.split(",")

        for i, src in enumerate(sources[2:]):
            if i % 10 == 0:
                print("Downloading files {} - {}".format(i, i + 10))
            extension = src.split(".")[-1]
            urllib.request.urlretrieve (src, os.path.join(download_folder, f"img_{i}.{extension}"))
