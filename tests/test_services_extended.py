import pytest

from app.models.qa import QAContextType
from app.schemas.qa import QAResponse
from app.schemas.simulation import AnswerItem, SubmitSimulationRequest
from app.services import detail_questions as dq
from app.services import qa as qa_service
from app.services import simulation as sim


class FakeSession:
    """Minimal async session stub for service-layer tests."""

    def __init__(self, execute_results=None):
        self.added = []
        self.flushed = False
        self.committed = False
        self.execute_calls = []
        self._id_counter = 1
        self._results = list(execute_results or [])

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flushed = True
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                setattr(obj, "id", self._id_counter)
                self._id_counter += 1

    async def commit(self):
        self.committed = True

    async def execute(self, stmt):
        self.execute_calls.append(stmt)
        # return object with scalar/ scalars helpers
        class _Result:
            def __init__(self, data):
                self._data = data

            def scalar_one_or_none(self):
                return self._data[0] if self._data else None

            def scalars(self):
                return iter(self._data)

            def all(self):
                return list(self._data)

        if self._results:
            return _Result(self._results.pop(0))
        return _Result([])


def test_detail_comment_and_next_step_messages():
    missing_comment = dq._comment_for_axis(score=5.0, missing=1)
    assert isinstance(missing_comment, str) and len(missing_comment) > 0
    high_comment = dq._comment_for_axis(score=8.5, missing=0)
    assert high_comment != missing_comment
    ok_comment = dq._comment_for_axis(score=dq.OK_LINE, missing=0)
    assert ok_comment != high_comment
    mid_comment = dq._comment_for_axis(score=6.0, missing=0)
    low_comment = dq._comment_for_axis(score=1.0, missing=0)
    assert len(mid_comment) > 0 and len(low_comment) > 0

    hint_with_missing = dq._next_step_for_axis("concept", missing=2)
    plain_hint = dq._next_step_for_axis("funds", missing=0)
    assert hint_with_missing != plain_hint


@pytest.mark.asyncio
async def test_detail_calculate_axis_scores_with_mock_persist(monkeypatch):
    called = {}

    async def _noop_persist(session, user_id, results, axis_meta):
        called["count"] = len(results)

    monkeypatch.setattr(dq, "_persist_axis_scores", _noop_persist)

    axis_meta = {code: {"name": dq.AXIS_DEFAULTS.get(code, code)} for code in dq.AXIS_ORDER}
    answers = {q["code"]: True for q in dq.DETAIL_QUESTION_DEFINITIONS}
    dummy_session = FakeSession()

    results = await dq.calculate_axis_scores(dummy_session, user_id=1, answers=answers, axis_meta=axis_meta)

    assert called["count"] == len(results)
    assert all(r.score == 10.0 for r in results)
    assert all(r.missing == 0 for r in results)


@pytest.mark.asyncio
async def test_detail_save_detail_answers_inserts_and_commits():
    session = FakeSession()
    answers = {dq.DETAIL_QUESTION_DEFINITIONS[0]["code"]: True}

    await dq.save_detail_answers(session, user_id=10, answers=answers)

    assert session.committed is True
    assert any(getattr(obj, "question_code", "") in answers for obj in session.added)


@pytest.mark.asyncio
async def test_detail_save_detail_answers_rejects_unknown_code():
    session = FakeSession()
    with pytest.raises(ValueError):
        await dq.save_detail_answers(session, user_id=1, answers={"unknown": True})


def test_detail_build_axis_checkpoints_distribution():
    axis_map = dq._build_axis_question_map()
    checkpoints = dq._build_axis_checkpoints(axis_map)
    # Each axis should have 10 checkpoint slots (4+3+3)
    assert all(len(qs) == 10 for qs in checkpoints.values())
    # First question gets weighted 4 times
    for axis_code, qs in checkpoints.items():
        first = axis_map[axis_code][0]
        assert qs.count(first) == 4


def test_detail_summarize_concept_text_default_and_custom():
    empty = dq.summarize_concept_text(None)
    assert empty["title"]
    assert isinstance(empty["description"], str)

    text = "タイトル行\n説明1\n説明2"
    summary = dq.summarize_concept_text(text)
    assert summary["title"] == "タイトル行"
    assert "説明1" in summary["description"]
    assert "説明2" in summary["description"]


def test_simulation_axis_score_unknown_and_compliance_floor():
    answers = {
        "main_genre": ["undecided_main"],
        "seats": [],
        "price_point": [],
        "location": [],
    }
    scores = sim.calculate_axis_scores(answers)
    assert scores["concept"] == 0.0
    assert scores["compliance"] == 1.0  # compliance gets minimum 1.0 when zero


def test_simulation_generate_funds_comment_branches():
    comment = sim.generate_funds_comment({"seats": 50, "price_point": 3000})
    assert comment[0].name.lower() == "tight"
    relaxed = sim.generate_funds_comment({"seats": 10, "price_point": 9000})
    assert relaxed[0].name.lower() == "relaxed"
    fallback = sim.generate_funds_comment({})
    assert fallback[0].name.lower() == "tight"


def test_simulation_store_profile_missing_required():
    profile = sim._build_store_profile({})
    missing = sim._find_missing_required(profile)
    for key in ["main_genre", "sub_genre", "seats", "price_point", "business_hours", "location"]:
        assert key in missing


