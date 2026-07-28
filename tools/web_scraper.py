import requests

class WebScraper:
    def __init__(self, url):
        self.url = url

    def scrape(self):
        response = requests.get(self.url)
        return response.text

# Example usage:
# scraper = WebScraper('https://www.example.com')
# print(scraper.scrape())