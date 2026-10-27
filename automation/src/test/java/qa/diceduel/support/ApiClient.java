package qa.diceduel.support;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.util.List;

/** 화면 값을 검증하기 위한 서버 API 호출. 테스트 모드 눈 지정(R-07)도 여기서 한다. */
public class ApiClient {
    private final String base;
    private final HttpClient http = HttpClient.newHttpClient();
    private final ObjectMapper json = new ObjectMapper();

    public ApiClient(String base) {
        this.base = base;
    }

    /** 다음 라운드의 눈을 지정한다 (테스트 모드 전용 API) */
    public void setNextRoll(int matchId, List<Integer> player, List<Integer> cpu) {
        String body = "{\"match_id\":%d,\"player\":%s,\"cpu\":%s}".formatted(matchId, player, cpu);
        HttpResponse<String> res = send(HttpRequest.newBuilder(URI.create(base + "/api/test/next-roll"))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(body)).build());
        if (res.statusCode() != 200) {
            throw new IllegalStateException("눈 지정 실패 " + res.statusCode() + ": " + res.body());
        }
    }

    /** 닉네임 부분 일치로 매치 목록 조회 (최대 1000건) */
    public JsonNode matches(String nickname) {
        String q = URLEncoder.encode(nickname, StandardCharsets.UTF_8);
        return readJson(send(get("/api/matches?limit=1000&nickname=" + q)).body());
    }

    /** 필터에 맞는 전체 건수 (응답 헤더 X-Total-Count) */
    public int totalCount(String nickname) {
        String q = URLEncoder.encode(nickname, StandardCharsets.UTF_8);
        return send(get("/api/matches?limit=1&nickname=" + q)).headers()
                .firstValue("X-Total-Count").map(Integer::parseInt).orElse(-1);
    }

    private HttpRequest get(String path) {
        return HttpRequest.newBuilder(URI.create(base + path)).GET().build();
    }

    private HttpResponse<String> send(HttpRequest req) {
        try {
            return http.send(req, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
        } catch (Exception e) {
            throw new IllegalStateException("API 호출 실패: " + req.uri(), e);
        }
    }

    private JsonNode readJson(String body) {
        try {
            return json.readTree(body);
        } catch (Exception e) {
            throw new IllegalStateException("JSON 읽기 실패: " + body, e);
        }
    }
}