@pytest.mark.asyncio
async def test_simulation_generate_store_story_fallback(monkeypatch):
    async def fake_story(payload):
        return None

    monkeypatch.setattr(sim, "ai_generate_store_story", fake_story)
    profile = {
        "main_genre": "izakaya",
        "sub_genre": "izakaya_taishu",
        "seats": 20,
        "price_point": 3000,
        "business_hours": "dinner",
        "location": "near_station",
    }
    story = await sim.generate_store_story(profile)
    assert "izakaya" in story
    assert "near_station" in story


@pytest.mark.asyncio
async def test_qa_handle_question_global_context(monkeypatch):
    session = FakeSession()
    async def fake_answer(context, question):
        return "answer text"

    monkeypatch.setattr(qa_service, "ai_answer_question", fake_answer)

    response: QAResponse = await qa_service.handle_question(
        db=session,
        user_id=99,
        context_type=QAContextType.GLOBAL.value,
        axis_code=None,
        question="今の状況は？",
    )

    assert isinstance(response, QAResponse)
    assert response.reply == "answer text"
    assert session.committed is True
    # Conversation and two messages should be added (user + assistant)
    assert any(getattr(obj, "role", None) for obj in session.added)


@pytest.mark.asyncio
async def test_simulation_process_submission_for_guest(monkeypatch):
    async def fake_story(payload):
        return "generated story"

    monkeypatch.setattr(sim, "ai_generate_store_story", fake_story)
    payload = SubmitSimulationRequest(
        answers=[
            AnswerItem(question_code="main_genre", values=["izakaya"]),
            AnswerItem(question_code="sub_genre", values=["izakaya_taishu"]),
            AnswerItem(question_code="seats", values=["24"]),
            AnswerItem(question_code="price_point", values=["3000"]),
            AnswerItem(question_code="business_hours", values=["dinner"]),
            AnswerItem(question_code="location", values=["near_station"]),
        ],
        guest_session_token="guest123",
    )
    session = FakeSession()

    result = await sim.process_simulation_submission(session, payload, user_id=None)

    assert result.session_id == 1
    assert "concept" in result.axis_scores
    assert result.funds_comment_text
    assert any(hasattr(obj, "session_id") for obj in session.added)


@pytest.mark.asyncio
async def test_simulation_process_submission_with_user(monkeypatch):
    async def fake_story(payload):
        return "generated story"

    async def fake_axis_map(db):
        return {"concept": 1}

    monkeypatch.setattr(sim, "ai_generate_store_story", fake_story)
    monkeypatch.setattr(sim, "_get_axis_id_map", fake_axis_map)

    payload = SubmitSimulationRequest(
        answers=[
            AnswerItem(question_code="main_genre", values=["izakaya"]),
            AnswerItem(question_code="sub_genre", values=["izakaya_taishu"]),
            AnswerItem(question_code="seats", values=["12"]),
            AnswerItem(question_code="price_point", values=["4500"]),
            AnswerItem(question_code="business_hours", values=["dinner"]),
            AnswerItem(question_code="location", values=["near_station"]),
        ],
        guest_session_token=None,
    )
    session = FakeSession()

    result = await sim.process_simulation_submission(session, payload, user_id=10)

    assert result.session_id == 1
    # AxisScore objects for user should be added
    assert any(obj.__class__.__name__ == "AxisScore" for obj in session.added)
    assert session.committed is True


@pytest.mark.asyncio
async def test_simulation_attach_session_to_user(monkeypatch):
    class DummySessionObj:
        def __init__(self):
            self.id = 5
            self.user_id = None

    class DummyResultObj:
        def __init__(self):
            from app.models.simple_simulation import FundsCommentCategory

            self.session_id = 5
            self.axis_scores = {"concept": 4.0}
            self.funds_comment_category = FundsCommentCategory.TIGHT
            self.funds_comment_text = "text"
            self.store_story_text = "story"

    async def fake_axis_map(db):
        return {"concept": 1}

    monkeypatch.setattr(sim, "_get_axis_id_map", fake_axis_map)

    session_obj = DummySessionObj()
    sim_result = DummyResultObj()
    session = FakeSession(execute_results=[[session_obj], [sim_result]])

    result = await sim.attach_session_to_user(session, session_id=5, user_id=99)

    assert result is not None
    assert session_obj.user_id == 99
    assert any(obj.__class__.__name__ == "StoreStory" for obj in session.added)
    assert session.committed is True


@pytest.mark.asyncio
async def test_qa_list_recent_questions(monkeypatch):
    from datetime import datetime, timedelta
    from app.models.free_question import FreeQuestion

    now = datetime.utcnow()
    items = [
        FreeQuestion(user_id=1, axis_code=None, question_text="q1", answer_text="a1", created_at=now),
        FreeQuestion(
            user_id=1,
            axis_code="concept",
            question_text="q2",
            answer_text="a2",
            created_at=now - timedelta(minutes=1),
        ),
    ]
    session = FakeSession(execute_results=[items])

    result = await qa_service.list_recent_questions(session, user_id=1, limit=5)

    assert len(result) == 2
    assert result[0].question_text == "q1"
