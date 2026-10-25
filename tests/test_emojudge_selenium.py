import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


BASE_URL = "http://localhost:30089"

# Replace these with an existing valid EmoJudge account.
VALID_ATTORNEY_ID = "sn123"
VALID_PASSWORD = "123456"


@pytest.fixture
def driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(3)

    yield driver

    driver.quit()


def login(driver, attorney_id, password):
    driver.get(BASE_URL)

    driver.find_element(By.ID, "attorney_id").send_keys(attorney_id)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()


# TEST 1
def test_login_page_loads(driver):
    driver.get(BASE_URL)

    assert "EmoJudge" in driver.title
    assert driver.find_element(By.ID, "attorney_id").is_displayed()
    assert driver.find_element(By.ID, "password").is_displayed()
    assert driver.find_element(
        By.CSS_SELECTOR, "button[type='submit']"
    ).is_displayed()


# TEST 2
def test_invalid_login(driver):
    login(driver, "invalid_user", "wrong_password")

    error = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located(
            (By.CLASS_NAME, "error-message")
        )
    )

    assert error.is_displayed()


# TEST 3
def test_valid_login_redirects_to_dashboard(driver):
    login(driver, VALID_ATTORNEY_ID, VALID_PASSWORD)

    WebDriverWait(driver, 10).until(
        EC.url_contains("/dashboard")
    )

    assert "/dashboard" in driver.current_url
    assert "Command Center" in driver.title


# TEST 4
def test_dashboard_content(driver):
    login(driver, VALID_ATTORNEY_ID, VALID_PASSWORD)

    WebDriverWait(driver, 10).until(
        EC.url_contains("/dashboard")
    )

    page_text = driver.find_element(By.TAG_NAME, "body").text

    assert "ANALYSIS COMMAND CENTER" in page_text
    assert "Witness Queue" in page_text
    assert "AI Analysis Engine" in page_text
    assert "SYSTEM STATUS" in page_text


# TEST 5
def test_start_analysis(driver):
    login(driver, VALID_ATTORNEY_ID, VALID_PASSWORD)

    start_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (By.CLASS_NAME, "primary-btn")
        )
    )

    start_button.click()

    WebDriverWait(driver, 10).until(
        EC.url_contains("/videos1")
    )

    assert "/videos1" in driver.current_url


# TEST 6
def test_witness_analyze_button(driver):
    login(driver, VALID_ATTORNEY_ID, VALID_PASSWORD)

    analyze_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (By.CLASS_NAME, "analyze-btn")
        )
    )

    analyze_button.click()

    WebDriverWait(driver, 10).until(
        EC.url_contains("/videos1")
    )

    assert "/videos1" in driver.current_url


# TEST 7
def test_logout(driver):
    login(driver, VALID_ATTORNEY_ID, VALID_PASSWORD)

    logout_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (By.CLASS_NAME, "logout-btn")
        )
    )

    logout_button.click()

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.ID, "attorney_id")
        )
    )

    assert driver.current_url.rstrip("/") == BASE_URL
    # TEST 8
def test_emotion_analysis_result(driver):
    login(driver, VALID_ATTORNEY_ID, VALID_PASSWORD)

    # Wait for dashboard
    WebDriverWait(driver, 10).until(
        EC.url_contains("/dashboard")
    )

    # Open witness analysis workspace
    start_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (By.CLASS_NAME, "primary-btn")
        )
    )
    start_button.click()

    WebDriverWait(driver, 10).until(
        EC.url_contains("/videos1")
    )

    # Open the first witness video
    first_video = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (By.CLASS_NAME, "video-card")
        )
    )
    first_video.click()

    # Emotion analysis runs automatically every 4 seconds.
    # Wait until the placeholder "—" is replaced by an AI result.
    WebDriverWait(driver, 45).until(
        lambda d: d.find_element(
            By.ID, "emotionBadge"
        ).text.strip() not in ("", "—")
    )

    emotion = driver.find_element(
        By.ID, "emotionBadge"
    ).text.strip()

    confidence = driver.find_element(
        By.ID, "confText"
    ).text.strip()

    print(f"Detected expression: {emotion}")
    print(f"Confidence: {confidence}")

    assert emotion != "—"
    assert emotion != ""
    assert "%" in confidence