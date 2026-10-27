package qa.diceduel.support;

import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeOptions;
import org.openqa.selenium.remote.RemoteWebDriver;

import java.net.URI;

/** 시나리오 하나 동안 Step 클래스들이 함께 쓰는 상태 (브라우저, API). picocontainer가 시나리오마다 새로 만든다. */
public class TestContext {
    private WebDriver driver;
    public final ApiClient api = new ApiClient(Config.baseUrl());

    public WebDriver driver() {
        if (driver == null) driver = createDriver();
        return driver;
    }

    public boolean hasDriver() {
        return driver != null;
    }

    public void quit() {
        if (driver != null) driver.quit();
        driver = null;
    }

    private static WebDriver createDriver() {
        ChromeOptions options = new ChromeOptions();
        options.addArguments("--window-size=1280,900", "--lang=ko-KR");
        if (Config.headless()) options.addArguments("--headless=new");
        try {
            String remote = Config.remoteUrl();
            if (!remote.isBlank()) return new RemoteWebDriver(URI.create(remote).toURL(), options);
        } catch (Exception e) {
            throw new IllegalStateException("원격 브라우저 연결 실패: " + Config.remoteUrl(), e);
        }
        return new ChromeDriver(options);  // 드라이버는 Selenium Manager가 자동으로 받는다
    }
}
