-- Dice Duel v1.0 스키마. PostgreSQL 컨테이너가 처음 만들어질 때 한 번 실행된다.

CREATE TABLE matches (
    id            SERIAL PRIMARY KEY,
    nickname      VARCHAR(20) NOT NULL,
    dice_count    SMALLINT    NOT NULL CHECK (dice_count IN (2, 3)),
    seed          BIGINT      NOT NULL,
    status        VARCHAR(12) NOT NULL DEFAULT 'IN_PROGRESS',  -- IN_PROGRESS / FINISHED
    rounds_played SMALLINT    NOT NULL DEFAULT 0,
    player_wins   SMALLINT    NOT NULL DEFAULT 0,
    cpu_wins      SMALLINT    NOT NULL DEFAULT 0,
    draws         SMALLINT    NOT NULL DEFAULT 0,
    result        VARCHAR(6),                                  -- PLAYER / CPU / DRAW
    source        VARCHAR(10) NOT NULL DEFAULT 'web',          -- web / generator
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at   TIMESTAMPTZ
);

CREATE TABLE rounds (
    id          SERIAL PRIMARY KEY,
    match_id    INT        NOT NULL REFERENCES matches(id),
    round_no    SMALLINT   NOT NULL,
    player_dice INT[]      NOT NULL,
    cpu_dice    INT[]      NOT NULL,
    player_sum  SMALLINT   NOT NULL,
    cpu_sum     SMALLINT   NOT NULL,
    result      VARCHAR(6) NOT NULL,                  -- PLAYER / CPU / DRAW
    forced      BOOLEAN    NOT NULL DEFAULT false,    -- 테스트 API로 지정한 눈인지
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (match_id, round_no)                        -- R-09: 같은 라운드는 한 번만
);

-- 테스트 모드 전용: 다음 라운드에 쓸 눈 (R-07)
CREATE TABLE forced_rolls (
    match_id    INT   PRIMARY KEY REFERENCES matches(id),
    player_dice INT[] NOT NULL,
    cpu_dice    INT[] NOT NULL
);

CREATE INDEX idx_matches_created_at ON matches (created_at);
CREATE INDEX idx_rounds_match_id ON rounds (match_id);
