from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
import requests
import configparser
import logging
import sys, os
import json
from urllib.parse import urlparse
from django.db import models




def extract_domain(url):
    parsed_url = urlparse(url)
    return parsed_url.netloc


logging.basicConfig(filename='logo_extraction.log', level=logging.INFO, format='%(asctime)s %(message)s')
logging.info("Reading config.file")
config = configparser.ConfigParser()
try:
    config.read('config.file')
    geckodriver_path = config['DEFAULT']['GECKODRIVER_LOCATION']

except FileNotFoundError:
    logging.error("File not found. Please place config.file in current working directory")


class LogoExtraction:

    def __init__(self, number_to_crawl):
        self.number_to_crawl = number_to_crawl
        options = Options()
        options.headless = True
        options.log.level = 'error'
        try:
            self.driver = webdriver.Firefox(options=options)
        except:
            print("geckodriver not found! Provide path to geckodriver in config.file")
            sys.exit(0)
        self.urls = []

    def get_url_from_file(self, input_filename):
        """
        Read urls from file

        Returns:
        :rtype: list : List of urls from file
        """
        try:
            with open(input_filename) as input_file:
                urls = input_file.readlines()
                if not urls:
                    logging.error("No valid url found! Input file is empty!")
                    sys.exit(0)
                else:
                    return urls
        except FileNotFoundError:
            logging.error("Input file not found")

    def get_element_by_xpath(self, driver, element_name):
        """
        Return element using xpath

        Parameters:
        :type element_name: str
        :type driver: selenium.webdriver.firefox.webdriver.WebDriver

        Returns:
        :rtype: selenium.webdriver.firefox.webelement.FirefoxWebElement

        """
        return driver.find_elements(by=By.XPATH, value=element_name)

    def fetch_logos(self, input_filename):
        """
        Extract logos from website by finding different html elements

        Parameters:
        :type input_filename : str

        """
        images_link = {}

        images_count = {'img': 0, 'a': 0, 'div': 0}

        if os.path.exists(input_filename):
            self.urls = self.get_url_from_file(input_filename)
        else:
            # could be the case that URL is supplied from cmdline
            self.urls.append(input_filename)

        while self.urls and self.number_to_crawl > 0:
            # popping elements from front
            url = self.urls.pop(0)
            self.number_to_crawl -= 1
            images_link[url] = []

            try:
                self.driver.get(url)
                logging.info("Processing URL: {}".format(url))
            except:
                logging.error("Cannot process {}. Invalid URL.".format(url))
                if not self.urls:
                    self.driver.close()
                    # sys.exit(0)
                else:
                    continue

            # search for images inside <img> tag
            images = self.get_element_by_xpath(self.driver, '//img')
            if images:
                # process src attribute for logos found using 'img' tag
                images_count['img'] += 1
                for image in images:
                    try:
                        logo_url = image.get_attribute('src')
                        logo_class = image.get_attribute('class')
                        logo_alt = image.get_attribute('alt')
                    except:
                        continue
                    if 'enamad' in logo_url or 'samandehi' in logo_url:
                        continue
                    if logo_url:
                        logo_name = logo_url.split("/")[-1].lower()
                        # check if name of the logo begins with "logo" or has an attribute that contains "logo"
                        if logo_name.startswith("logo") or "logo" in logo_class.lower() or "logo" in logo_alt.lower():
                            images_link[url].append(logo_url)
                            break
                        # check if name of the logo contains "logo" if not beginning with it
                        elif "logo" in logo_name:
                            images_link[url].append(logo_url)
                            break
                        # check if the website's name is present in logo name and has the website address in it
                        elif url.split("/")[-1].split(".")[0] in logo_name and url in logo_url:
                            images_link[url].append(logo_url)
                            break
                        elif 'logo' in logo_url:
                            images_link[url].append(logo_url)
                            break

            if len(images_link[url]) == 0:
                # search for images inside <a> tag
                images = self.get_element_by_xpath(self.driver, '//a/img')
                if images:
                    print("Images found using a tag")
                    images_count['a'] += 1
                    for image in images:
                        if image.get_attribute(''):
                            images_link[url].append(image.get_attribute('src'))
                            break

                if len(images_link[url]) == 0:
                    images = self.get_element_by_xpath(self.driver, "//div/a/*[name()='svg']")
                    for image in images:
                        if image.get_attribute('outerHTML'):
                            image.screenshot('crawled/' + extract_domain(url) + '/' + '-1.png')

                    # search for images inside <div> tag
                    images = self.get_element_by_xpath(self.driver, '//div/a/img')
                    images_count['div'] += 1
                    for image in images:
                        if image.get_attribute('src'):
                            images_link[url].append(image.get_attribute('src'))
                            break

        logging.info("Total Number of URLs processed: {}".format(len(images_link.keys())))
        logging.info("Analysis of logo extraction. Image sources by tags: ")
        logging.info(images_count)

        self.driver.close()

        self.write_logo_urls_to_file(images_link)

    def write_logo_urls_to_file(self, images_link):
        """

        Writes valid logo links from dictionary returned by fetch_logos to a text file

        Parameters:
        :type images_link: dict

        """
        for key, values in images_link.items():
            domain = extract_domain(key)
            try:
                os.mkdir('crawled/' + domain)
            except:
                logging.error('Directory already exists')
            for i in range(len(values)):
                data = requests.get(values[i]).content
                if values[i].endswith('webp'):
                    f = open('crawled/' + domain + '/' + str(i) + '.webp', 'wb')
                else:
                    f = open('crawled/' + domain + '/' + str(i) + '.jpg', 'wb')
                f.write(data)
                f.close()

        json.dump(images_link, open("output.json", 'w'))
        f = open('input.txt', 'w')
        urls = ''.join(self.urls)
        f.write(urls)
        f.close()


if __name__ == '__main__':
    L = LogoExtraction(1)
    L.fetch_logos(sys.argv[1])
