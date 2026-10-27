package qa.diceduel.steps;

import io.cucumber.java.After;
import io.cucumber.java.AfterStep;
import io.cucumber.java.Scenario;
import org.openqa.selenium.OutputType;
import org.openqa.selenium.TakesScreenshot;
import qa.diceduel.support.TestContext;

/** Step마다 화면을 찍어 리포트에 붙이고, 시나리오가 끝나면 브라우저를 닫는다. */
public class Hooks {
    private final TestContext ctx;

    public Hooks(TestContext ctx) {
        this.ctx = ctx;
    }

    @AfterStep
    public void screenshot(Scenario scenario) {
        if (!ctx.hasDriver()) return;
        byte[] png = ((TakesScreenshot) ctx.driver()).getScreenshotAs(OutputType.BYTES);
        scenario.attach(png, "image/png", scenario.isFailed() ? "실패 시점 화면" : "화면");
    }

    @After
    public void close() {
        ctx.quit();
    }
}
