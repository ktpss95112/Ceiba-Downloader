import logging
import os
import re
import time
from typing import List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from PySide6.QtCore import Signal

import strings
import util
from crawler import Crawler


class Course():

    cname_map = {
        'bulletin': '公佈欄',
        'syllabus': '課程大綱',
        'hw': '作業',
        'info': '課程資訊',
        'personal': '教師資訊',
        'grade': '學習成績',
        'board': '討論看板',
        'calendar': '課程行事曆',
        'share': '資源分享',
        'vote': '投票區',
        'student': '修課學生'
    }

    def __init__(self, semester, course_num, cname, ename, teacher, href):
        self.semester = semester
        self.course_num = course_num
        self.cname = cname
        self.ename = ename
        self.teacher = teacher
        self.href = href
        self.folder_name = util.get_valid_filename("_".join(
            [self.semester, self.cname, self.teacher]))
        self.course_sn = 0

    def __str__(self):
        return " ".join([self.cname, self.teacher, self.href])

    def download(self,
                 path: str,
                 session: requests.Session,
                 modules_filter_list: List[str] = None,
                 progress: Signal = None):
        self.path = os.path.join(path, self.folder_name)
        os.makedirs(self.path, exist_ok=True)
        current_url = util.get(session, self.href).url
        self.course_sn = re.search(
            r'course/([0-9a-f]*)+',
            current_url).group(0).removeprefix('course/')
        modules = self.homepage_download(session, '首頁', modules_filter_list)
        if progress:
            modules_not_in_this_module_num = len(modules_filter_list) - len(
                modules)
            if modules_not_in_this_module_num > 0:
                progress.emit(modules_not_in_this_module_num)

        for module in modules:
            try:
                self.__html_download(session, Course.cname_map[module], module)
            except Exception as e:
                logging.error(e)
                logging.debug(e, exc_info=True)
                logging.warning(strings.error_skip_and_continue_download.format(self.cname, module))
            if progress:
                progress.emit(1)

    @util.progress_decorator()
    def __html_download(self, session: requests.Session, obj_cname: str,
                        module: str):
        url = util.module_url + "?csn=" + self.course_sn + "&default_fun=" + module + "&current_lang=chinese"  # TODO:language

        module_dir = os.path.join(self.path, module)
        os.makedirs(module_dir, exist_ok=True)

        Crawler(session, url, module_dir, module + '.html', "").crawl()

    @util.progress_decorator()
    def homepage_download(self,
                          session: requests.Session,
                          cname: str = '首頁',
                          modules_filter_list: List[str] = None):
        url_gen = lambda x: x + "?csn=" + self.course_sn + "&default_fun=info&current_lang=chinese"  # TODO:language
        button_url = url_gen(util.button_url)
        banner_url = url_gen(util.banner_url)
        homepage_url = url_gen(util.homepage_url)
        Crawler(session, banner_url, self.path, "banner.html").crawl()
        self.__download_homepage(session, homepage_url)
        return self.__download_button(session, button_url, 'button.html',
                                      modules_filter_list)

    def __download_homepage(self,
                            session: requests.Session,
                            url: str,
                            filename: str = 'index.html'):
        resp = util.get(session, url)
        soup = BeautifulSoup(resp.content, 'html.parser')
        soup.find("frame", {"name": "topFrame"})['src'] = "banner.html"
        soup.find("frame", {"name": "leftFrame"})['src'] = "button.html"
        soup.find("frame", {"name": "mainFrame"})['src'] = "info/info.html"
        # TODO: footer.php
        with open(os.path.join(self.path, filename), 'w',
                  encoding='utf-8') as file:
            file.write(str(soup))

    def __download_button(self,
                          session: requests.Session,
                          url: str,
                          filename: str,
                          modules_filter_list: List[str] = None) -> List[str]:
        resp = util.get(session, url)
        soup = BeautifulSoup(resp.content, 'html.parser')
        Crawler(session, url, self.path).download_css(soup.find_all('link'))

        nav_co = soup.find("div", {"id": "nav_co"})
        items = []
        for a in nav_co.find_all('a'):
            try:
                item = re.search(r"onclick\('(.*?)'.*\)",
                                 a['onclick']).group(1)
            except AttributeError:
                logging.debug(
                    'abnormal onclick value: ' + a['onclick']
                )  # Only found out such case in '108-1 Machine Learning Foundations'
                item = a.next_element['id']
            else:
                if item in ['logout', 'calendar'] or \
                        (modules_filter_list is not None and item not in modules_filter_list):
                    # I assume the calendar is a feature nobody uses.
                    a.extract()  # remove the element
                    continue
            a['onclick'] = "parent.parent.mainFrame.location='" + item + "/" + item + ".html'"
            items.append(item)
        with open(os.path.join(self.path, filename), 'w',
                  encoding='utf-8') as file:
            file.write(str(soup))
        return items
