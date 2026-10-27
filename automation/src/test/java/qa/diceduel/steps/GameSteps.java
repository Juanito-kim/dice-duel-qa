package qa.diceduel.steps;

import io.cucumber.java.en.Given;
import io.cucumber.java.en.Then;
import io.cucumber.java.en.When;
import qa.diceduel.pages.GamePage;
import qa.diceduel.support.TestContext;

import java.util.Arrays;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** 게임 화면 Step (01·02·03 feature) */
public class GameSteps {
    private final TestContext ctx;
    private GamePage game;

    public GameSteps(TestContext ctx) {
        this.ctx = ctx;
    }

    private GamePage game() {
        if (game == null) game = new GamePage(ctx.driver());
        return game;
    }

    /** "[3, 3]" → [3, 3] */
    private static List<Integer> dice(String text) {
        return Arrays.stream(text.replaceAll("[\\[\\]\\s]", "").split(",")).map(Integer::parseInt).toList();
    }

    // ---------- 준비 ----------
    @Given("^사용자가 게임 화면에 접속했다$")
    public void openGame() {
        game().open();
    }

    @Given("^사용자가 \"([^\"]*)\" 닉네임으로 주사위 (\\d)개 매치를 시작했다$")
    public void startedMatch(String nickname, int diceCount) {
        game().open();
        game().startMatch(nickname, diceCount);
        assertTrue(game().isMatchStarted(), "매치가 시작되지 않음: " + game().startError());
    }

    @Given("^다음 라운드 결과가 플레이어 (\\[[^\\]]*\\]), 컴퓨터 (\\[[^\\]]*\\])로 정해져 있다$")
    public void nextRoll(String player, String cpu) {
        ctx.api.setNextRoll(game().matchId(), dice(player), dice(cpu));
    }

    // ---------- 행동 ----------
    @When("^닉네임 \"([^\"]*)\"[과와] 주사위 (\\d)개로 매치 시작을 누른다$")
    public void pressStart(String nickname, int diceCount) {
        game().startMatch(nickname, diceCount);
    }

    @When("^매치 진행 중에 주사위 개수 (\\d)개를 선택한다$")
    public void changeDiceDuringMatch(int diceCount) {
        game().chooseDiceCount(diceCount);
    }

    @When("^사용자가 던지기 버튼을 누른다$")
    public void pressThrow() {
        game().throwDice();
    }

    @When("^플레이어가 이기는 라운드를 (\\d)번 진행한다$")
    public void playerWins(int times) {
        for (int i = 0; i < times; i++) {
            ctx.api.setNextRoll(game().matchId(), List.of(6, 6), List.of(1, 2));
            game().throwDice();
        }
    }

    // ---------- 확인 ----------
    @Then("^매치 시작 결과는 \"(시작|거부)\"이다$")
    public void startOutcome(String expected) {
        if (expected.equals("시작")) {
            assertTrue(game().isMatchStarted(), "시작되어야 하는데 거부됨. 화면 문구: " + game().startError());
        } else {
            assertFalse(game().isMatchStarted(), "거부되어야 하는데 매치가 시작됨");
            assertTrue(game().startError().contains("2~10자"), "오류 문구: " + game().startError());
        }
    }

    @Then("^주사위 개수 선택은 (\\d)개 그대로다$")
    public void diceSelectionUnchanged(int expected) {
        assertEquals(expected, game().selectedDiceCount(), "매치 중인데 주사위 개수 선택이 바뀜");
    }

    @Then("^양쪽 주사위는 각각 (\\d)개다$")
    public void diceCountShown(int expected) {
        assertEquals(expected, game().dice("player").size(), "플레이어 주사위 수");
        assertEquals(expected, game().dice("cpu").size(), "컴퓨터 주사위 수");
    }

    @Then("^라운드 결과는 \"([^\"]*)\"로 표시된다$")
    public void roundResult(String expected) {
        assertEquals(expected, game().roundResult(), "라운드 결과");
    }

    @Then("^스코어는 (\\d+ : \\d+) 이 된다$")
    public void score(String expected) {
        assertEquals(expected, game().score(), "스코어 (플레이어 : 컴퓨터)");
    }

    @Then("^게임 규칙 안내에 \"([^\"]*)\" 문구가 있다$")
    public void rulesContain(String text) {
        assertTrue(game().rulesText().contains(text), "규칙 안내에 없음: " + text);
    }

    @Then("^라운드 1의 양쪽 주사위와 합계가 표시된다$")
    public void firstRoundShown() {
        assertEquals(1, game().roundNo(), "라운드 번호");
        List<Integer> p = game().dice("player"), c = game().dice("cpu");
        assertEquals(2, p.size());
        assertEquals(2, c.size());
        assertEquals(String.valueOf(p.stream().mapToInt(Integer::intValue).sum()), game().sum("player"), "플레이어 합계");
        assertEquals(String.valueOf(c.stream().mapToInt(Integer::intValue).sum()), game().sum("cpu"), "컴퓨터 합계");
        assertFalse(game().roundResult().isEmpty(), "라운드 결과 문구가 비어 있음");
    }

    @Then("^매치 결과는 \"([^\"]*)\"로 표시된다$")
    public void matchResult(String expected) {
        assertEquals(expected, game().matchResult(), "매치 결과");
    }

    @Then("^던지기 버튼은 비활성화된다$")
    public void throwDisabled() {
        assertFalse(game().isThrowEnabled(), "끝난 매치인데 던지기 버튼이 활성화됨");
    }
}
