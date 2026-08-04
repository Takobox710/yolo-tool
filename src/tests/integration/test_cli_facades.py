from __future__ import annotations


def test_run_predict_forwards_the_optional_structured_emitter(monkeypatch):
    from src.bootstrap import cli_validation

    captured = {}

    def fake_impl(argv, emit=None):
        captured["argv"] = argv
        captured["emit"] = emit
        return 7

    emitter = lambda *_args, **_kwargs: None
    monkeypatch.setattr(cli_validation, "_run_predict_cli_impl", fake_impl)

    assert cli_validation.run_predict(["payload.json"], emit=emitter) == 7
    assert captured == {"argv": ["payload.json"], "emit": emitter}
