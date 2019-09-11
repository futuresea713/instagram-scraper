import argparse
from instagram_scraper import InstagramScraper
import re
import sys
import textwrap
import cv2
import glob
import random
from random import randrange
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from multiprocessing import Pool
import multiprocessing
import numpy as np
import threading
from selenium.webdriver.chrome.options import Options


threadLocal = threading.local()
#os.remove("imgurls.txt")
# files = glob.glob('result/*')
# for f in files:
#     os.remove(f)

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

import warnings

import threading

try:
    reload(sys)  # Python 2.7
    sys.setdefaultencoding("UTF8")
except NameError:
    pass

warnings.filterwarnings('ignore')

input_lock = threading.RLock()

DEFAULT_DOWNLOAD_LIMIT = 1000

if not os.path.exists("result"):
    os.makedirs("result")

def overlay_transparent(background_img, img_to_overlay_t, x, y, overlay_size=None):

    bg_img = background_img.copy()

    if overlay_size is not None:
        img_to_overlay_t = cv2.resize(img_to_overlay_t.copy(), overlay_size)

    # Extract the alpha mask of the RGBA image, convert to RGB
    b, g, r, a = cv2.split(img_to_overlay_t)
    overlay_color = cv2.merge((b, g, r))

    # Apply some simple filtering to remove edge noise
    mask = cv2.medianBlur(a, 5)

    h, w, _ = overlay_color.shape
    roi = bg_img[y:y + h, x:x + w]

    # Black-out the area behind the logo in our original ROI
    img1_bg = cv2.bitwise_and(roi.copy(), roi.copy(), mask=cv2.bitwise_not(mask))

    # Mask out the logo from the logo image.
    img2_fg = cv2.bitwise_and(overlay_color, overlay_color, mask=mask)

    # Update the original image with our new ROI
    bg_img[y:y + h, x:x + w] = cv2.add(img1_bg, img2_fg)

    return bg_img



def get_driver():
    driver = getattr(threadLocal, 'driver', None)
    if driver is None:
        options = Options()
        options.add_experimental_option("excludeSwitches",
                                        ["ignore-certificate-errors", "safebrowsing-disable-download-protection",
                                         "safebrowsing-disable-auto-update", "disable-client-side-phishing-detection"])

        options.add_argument('--disable-infobars')
        options.add_argument('--disable-extensions')
        options.add_argument('--profile-directory=Default')
        options.add_argument("--incognito")
        options.add_argument("--disable-plugins-discovery")
        prefs = {'profile.default_content_setting_values.automatic_downloads': 1}
        options.add_experimental_option("prefs", prefs)
        #options.add_argument("--headless")
        driver = webdriver.Chrome('chromedriver', options=options)
        setattr(threadLocal, 'driver', driver)
        return driver





def UploadingImage(all_imgs):
    try:

        driver = get_driver()
        url = "https://imgbox.com"
        driver.get(url)
        try:
            uploadbutton =  driver.find_element_by_css_selector("span.btn.btn-warning.fileinput-button.select-files-button-large")

            input = uploadbutton.find_element_by_tag_name("input")
            imgs = [ os.getcwd() + "\\" + s  for s in all_imgs]
            input.send_keys('\n'.join(imgs))
            time.sleep(1)
            types = driver.find_elements_by_css_selector("div.btn-group.bootstrap-select.span12")
            types[0].click()
            time.sleep(1)
            contenttype = driver.find_elements_by_css_selector("ul.dropdown-menu.inner.selectpicker")
            liarr = contenttype[0].find_elements_by_tag_name("li")
            for type in liarr:
                if type.text == "Family Safe Content":
                    type.click()
                    time.sleep(1)
                    break

            types[1].click()
            time.sleep(1)
            liarr = contenttype[1].find_elements_by_tag_name("li")
            for type in liarr:
                if type.text == "800x800 pixel (square)":
                    type.click()
                    time.sleep(1)
                    break
            submit = driver.find_element_by_id("fake-submit-button")
            submit.click()
            time.sleep(1)
            container = WebDriverWait(driver, 10000).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.boxed-content.thumb-container")))
            allimage = container.find_elements_by_tag_name("img")
            string = ""
            for img in allimage:
                imgsrc = img.get_attribute("src")
                string += imgsrc
                string += "|"
            filenm = "imgurls.txt"
            with open(filenm, "a", encoding="utf8") as f:
                f.write(string)

        except:
            print("uploading error")
            driver.close()
        driver.close()
    except:
        pass



