"""
A collection of classes to deal with the mess of generating url links to the EMBO Press review prcocess files.
Unfortunately, RPF are not (yet) assined their own DOI. The morphology of the links are also variable, depending on the journal.
All the RPF links generated are teste to be alive.

Usage:
    url =  generate_rpf_link('Molecular Systems Biology', '10.15252/msb.20198849')
"""

from json import JSONDecodeError
from random import randint
from time import sleep
import requests
import re
from .utils import resolve
from . import logger


class RPFLinkAbstract:
    """
    Base abstract class used to generate links to EMBO Press review process files (RPF). 
    The class is callable and makes sure that the links are tested and active.
    Subclasses need to implement the private method _generate_link() which take a doi as argument.

    Argument:
        doi (str): the doi of the paper from which the rpf link should be generated.

    Returns:
        str: the url of the link to the RPF or an empty string if the link did not work.
    """

    def __init__(self, delay_requests: bool = True, *args, **kwargs) -> None:
        super.__init__(*args, **kwargs)
        self.delay_requests = True

    # wouldn't it be nice to have doi for RPFs?
    # But we don't... so, here it goes:
    # https://www.embopress.org/action/downloadSupplement?doi=10.15252/embj.2019102578&file=embj2019102578.reviewer_comments.pdf
    # https://www.embopress.org/action/downloadSupplement?doi=10.15252/msb.20198849&file=msb198849.reviewer_comments.pdf
    # https://www.embopress.org/action/downloadSupplement?doi=10.15252/msb.202010025&file=msb202010025.reviewer_comments.pdf
    # https://www.embopress.org/action/downloadSupplement?doi=10.15252/embr.201847097&file=embr201847097.reviewer_comments.pdf
    # https://www.embopress.org/action/downloadSupplement?doi=10.15252/emmm.201910291&file=emmm201910291.reviewer_comments.pdf
    # https://www.life-science-alliance.org/content/lsa/2/4/e201900445.reviewer-comments.pdf

    def _generate_link(self, doi: str) -> str:
        raise NotImplementedError

    def _test(self, link: str, invalid='') -> bool:
        if not link:
            return invalid

        if self.delay_requests:
            duration = randint(5, 20)
            logger.debug('Delaying %s seconds before requesting %s', duration, link)
            sleep(duration)

        proxy_request_data = {
            'cmd': 'request.get',
            'url': link,
            'maxTimeout': 60000,
        }
        proxy_response = requests.post('http://proxy:8191/v1', json=proxy_request_data, timeout=60000)

        if proxy_response.status_code != 200:
            logger.warning("Failed to get response from proxy for %s: %s, %s", link, proxy_response, proxy_response.headers)
            return invalid
        try:
            proxy_response_data = proxy_response.json()
        except JSONDecodeError as e:
            logger.warning("Failed to get valid response from proxy for %s: %s, %s", link, proxy_response, proxy_response.headers)
            return invalid
        
        response_status = proxy_response_data['solution']['status']
        response_headers = proxy_response_data['solution']['headers']
        if response_status != 200:
            logger.warning("Failed to get response for %s: %s, %s", link, response_status, response_headers)
            return invalid

        response_content_type = response_headers.get('content-type', '')
        return link if 'application/pdf' in response_content_type else invalid

    def __call__(self, doi: str) -> str:
        link = self._generate_link(doi)
        return self._test(link)


class RPFLinkEjErEmmMsb(RPFLinkAbstract):
    """
    The class that generates RPF links for EMBO Journal, EMBO reports and EMBO Molecular Medicine.
    """

    def _generate_link(self, doi: str) -> str:
        suffix_without_dot = re.sub(r'^10.\d{4,9}/([-_;()/:a-zA-Z0-9]+)\.([-_;()/:a-zA-Z0-9]+)$', r'\1\2', doi)
        link = f"https://www.embopress.org/action/downloadSupplement?doi={doi}&file={suffix_without_dot}.reviewer_comments.pdf"
        return link


# deprecated
# class RPFLinkMSB(RPFLinkAbstract):
#     """
#     The class that generates RPF links for Molecular Systems Biology.
#     """
#     def _generate_link(self, doi: str) -> str:
#         suffix_without_dot_truncated_year =re.sub(r'^10.\d{4,9}/([-_;()/:a-zA-Z0-9]+)\.\d\d([-_;()/:a-zA-Z0-9]+)', r'\1\2', doi)
#         link = f"https://www.embopress.org/action/downloadSupplement?doi={doi}&file={suffix_without_dot_truncated_year}.reviewer_comments.pdf"
#         return link


class RPFLinkLSA(RPFLinkAbstract):
    """
    The class that generates RPF links for Life Science Alliance.
    """
    def _generate_link(self, doi: str) -> str:
        resolved = resolve(doi)
        vol_issue_enumber = re.search(r'\d+/\d+/e\d+', resolved).group(0)
        link = f"https://www.life-science-alliance.org/content/lsa/{vol_issue_enumber}.reviewer-comments.pdf"
        return link


def generate_rpf_link(journal: str, doi: str) -> str:
    """
    Resolves an EMBO Press journal and doi into a link to the Review Process Files (RPF).

    Arguments:
        journal (str): the name of the journal
        doi (str): the doi of the paper

    Returns:
        str: the url of the link to the rpf
    """

    journal = journal.strip().lower()
    if journal in ['the embo journal', 'embo reports', 'embo molecular medicine', 'molecular systems biology']:
        resolver = RPFLinkEjErEmmMsb()
    elif journal == 'life science alliance':
        resolver = RPFLinkLSA()
    else:
        return ""
    return resolver(doi)