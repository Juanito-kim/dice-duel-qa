package qa.diceduel.pages;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.WebDriverWait;
import qa.diceduel.support.Config;

import java.time.Duration;
import java.util.List;

/** 게임 화면 (Page Object). 요소는 모두 data-testid로 찾는다. */
public class GamePage {
    private final WebDriver driver;
    private final WebDriverWait wait;

    public GamePage(WebDriver driver) {
        this.driver = driver;
        this.wait = new WebDriverWait(driver, Duration.ofSeconds(10));
    }

    private static By id(String testId) {
        return By.cssSelector("[data-testid='" + testId + "']");
    }

    private WebElement el(String testId) {
        return driver.findElement(id(testId));
    }

    public void open() {
        driver.get(Config.baseUrl() + (Config.anim() ? "/" : "/?noanim"));
        wait.until(d -> el("start-button").isDisplayed());
    }

    // ---------- 매치 시작 ----------
    public void startMatch(String nickname, int diceCount) {
        el("dice-count-" + diceCount).click();
        WebElement input = el("nickname-input");
        input.clear();
        input.sendKeys(nickname);
        el("start-button").click();
        // 시작되면 매치 영역이 보이고, 거부되면 오류 문구가 나온다
        wait.until(d -> isMatchStarted() || !startError().isEmpty());
    }

    public boolean isMatchStarted() {
        return el("match-section").isDisplayed();
    }

    public String startError() {
        return el("start-error").getText();
    }

    public int matchId() {
        return Integer.parseInt(el("match-id").getText());
    }

    public void chooseDiceCount(int diceCount) {
        el("dice-count-" + diceCount).click();
    }

    public int selectedDiceCount() {
        return Integer.parseInt(driver.findElement(By.cssSelector("input[name=dice]:checked")).getAttribute("value"));
    }

    // ---------- 던지기 ----------
    /** 던지기 버튼을 누르고, 굴림이 끝나 결과가 화면에 반영될 때까지 기다린다. */
    public void throwDice() {
        String before = el("round-no").getText();
        el("throw-button").click();
        wait.until(d -> "false".equals(el("match-section").getAttribute("data-rolling"))
                && (!el("round-no").getText().equals(before) || !el("throw-error").getText().isEmpty()));
    }

    public String roundResult() {
        return el("round-result").getText();
    }

    public String score() {
        return el("score").getText();
    }

    public int roundNo() {
        return Integer.parseInt(el("round-no").getText());
    }

    /** side: "player" 또는 "cpu". 주사위 눈은 점으로 그려지므로 data-value로 읽는다 */
    public List<Integer> dice(String side) {
        return driver.findElements(By.cssSelector("[data-testid='" + side + "-dice'] .die")).stream()
                .map(e -> Integer.parseInt(e.getAttribute("data-value"))).toList();
    }

    public String sum(String side) {
        return el(side + "-sum").getText();
    }

    public String matchResult() {
        return el("match-result").getText();
    }

    public boolean isThrowEnabled() {
        return el("throw-button").isEnabled();
    }

    // ---------- 규칙 안내 ----------
    public String rulesText() {
        return el("rules").getText();
    }
}
