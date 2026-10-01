from app import triage
from app.schemas import StoredStep, Triage


def _step(id: int) -> StoredStep:
    return StoredStep(id=id, step_number=id, text=f"step {id}", is_safety_warning=False, icon="wrench")


async def test_triage_drops_step_id_not_in_sop(monkeypatch):
    steps = [_step(1), _step(2)]

    async def fake_call_json(messages, model_cls):
        return Triage(kind="machine", summary="loud noise", step_id=999, severity="high", suggested_change=None)

    monkeypatch.setattr(triage.llm, "call_json", fake_call_json)
    result = await triage.triage(steps, "it is making a loud noise", "hi", None)
    assert result.step_id is None
    assert result.kind == "machine"


async def test_triage_keeps_step_id_when_valid(monkeypatch):
    steps = [_step(1), _step(2)]

    async def fake_call_json(messages, model_cls):
        return Triage(kind="sop", summary="wrong bolt size", step_id=2, severity="medium", suggested_change="use M8")

    monkeypatch.setattr(triage.llm, "call_json", fake_call_json)
    result = await triage.triage(steps, "the bolt size is wrong", "hi", None)
    assert result.step_id == 2
