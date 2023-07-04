from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

URL = 'https://zap.planning.nyc.gov/projects'
PROJECT_SELECTOR = '.projects-list-result'

class Project:
    def __init__(self, element: WebElement):
        self.element = element

    def name(self) -> str:
        return self.by_css(f'{PROJECT_SELECTOR}--header a').text

    def url(self) -> str:
        return self.by_css(f'{PROJECT_SELECTOR}--header a').get_attribute('href')

    def status(self) -> str:
        return self.by_css('.publicstatus-label').text

    def by_css(self, selector: str) -> WebElement:
        return self.element.find_element(By.CSS_SELECTOR, selector)


def main():
    pass
    opts = webdriver.FirefoxOptions()
    opts.add_argument("--headless")
    driver = webdriver.Firefox(options=opts)
    driver.get(URL)
    WebDriverWait(driver, 10) \
        .until(EC.presence_of_element_located((By.CSS_SELECTOR, PROJECT_SELECTOR)))

    elems = driver.find_elements(By.CSS_SELECTOR, PROJECT_SELECTOR)
    for elem in elems:
        project = Project(elem)
        print(f'{project.name()} ({project.status()}): {project.url()}')
    print(len(elems))

