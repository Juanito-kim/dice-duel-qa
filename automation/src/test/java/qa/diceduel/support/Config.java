package qa.diceduel.support;

/** 실행 설정: -D 옵션 또는 환경 변수로 바꾼다. */
public final class Config {
    private Config() {
    }

    private static String get(String prop, String env, String fallback) {
        String v = System.getProperty(prop);
        if (v == null || v.isBlank()) v = System.getenv(env);
        return (v == null || v.isBlank()) ? fallback : v;
    }

    /** 테스트 대상 주소 */
    public static String baseUrl() {
        return get("baseUrl", "BASE_URL", "http://localhost:8080");
    }

    /** true면 브라우저 창 없이 실행 (CI) */
    public static boolean headless() {
        return Boolean.parseBoolean(get("headless", "HEADLESS", "false"));
    }

    /** true면 굴림 애니메이션을 켠 채 실행 (기본은 ?noanim으로 끔 → 실행 시간 단축) */
    public static boolean anim() {
        return Boolean.parseBoolean(get("anim", "ANIM", "false"));
    }

    /** 값이 있으면 원격 브라우저(selenium/standalone-chrome 컨테이너)를 사용 */
    public static String remoteUrl() {
        return get("seleniumRemoteUrl", "SELENIUM_REMOTE_URL", "");
    }
}
