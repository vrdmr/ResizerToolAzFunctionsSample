import os
import shutil
import ssl
import time
import tempfile
from urllib.parse import urlparse
from urllib.request import urlretrieve

import azure.functions as func
import PIL
from PIL import Image


target_sizes = [200]
ssl._create_default_https_context = ssl._create_unverified_context


class ThumbnailMakerService(object):
    def __init__(self, home_dir='.'):
        self.home_dir = tempfile.gettempdir()
        self.input_dir = self.home_dir + os.path.sep + 'incoming'
        self.output_dir = self.home_dir + os.path.sep + 'outgoing'

    def download_images(self, img_url):
        # validate inputs
        if not img_url:
            return
        os.makedirs(self.input_dir, exist_ok=True)

        start = time.perf_counter()
        # download each image and save to the input dir
        img_filename = urlparse(img_url).path.split('/')[-1]
        urlretrieve(img_url, self.input_dir + os.path.sep + img_filename)
        end = time.perf_counter()

    def perform_resizing(self):
        # validate inputs
        if not os.listdir(self.input_dir):
            return
        os.makedirs(self.output_dir, exist_ok=True)
        num_images = len(os.listdir(self.input_dir))

        start = time.perf_counter()
        for filename in os.listdir(self.input_dir):
            orig_img = Image.open(self.input_dir + os.path.sep + filename)
            for basewidth in target_sizes:
                img = orig_img
                # calculate target height of the resized image to maintain the aspect ratio
                wpercent = (basewidth / float(img.size[0]))
                hsize = int((float(img.size[1]) * float(wpercent)))
                # perform resizing
                img = img.resize((basewidth, hsize), PIL.Image.LANCZOS)

                # save the resized image to the output dir with a modified file name
                new_filename = os.path.splitext(filename)[0] + \
                    '_' + str(basewidth) + os.path.splitext(filename)[1]
                img.save(self.output_dir + os.path.sep + new_filename)

            os.remove(self.input_dir + os.path.sep + filename)
        end = time.perf_counter()

    def make_thumbnail(self, img_url):
        start = time.perf_counter()

        self.download_images(img_url)
        self.perform_resizing()

        end = time.perf_counter()
        self._cleanup_temp_directories()
        return end - start

    def _cleanup_temp_directories(self):
        shutil.rmtree(self.input_dir)
        shutil.rmtree(self.output_dir)


tn_maker = ThumbnailMakerService()


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse(f'Please pass an image name in the body. Expected body: {"image_url":"<url>"}. Sample image: https://pixy.org/src/19/193722.jpg', status_code=400)
    return func.HttpResponse(f"Resized the image passed in {tn_maker.make_thumbnail(req_body['image_url'])} seconds", status_code=200)
