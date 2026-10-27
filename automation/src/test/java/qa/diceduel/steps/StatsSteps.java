package qa.diceduel.steps;

import com.fasterxml.jackson.databind.JsonNode;
import io.cucumber.java.en.Given;
import io.cucumber.java.en.Then;
import io.cucumber.java.en.When;
import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;
import qa.diceduel.pages.StatsPage;
import qa.diceduel.support.TestContext;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** 통계 화면 Step (04 feature). 화면 값을 서버 API로 다시 계산한 값과 비교한다. */
public class StatsSteps {
    private final TestContext ctx;
    private StatsPage stats;
    private String nicknameFilter = "";

    public StatsSteps(TestContext ctx) {
        this.ctx = ctx;
    }

    private StatsPage stats() {
        if (stats == null) stats = new StatsPage(ctx.driver());
        return stats;
    }

    @Given("^사용자가 통계 화면에 접속했다$")
    public void openStats() {
        stats().open();
    }

    @When("^닉네임 \"([^\"]*)\"로 매치 기록을 조회한다$")
    public void searchNickname(String nickname) {
        nicknameFilter = nickname;
        stats().searchNickname(nickname);
    }

    @When("^더보기를 더 이상 없을 때까지 누른다$")
    public void loadAll() {
        while (stats().hasMore()) stats().loadMore();
    }

    @Then("^닉네임별 전적의 모든 승률이 매치 기록으로 계산한 값과 같다$")
    public void winRatesMatch() {
        List<String> diffs = new ArrayList<>();
        for (WebElement row : stats().playerRows()) {
            List<WebElement> td = row.findElements(By.tagName("td"));
            String nickname = td.get(1).getText(), shown = td.get(5).getText();
            int wins = 0, finished = 0;
            for (JsonNode m : ctx.api.matches(nickname)) {
                if (!m.get("nickname").asText().equals(nickname)) continue;  // 부분 일치 결과에서 같은 닉네임만
                if ("FINISHED".equals(m.get("status").asText())) finished++;
                if ("PLAYER".equals(m.path("result").asText())) wins++;
            }
            String expected = String.format("%.2f%%", finished == 0 ? 0.0 : 100.0 * wins / finished);
            if (!expected.equals(shown)) {
                diffs.add("%s 화면 %s vs 계산 %s (%d승 / 끝난 매치 %d)".formatted(nickname, shown, expected, wins, finished));
            }
        }
        assertTrue(diffs.isEmpty(), "S-04 승률 불일치 " + diffs.size() + "건: " + String.join("; ", diffs));
    }

    @Then("^매치 기록의 닉네임은 모두 \"([^\"]*)\"를 포함한다$")
    public void allNicknamesContain(String part) {
        List<String> names = stats().matchColumn(2);
        assertTrue(!names.isEmpty(), "조회 결과가 없음");
        names.forEach(n -> assertTrue(n.contains(part), "필터와 맞지 않는 닉네임: " + n));
    }

    @Then("^건수 표시는 서버의 전체 건수와 같다$")
    public void countMatchesServer() {
        int total = ctx.api.totalCount(nicknameFilter);
        assertTrue(stats().countLabel().endsWith("/ " + total + "건"), "건수 표시 " + stats().countLabel() + ", 서버 " + total);
    }

    @Then("^매치 기록은 처음에 (\\d+)건만 보인다$")
    public void firstPage(int size) {
        assertEquals(size, stats().matchRows().size(), "처음 표시 건수");
    }

    @Then("^매치 기록 건수는 서버의 전체 건수와 같고 중복이 없다$")
    public void allLoaded() {
        List<String> ids = stats().matchIds();
        int total = ctx.api.totalCount("");
        assertEquals(total, ids.size(), "불러온 건수");
        assertEquals(ids.size(), new HashSet<>(ids).size(), "중복된 매치가 있음");
        assertTrue(stats().countLabel().startsWith(total + " / " + total), "건수 표시: " + stats().countLabel());
    }
}
