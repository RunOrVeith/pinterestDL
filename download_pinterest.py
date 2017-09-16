#! /usr/bin/env python
import sys
import os
from time import sleep
import urllib.request
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import selenium.webdriver.support.ui as ui
from selenium.webdriver.common.by import By

class PinterestDownloader(object):

    def load_board(self, board_url):
        browser = webdriver.Chrome()
        browser.get(board_url)
        sleep(1) # Let the page load

        body = browser.find_element_by_tag_name("body")

        spans = body.find_elements_by_tag_name("span")
        num_scrolls = 0
        for span in spans:
            if "Pins" in span.text:
                num_scrolls = int(span.text.split(" ")[0])
        #self._scroll_down(body, num_scrolls // 10)
        while len(browser.find_elements(By.XPATH, "//a[starts-with(@href, '/pin/')]")) < num_scrolls:
            self._scroll_down(body, 1)
        print("Done scrolling")
        low_res_imgs = browser.find_elements(By.XPATH, "//a[starts-with(@class, 'pinLink')]")
        low_res_sources = []
        for low_res_img in low_res_imgs:
            print(low_res_img.get_attribute("href"))
        print(low_res_sources)


    def _scroll_down(self, element, nr_scrolls, wait_between_scrolls=0.1):
        for _ in range(nr_scrolls):
            element.send_keys(Keys.PAGE_DOWN)
            sleep(wait_between_scrolls)

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
