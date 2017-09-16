#! /usr/bin/env python
import sys
import os
import urllib.request

if __name__ == "__main__":
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
