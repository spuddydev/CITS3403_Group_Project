import unittest
import multiprocessing
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

def run_app():
    from app import app
    app.run(port=5003, use_reloader=False)

class BasicFlaskTests(unittest.TestCase):
    def setUp(self):
        from app import app
        self.app = app.test_client()
        self.app.testing = True

    def test_home_page(self):
        response = self.app.get('/home')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<html', response.data.lower())

    def test_redirect_default(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 302)  # redirect to somewhere

    def test_login_page_loads(self):
        response = self.app.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)

    def test_register_page_loads(self):
        response = self.app.get('/register')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Register', response.data)

    def test_profile_page_requires_login(self):
        response = self.app.get('/profile', follow_redirects=True)
        # Assuming profile redirects to login if not authenticated
        self.assertIn(b'Login', response.data)

    def test_dashboard_requires_login(self):
        response = self.app.get('/dashboard', follow_redirects=True)
        # Assuming dashboard redirects to login if not authenticated
        self.assertIn(b'Login', response.data)

    def test_404_error(self):
        response = self.app.get('/nonexistentpage')
        self.assertEqual(response.status_code, 404)
        self.assertIn(b'Not Found', response.data)


class SeleniumWebDriverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ctx = multiprocessing.get_context('spawn')
        cls.server_process = ctx.Process(target=run_app)
        cls.server_process.start()
        time.sleep(2)  

        options = Options()
        options.add_argument("--headless")
        cls.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        cls.base_url = "http://localhost:5003/"

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        cls.server_process.terminate()
        cls.server_process.join()

    def test_homepage_loads(self):
        self.driver.get(self.base_url + "home")
        self.assertIn("html", self.driver.page_source.lower())

if __name__ == '__main__':
    unittest.main()
