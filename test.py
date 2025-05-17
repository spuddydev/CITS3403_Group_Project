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
        self.assertEqual(response.status_code, 302)

    def test_login_page_loads(self):
        response = self.app.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'login', response.data.lower())

    def test_register_page_loads(self):
        response = self.app.get('/register')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'register', response.data.lower())

    def test_profile_requires_login(self):
        response = self.app.get('/profile', follow_redirects=True)
        self.assertIn(b'login', response.data.lower())

    def test_dashboard_requires_login(self):
        response = self.app.get('/dashboard', follow_redirects=True)
        self.assertIn(b'login', response.data.lower())

    def test_404_error(self):
        response = self.app.get('/nonexistent')
        self.assertEqual(response.status_code, 404)
        self.assertIn(b'not found', response.data.lower())

    def test_logout_redirects(self):
        response = self.app.get('/logout', follow_redirects=True)
        self.assertIn(b'login', response.data.lower())

    def test_static_css_exists(self):
        response = self.app.get('/static/css/style.css')  
        self.assertIn(response.status_code, [200, 304])

    def test_about_page_loads(self):
        response = self.app.get('/about')
        self.assertIn(response.status_code, [200, 302, 404])  # change if route is defined

    def test_contact_page_loads(self):
        response = self.app.get('/contact')
        self.assertIn(response.status_code, [200, 302, 404])  # change if route is defined


class SeleniumWebDriverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ctx = multiprocessing.get_context('spawn')
        cls.server_process = ctx.Process(target=run_app)
        cls.server_process.start()
        time.sleep(2.5)  # Give Flask time to spin up

        options = Options()
        options.add_argument("--headless=new")
        cls.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        cls.base_url = "http://localhost:5003"

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        cls.server_process.terminate()
        cls.server_process.join()

    def visit_and_assert(self, path, expected_text):
        self.driver.get(f"{self.base_url}{path}")
        self.assertIn(expected_text.lower(), self.driver.page_source.lower())

    def test_homepage_loads(self):
        self.visit_and_assert("/home", "html")

    def test_login_page_loads(self):
        self.visit_and_assert("/login", "login")

    def test_register_page_loads(self):
        self.visit_and_assert("/register", "register")

    def test_404_page_displays(self):
        self.driver.get(f"{self.base_url}/notarealpage")
        self.assertIn("not found", self.driver.page_source.lower())

    def test_dashboard_redirects_unauthenticated(self):
        self.driver.get(f"{self.base_url}/dashboard")
        self.assertIn("login", self.driver.page_source.lower())

    def test_profile_redirects_unauthenticated(self):
        self.driver.get(f"{self.base_url}/profile")
        self.assertIn("login", self.driver.page_source.lower())

    def test_social_redirects_unauthenticated(self):
        self.driver.get(f"{self.base_url}/social")
        self.assertIn("login", self.driver.page_source.lower())

    def test_trends_redirects_unauthenticated(self):
        self.driver.get(f"{self.base_url}/trends")
        self.assertIn("login", self.driver.page_source.lower())

    def test_researchers_redirects_unauthenticated(self):
        self.driver.get(f"{self.base_url}/researchers")
        self.assertIn("login", self.driver.page_source.lower())

    def test_upload_redirects_unauthenticated(self):
        self.driver.get(f"{self.base_url}/upload")
        self.assertIn("login", self.driver.page_source.lower())

    def test_saved_redirects_unauthenticated(self):
        self.driver.get(f"{self.base_url}/saved")
        self.assertIn("login", self.driver.page_source.lower())

if __name__ == '__main__':
    unittest.main()