def main():
    parser = argparse.ArgumentParser(
        description="instagram-scraper scrapes and downloads an instagram user's photos and videos.",
        epilog=textwrap.dedent("""
        You can hide your credentials from the history, by reading your
        username from a local file:

        $ instagram-scraper @insta_args.txt user_to_scrape

        with insta_args.txt looking like this:
        -u=my_username
        -p=my_password

        You can add all arguments you want to that file, just remember to have
        one argument per line.

        Customize filename:
        by adding option --template or -T
        Default is: {urlname}
        And there are some option:
        {username}: Instagram user(s) to scrape.
        {shortcode}: post shortcode, but profile_pic and story are none.
        {urlname}: filename form url.
        {mediatype}: type of media.
        {datetime}: date and time that photo/video post on,
                     format is: 20180101 01h01m01s
        {date}: date that photo/video post on,
                 format is: 20180101
        {year}: format is: 2018
        {month}: format is: 01-12
        {day}: format is: 01-31
        {h}: hour, format is: 00-23h
        {m}: minute, format is 00-59m
        {s}: second, format is 00-59s

        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        fromfile_prefix_chars='@')

    parser.add_argument('username', help='Instagram user(s) to scrape', nargs='*')
    parser.add_argument('-limit',
                        '-l',
                        help='Number of files to generate (default: %s)'
                             % DEFAULT_DOWNLOAD_LIMIT,
                        type=int
                        )
    parser.add_argument('--destination', '-d', default='./', help='Download destination')
    parser.add_argument('--login-user', '--login_user', '-u', default=None, help='Instagram login user')
    parser.add_argument('--login-pass', '--login_pass', '-p', default=None, help='Instagram login password')
    parser.add_argument('--followings-input', '--followings_input', action='store_true', default=False,
                        help='Compile list of profiles followed by login-user to use as input')
    parser.add_argument('--followings-output', '--followings_output',
                        help='Output followings-input to file in destination')
    parser.add_argument('--filename', '-f', help='Path to a file containing a list of users to scrape')
    parser.add_argument('--quiet', '-q', default=False, action='store_true', help='Be quiet while scraping')
    parser.add_argument('--maximum', '-m', type=int, default=0, help='Maximum number of items to scrape')
    parser.add_argument('--retain-username', '--retain_username', '-n', action='store_true', default=False,
                        help='Creates username subdirectory when destination flag is set')
    parser.add_argument('--media-metadata', '--media_metadata', action='store_true', default=False,
                        help='Save media metadata to json file')
    parser.add_argument('--profile-metadata', '--profile_metadata', action='store_true', default=False,
                        help='Save profile metadata to json file')
    parser.add_argument('--proxies', default={}, help='Maximum number of items to scrape')
    parser.add_argument('--include-location', '--include_location', action='store_true', default=False,
                        help='Include location data when saving media metadata')
    parser.add_argument('--media-types', '--media_types', '-t', nargs='+', default=['image', 'video', 'story'],
                        help='Specify media types to scrape')
    parser.add_argument('--latest', action='store_true', default=False, help='Scrape new media since the last scrape')
    parser.add_argument('--latest-stamps', '--latest_stamps', default=None,
                        help='Scrape new media since timestamps by user in specified file')
    parser.add_argument('--cookiejar', '--cookierjar', default=None,
                        help='File in which to store cookies so that they can be reused between runs.')
    parser.add_argument('--tag', action='store_true', default=False, help='Scrape media using a hashtag')
    parser.add_argument('--filter', default=None, help='Filter by tags in user posts', nargs='*')
    parser.add_argument('--location', action='store_true', default=False, help='Scrape media using a location-id')
    parser.add_argument('--search-location', action='store_true', default=False, help='Search for locations by name')
    parser.add_argument('--comments', action='store_true', default=False, help='Save post comments to json file')
    parser.add_argument('--no-check-certificate', action='store_true', default=False,
                        help='Do not use ssl on transaction')
    parser.add_argument('--interactive', '-i', action='store_true', default=False,
                        help='Enable interactive login challenge solving')
    parser.add_argument('--retry-forever', action='store_true', default=False,
                        help='Retry download attempts endlessly when errors are received')
    parser.add_argument('--verbose', '-v', type=int, default=0, help='Logging verbosity level')
    parser.add_argument('--template', '-T', type=str, default='{urlname}', help='Customize filename template')


    args = parser.parse_args()

    if (args.login_user and args.login_pass is None) or (args.login_user is None and args.login_pass):
        parser.print_help()
        raise ValueError('Must provide login user AND password')

    if not args.username and args.filename is None and not args.followings_input:
        parser.print_help()
        raise ValueError(
            'Must provide username(s) OR a file containing a list of username(s) OR pass --followings-input')
    elif (args.username and args.filename) or (args.username and args.followings_input) or (
            args.filename and args.followings_input):
        parser.print_help()
        raise ValueError(
            'Must provide only one of the following: username(s) OR a filename containing username(s) OR --followings-input')

    if args.tag and args.location:
        parser.print_help()
        raise ValueError('Must provide only one of the following: hashtag OR location')

    if args.tag and args.filter:
        parser.print_help()
        raise ValueError('Filters apply to user posts')

    if args.filename:
        args.usernames = InstagramScraper.parse_file_usernames(args.filename)
    else:
        args.usernames = InstagramScraper.parse_delimited_str(','.join(args.username))

    if args.media_types and len(args.media_types) == 1 and re.compile(r'[,;\s]+').findall(args.media_types[0]):
        args.media_types = InstagramScraper.parse_delimited_str(args.media_types[0])

    if args.retry_forever:
        global MAX_RETRIES
        MAX_RETRIES = sys.maxsize

    scraper = InstagramScraper(**vars(args))

    if args.login_user and args.login_pass:
        scraper.authenticate_with_login()
    else:
        scraper.authenticate_as_guest()

    if args.followings_input:
        scraper.usernames = list(scraper.query_followings_gen(scraper.login_user))
        if args.followings_output:
            with open(scraper.destination + scraper.followings_output, 'w') as file:
                for username in scraper.usernames:
                    file.write(username + "\n")
            # If not requesting anything else, exit
            if args.media_types == ['none'] and args.media_metadata is False:
                scraper.logout()
                return

    if args.tag:
        scraper.scrape_hashtag()
    elif args.location:
        scraper.scrape_location()
    elif args.search_location:
        scraper.search_locations()
    else:
        scraper.scrape()

    scraper.save_cookies()
    with open("imgurls.txt", "a", encoding="utf8") as f:
        f.write("{")
    number = args.limit
    if number == None or number == 0:
        number = 1000
    for username in args.usernames:
        org_path = username
        all_img = glob.glob(org_path + "/*.jpg")
        for org_img in all_img:
            outfile = org_img.replace(username + "\\", "")
            path = r'emoji'  # use your path
            all_emoji = glob.glob(path + "/*.png")
            all_count = number
            while all_count > 0:

                img = cv2.imread(org_img)
                img_cnt = random.randint(1, 6)
                height, width, channels = img.shape

                while img_cnt > 0:
                    id = randrange(33)
                    choose_emoji = all_emoji[id]
                    overlay_t = cv2.imread(choose_emoji, -1)
                    img = overlay_transparent(img, overlay_t, random.randint(0, width - 75), random.randint(0, height - 75), (75, 75))
                    img_cnt -= 1

                output = "result/" + str(outfile) + "-" + str(all_count) + ".png"
                cv2.imwrite(output, img)
                all_count -= 1

            org_path = 'result'
            all_images = glob.glob(org_path + "/*.png")
            arr = np.array_split(all_images,5)
            with open("imgurls.txt", "a", encoding="utf8") as f:
                f.write("{")
            with Pool(processes=5) as pool:
                pool.map(UploadingImage, arr)
            files = glob.glob('result/*')
            for f in files:
                os.remove(f)
            with open("imgurls.txt", 'rb+') as filehandle:
                filehandle.seek(-1, os.SEEK_END)
                filehandle.truncate()
            with open("imgurls.txt", "a", encoding="utf8") as f:
                f.write("}|")
            print("image done:" + org_img)

        with open("imgurls.txt", 'rb+') as filehandle:
            filehandle.seek(-1, os.SEEK_END)
            filehandle.truncate()
        with open("imgurls.txt", "a", encoding="utf8") as f:
            f.write("}")


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
    cv2.destroyAllWindows()