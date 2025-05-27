from plugins.base import MangaPluginBase, Formats, AgeRating, Status, NO_THUMBNAIL_URL, DATETIME_FORMAT
import requests
from bs4 import BeautifulSoup
from lxml import etree

import logging
logger = logging.getLogger(__name__)

class HDPornComicPlugin(MangaPluginBase):
    languages = ["en"]
    base_url = "https://hdporncomics.com"

    def search_manga(self, query:str, language:str=None) -> list[dict]:
        logger.debug(f'Searching for "{query}"')
        try:
            current_page = 1
            of_pages = current_page
            check_for_pages = False
            searched_manga = []
            while current_page <= of_pages:
                response = requests.get(f'{self.base_url}/page/{current_page}',
                                            params={
                                                "s": query.lower(),
                                                "s_extra[]": ["title", "taxonomy"],
                                            },
                                            timeout=10
                                            )
                
                response.raise_for_status()

                if not check_for_pages:
                    of_pages = self.get_search_pages_from_html(response.text)
                    check_for_pages = True

                searched_manga.append(self.get_manga_list_from_html(response.text))
                current_page += 1
            
            return sum(searched_manga, [])

        except Exception as e:
            logger.error(f'Error while searching manga - {e}')
        return []
    
    def get_search_pages_from_html(self, document) -> int:
        soup = BeautifulSoup(document, 'lxml')
        dom = etree.HTML(str(soup))
        navigation = dom.xpath("//*[@id='navigation']/nav/div/a")

        if len(navigation) == 0:
            return 0
        
        return int(navigation[-2].text)
    
    def get_manga_list_from_html(self, document) -> list[dict]:
        soup = BeautifulSoup(document, 'lxml')
        dom = etree.HTML(str(soup))
        mangaList = dom.xpath("//*[@id='all-posts']/div[contains(@class,'max-w-md')]")

        if not mangaList:
            return []
        
        mangaData = []
        for child in mangaList:
            if not isinstance(child.tag, str):
                continue
            child_divs = child.xpath("./div")

            img_section = child_divs[0]
            info_section = child_divs[1]

            if img_section is None or info_section is None:
                continue

            url_div = img_section.xpath("./a")

            if len(url_div) == 0:
                continue

            img = url_div[0].xpath(".//img")

            if len(img) == 0:
                continue

            manga_dict = self.search_manga_dict()
            manga_dict["cover"] = img[0].get("src") or NO_THUMBNAIL_URL
            manga_dict["url"] = url_div[0].get("href")

            if manga_dict["url"] is None:
                continue

            name_div = info_section.xpath("./a/h2")

            if len(name_div) == 0:
                continue

            manga_dict["name"] = name_div[0].text
            mangaData.append(manga_dict)

        return mangaData

    def get_manga(self, arguments:dict) -> dict:
        try:
            url = arguments.get("url")
            if url is None:
                raise Exception("There is no URL in arguments")
            response = requests.get(url,
                                    timeout=10
                                    )
            response.raise_for_status()

            return self.get_manga_from_html(response.text, url)

        except Exception as e:
            logger.error(f'Error while getting manga - {e}')

        return {}
    
    def get_manga_from_html(self, document, url) -> dict:
        soup = BeautifulSoup(document, 'lxml')
        dom = etree.HTML(str(soup))
        info_nodes = dom.xpath("//div[@id='infoBox']")
        manga = self.get_manga_dict()
        if len(info_nodes) == 0:
            return manga
        info_node = info_nodes[0]


        name = info_node.xpath("./h1")
        if len(name) == 0:
            return manga
        manga["name"] = name[0].text


        img_nodes = dom.xpath("//*[@id='imgBox']/img")
        manga["poster_url"] = img_nodes[0].get("src") if len(img_nodes) != 0 and img_nodes[0].get("src") else NO_THUMBNAIL_URL

        metadata_nodes = info_node.xpath("./div")
        manga["writers"] = []

        for metadata_node in metadata_nodes:
            span_nodes = metadata_node.xpath("./span")
            type_span = span_nodes[0]
            values_span = span_nodes[1]

            m_type:str = type_span.text

            if m_type.startswith("Tags"):
                for tag in values_span.xpath(".//span/a"):
                    manga["tags"].append(tag.text)
            elif m_type.startswith("Genres"):
                for genre in values_span.xpath(".//span/a"):
                    manga["genres"].append(genre.text)
            elif m_type.startswith("Artist"):
                for artist in values_span.xpath(".//span/a"):
                    manga["writers"].append(artist.text)
            elif m_type.startswith("Images"):
                if len(values_span) != 0:
                    manga["pages"] = int(values_span[0].text)

        manga["url"] = url

        return manga
    
    def get_chapters(self, arguments:dict) -> list[dict]:
        try:
            url = arguments.get("url")
            if url is None:
                raise Exception("There is no URL in arguments")
            response = requests.get(url,
                                    timeout=10
                                    )
            response.raise_for_status()

            return self.get_chapters_list_from_html(arguments)

        except Exception as e:
            logger.error(f'Error while getting manga - {e}')

        return []
    
    def get_chapters_list_from_html(self, arguments) -> list[dict]:
        chapter = self.get_chapter_dict()
        chapter["name"] = arguments.get("name")
        chapter["writer"] = ", ".join(arguments.get("writers"))
        chapter["page_count"] = arguments.get("pages")
        chapter["age_rating"] = AgeRating.R18_PLUS
        chapter["arguments"] = arguments
        chapter["url"] = arguments.get("url")
        chapter["source_url"] = arguments.get("url")

        return [chapter]
    
    def get_pages(self, arguments:dict) -> list[dict]:
        try:
            url = arguments.get("url")
            if url is None:
                raise Exception("There is no URL in arguments")
            response = requests.get(url,
                                    timeout=10
                                    )
            response.raise_for_status()

            return self.get_pages_list_from_html(response.text, arguments)

        except Exception as e:
            logger.error(f'Error while getting manga - {e}')

        return []
    
    def get_pages_list_from_html(self, document, arguments) -> list[dict]:
        soup = BeautifulSoup(document, 'lxml')
        dom = etree.HTML(str(soup))

        images = dom.xpath("//article[2]/div/div/figure")
        if len(images) == 0:
            raise ValueError("No images found")
        
        pages = []
        for image in images:
            page = self.get_page_dict()
            image_node = image.xpath("./a")

            if len(image_node) == 0:
                raise ValueError("Image search errors")
            
            image_url = image_node[0].get("href")

            if image_url is None:
                raise ValueError("Image search errors")
            
            page["arguments"] = arguments
            page["url"] = image_url

            pages.append(page)

        return pages