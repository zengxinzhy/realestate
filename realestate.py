#!/usr/bin/env python
"""Real estate web crawler"""
import signal
import argparse
import sys
import re

import logging

from html.parser import HTMLParser
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.exporters import CsvItemExporter

import scrapy.item
import scrapy.selector
import scrapy.signals
import pydispatch
import scrapy.crawler

EXPORT_FIELDS = ['bed', 'bath', 'car', 'price', 'address', 'url']


class RealestateItem(scrapy.item.Item):
    """A real estate listing summary"""
    bed = scrapy.item.Field()
    bath = scrapy.item.Field()
    car = scrapy.item.Field()
    price = scrapy.item.Field()
    address = scrapy.item.Field()
    url = scrapy.item.Field()


class RealestateSpider(CrawlSpider):
    """Real estate web crawler"""
    name = 'buyrentsold'
    allowed_domains = ['realestate.com.au']

    custom_settings = {
        'LOG_ENABLED': True
    }

    def __init__(self, command = 'buy', search = 'tempe'):
        search = re.sub(r'\s+', '+', re.sub(',+', '%2c', search)).lower()
        url = '/{0}/in-{{0}}{{{{0}}}}/list-{{{{1}}}}'.format(command)
        start_url = 'http://www.{0}{1}'
        start_url = start_url.format(
                self.allowed_domains[0], url.format(search)
        )
        self.start_urls = [start_url.format('', 1)]
        extractor = LinkExtractor(
            allow=url.format(re.escape(search)).format('.*', '')
        )
        rule = Rule(
            extractor, callback='parse_items', follow=True
        )
        self.rules = [rule]
        super(RealestateSpider, self).__init__()

    def parse_items(self, response):
        """Parse a page of real estate listings"""
        hxs = scrapy.selector.HtmlXPathSelector(response)
        for i in hxs.select('//div[contains(@class, "listingInfo")]'):
            item = RealestateItem()
            path = 'div[contains(@class, "propertyStats")]//text()'
            item['price'] = i.select(path).extract()
            vcard = i.select('div[contains(@class, "vcard")]//a')
            item['address'] = vcard.select('text()').extract()
            url = vcard.select('@href').extract()
            if len(url) == 1:
                item['url'] = 'http://www.{0}{1}'.format(
                        self.allowed_domains[0], url[0]
                )
            features = i.select('dl')
            for field in ('bed', 'bath', 'car'):
                path = '(@class, "rui-icon-{0}")'.format(field)
                path = 'dt[contains{0}]'.format(path)
                path = '{0}/following-sibling::dd[1]'.format(path)
                path = '{0}/text()'.format(path)
                item[field] = features.select(path).extract() or 0
            yield item

def unescape(data):
    """Unescape html text"""
    return HTMLParser.HTMLParser().unescape(','.join(data))

def realestate(command, search, filehandle):
    """Writes the real estate search results to the given file handle"""
    exporter = scrapy.exporters.CsvItemExporter(
            filehandle, fields_to_export=EXPORT_FIELDS
    )

    def catch_item(sender, item, **kwargs):
        """Output item as a csv line"""
        exporter.export_item(item)

    pydispatch.dispatcher.connect(exporter.start_exporting,
            signal=scrapy.signals.spider_opened)
    pydispatch.dispatcher.connect(exporter.finish_exporting,
            signal=scrapy.signals.spider_closed)
    pydispatch.dispatcher.connect(catch_item,
            signal=scrapy.signals.item_passed)

    #spider = RealestateSpider(command, search)

    crawler = scrapy.crawler.CrawlerProcess()
    crawler.crawl(RealestateSpider, command=command, search=search)
    crawler.start()


def main():
    """Output the real estate search results in csv format"""
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    parser = argparse.ArgumentParser(description='Realestate search results.')
    parser.add_argument('command', choices=['buy', 'rent', 'sold'])
    parser.add_argument('search')
    args = parser.parse_args()
    realestate(args.command, args.search, sys.stdout)
if __name__ == '__main__':
    main()
