package qa.diceduel.pages;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.WebDriverWait;
import qa.diceduel.support.Config;

import java.time.Duration;
import java.util.List;

/** 통계 화면 (Page Object) */
public class StatsPage {
    private final WebDriver driver;
    private final WebDriverWait wait;

    public StatsPage(WebDriver driver) {
        this.driver = driver;
        this.wait = new WebDriverWait(driver, Duration.ofSeconds(10));
    }

    private WebElement el(String testId) {
        return driver.findElement(By.cssSelector("[data-testid='" + testId + "']"));
    }

    public void open() {
        driver.get(Config.baseUrl() + "/stats");
        wait.until(d -> !matchRows().isEmpty() && !playerRows().isEmpty());
    }

    // ---------- 매치 기록 ----------
    public List<WebElement> matchRows() {
        return driver.findElements(By.cssSelector("[data-testid='match-row']"));
    }

    /** 매치 기록 표의 n번째 열 값 (0부터: 매치, 시작 시각, 닉네임, …) */
    public List<String> matchColumn(int index) {
        return matchRows().stream().map(r -> r.findElements(By.tagName("td")).get(index).getText()).toList();
    }

    public List<String> matchIds() {
        return matchRows().stream().map(r -> r.getAttribute("data-match-id")).toList();
    }

    public String countLabel() {
        return el("grid-count").getText();
    }

    public void searchNickname(String nickname) {
        WebElement input = el("filter-nickname");
        input.clear();
        input.sendKeys(nickname);
        String before = countLabel();
        el("filter-apply").click();
        wait.until(d -> !countLabel().equals(before));
    }

    public boolean hasMore() {
        return driver.findElement(By.id("load-more")).isDisplayed();
    }

    public void loadMore() {
        int before = matchRows().size();
        driver.findElement(By.id("load-more")).click();
        wait.until(d -> matchRows().size() > before);
    }

    // ---------- 닉네임별 전적 ----------
    public List<WebElement> playerRows() {
        return driver.findElements(By.cssSelector("[data-testid='player-row']"));
    }
}
