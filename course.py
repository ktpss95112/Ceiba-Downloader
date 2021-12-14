from PySide6.QtWidgets import QProgressBar
import requests
import os
from qt_custom_widget import PyLogOutput
import util
import strings
import re
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import List
from crawler import Crawler


class Course():

    cname_map = {'bulletin': '公佈欄', 'syllabus': '課程大綱', 'hw': '作業',
                    'info': '課程資訊', 'personal': '教師資訊', 'grade': '學習成績',
                    'board': '討論看板', 'calendar': '課程行事曆', 'share': '資源分享',
                    'vote': '投票區', 'student': '修課學生'}
    
    def __init__(self, semester, course_num, cname, ename, teacher, href):
        self.semester = semester
        self.course_num = course_num
        self.cname = cname
        self.ename = ename
        self.teacher = teacher
        self.href = href
        self.folder_name = util.get_valid_filename("_".join([self.semester, self.cname, self.teacher]))
        self.course_sn = 0

    def __str__(self):
        return " ".join([self.cname, self.teacher, self.href])

    def download(self, path: str, session: requests.Session, modules_filter_list: List[str] = None, progress_bar: QProgressBar = None, log_output: PyLogOutput = None):
        self.path = os.path.join(path, self.folder_name)
        current_url = session.get(self.href).url
        self.course_sn = re.search(r'course/([0-9a-f]*)+', current_url).group(0).removeprefix('course/')
        modules = self.homepage_download(session, '首頁', modules_filter_list, log_output)
        for module in modules:
            if log_output:
                log_output.insertText(strings.course_module_download_info.format(self.cname, Course.cname_map[module]))
            self.__html_download(session, Course.cname_map[module], module, log_output)
            if progress_bar:
                progress_bar.setValue(progress_bar.value() + 1)

    @util.progress_decorator()
    def __html_download(self, session: requests.Session, obj_cname: str, module: str, log_output: PyLogOutput = None):
        url = util.module_url + "?csn=" + self.course_sn + "&default_fun=" + module + "&current_lang=chinese" # TODO:language
        resp = session.get(url)
        if any(x in resp.content.decode('utf-8') for x in ['此功能並未開啟', '目前無指派作業']):
            print(strings.cancel_on_object.format(self.cname, obj_cname, obj_cname))
            return

        dir = os.path.join(self.path, module)
        os.makedirs(dir, exist_ok=True)

        c = Crawler(session, url, dir, module + '.html', 0, log_output)
        c.crawl(is_table=True)
    
    @util.progress_decorator()
    def homepage_download(self, session: requests.Session, cname: str = '首頁', modules_filter_list: List[str] = None, log_output: PyLogOutput = None):
        url_gen = lambda x: x + "?csn=" + self.course_sn + "&default_fun=info&current_lang=chinese"  # TODO:language
        button_url = url_gen(util.button_url)
        banner_url = url_gen(util.banner_url)
        homepage_url = url_gen(util.homepage_url)
        Crawler(session, banner_url, self.path, "banner.html", log_output).crawl()
        self.__download_homepage(session, homepage_url)
        return self.__download_button(session, button_url, 'button.html', modules_filter_list)
    
    def __download_homepage(self, session: requests.Session, url: str, filename: str = 'index.html'):
        resp = session.get(url)
        soup = BeautifulSoup(resp.content, 'html.parser')
        soup.find("frame", {"name": "topFrame"})['src'] = "banner.html"
        soup.find("frame", {"name": "leftFrame"})['src'] = "button.html"
        soup.find("frame", {"name": "mainFrame"})['src'] = "info/info.html"
        # TODO: footer.php
        with open(os.path.join(self.path, filename), 'w', encoding='utf-8') as file:
            file.write(str(soup))

    def __download_button(self, session: requests.Session, url: str, filename: str, modules_filter_list: List[str] = None) -> List[str]:
        resp = session.get(url)
        soup = BeautifulSoup(resp.content, 'html.parser')
        for css in soup.find_all('link'):
            url = urljoin(url, css.get('href'))
            css['href'] = url.split('/')[-1]
            
            c = Crawler(session, url, self.path, css['href'], 0)
            c.crawl(static=True)
        
        nav_co = soup.find("div", {"id": "nav_co"})
        items = []
        for a in nav_co.find_all('a'):
            item = re.search(r"onclick\('(.*?)'.*\)", a['onclick']).group(1)
            if item in ['logout', 'calendar'] or item not in modules_filter_list:  # I assume the calendar is a feature nobody uses.
                a.extract()  # remove the element
                continue
            a['href'] = os.path.join(item, item + ".html")
            items.append(item)
        with open(os.path.join(self.path, filename), 'w', encoding='utf-8') as file:
            file.write(str(soup))
        return items
